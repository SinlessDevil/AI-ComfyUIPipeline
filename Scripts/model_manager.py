"""Plan, download, or verify the selected pinned model profile. Standard library only."""
import argparse
import hashlib
import json
import shutil
from pathlib import Path
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def checksum(path):
    digest = hashlib.sha256()
    with path.open('rb') as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b''):
            digest.update(block)
    return digest.hexdigest()


def destination(root, relative):
    folder = (root / 'Models').resolve()
    target = (folder / relative).resolve()
    if not target.is_relative_to(folder) or target == folder:
        raise ValueError(f'Model path escapes Models: {relative}')
    return target


def selected_models(catalog, profile):
    ids = set(catalog['profiles'][profile])
    entries = [model for model in catalog['models'] if model['id'] in ids]
    if len(entries) != len(ids):
        raise ValueError('Unknown model ID in profile')
    return entries


def download(model, target):
    if target.exists():
        if target.stat().st_size == model['bytes'] and checksum(target) == model['sha256']:
            print(f'Verified existing: {model["file"]}', flush=True)
            return
        raise RuntimeError(f'Existing file differs; preserving it: {target}')
    target.parent.mkdir(parents=True, exist_ok=True)
    partial = target.with_name(target.name + '.part')
    offset = partial.stat().st_size if partial.exists() else 0
    if offset > model['bytes']:
        raise RuntimeError(f'Oversized partial download: {partial}')
    if offset < model['bytes']:
        headers = {'Range': f'bytes={offset}-'} if offset else {}
        request = urllib.request.Request(model['url'], headers=headers)
        with urllib.request.urlopen(request, timeout=120) as response:
            append = offset > 0 and response.status == 206
            if append and not response.headers.get('Content-Range', '').startswith(f'bytes {offset}-'):
                raise RuntimeError('Server returned an unexpected resume offset')
            with partial.open('ab' if append else 'wb') as output:
                while block := response.read(8 * 1024 * 1024):
                    output.write(block)
    if partial.stat().st_size != model['bytes'] or checksum(partial) != model['sha256']:
        # Keep a failed download for inspection but avoid retrying the same full corrupt file.
        partial.rename(partial.with_name(partial.name + '.invalid'))
        raise RuntimeError(f'Download checksum/size mismatch: {target}')
    partial.replace(target)
    print(f'Downloaded and verified: {model["file"]}', flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--catalog', type=Path, default=ROOT / 'Config/models.lock.json')
    parser.add_argument('--profile', default='ui')
    action = parser.add_mutually_exclusive_group()
    action.add_argument('--download', action='store_true')
    action.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    catalog = json.loads(args.catalog.read_text(encoding='utf-8-sig'))
    entries = selected_models(catalog, args.profile)
    print(f'{args.profile}: {len(entries)} files, {sum(m["bytes"] for m in entries) / 1e9:.3f} GB total', flush=True)
    missing_bytes = 0
    for model in entries:
        target = destination(args.root, model['file'])
        if not target.exists():
            partial = target.with_name(target.name + '.part')
            missing_bytes += max(0, model['bytes'] - (partial.stat().st_size if partial.exists() else 0))
        print(f'  {model["file"]}: {model["bytes"] / 1e9:.3f} GB', flush=True)
    if args.download:
        disk_path = args.root.resolve()
        while not disk_path.exists():
            disk_path = disk_path.parent
        if shutil.disk_usage(disk_path).free < missing_bytes + 1024**3:
            raise RuntimeError('Not enough free disk space for the model download plus 1 GiB reserve')
        for model in entries:
            download(model, destination(args.root, model['file']))
    elif args.verify:
        for model in entries:
            target = destination(args.root, model['file'])
            if not target.is_file() or target.stat().st_size != model['bytes'] or checksum(target) != model['sha256']:
                raise RuntimeError(f'Model verification failed: {target}')
        print('All selected models verified.')


if __name__ == '__main__':
    main()
