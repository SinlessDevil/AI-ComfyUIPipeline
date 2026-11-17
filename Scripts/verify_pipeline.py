"""Submit a new local generation and verify the returned PNG. Requires a running backend."""
import argparse
import copy
import json
from pathlib import Path
import secrets
import time
import urllib.error
import urllib.request
import uuid
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
HTTP = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(url, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(url, data=payload, headers={'Content-Type':'application/json'} if payload else {})
    try:
        with HTTP.open(req, timeout=30) as response:
            return json.load(response)
    except urllib.error.HTTPError as error:
        raise RuntimeError(f'ComfyUI HTTP {error.code}: {error.read().decode(errors="replace")}') from error


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT)
    parser.add_argument('--workflow', type=Path)
    parser.add_argument('--url', default='http://127.0.0.1:8188')
    parser.add_argument('--timeout', type=int, default=600)
    args = parser.parse_args()
    root = args.root.resolve()
    path = args.workflow or root / 'Workflows/GameArt/GameArt_Text_Final_API.json'
    graph = copy.deepcopy(json.loads(path.read_text(encoding='utf-8-sig')))
    run_id = uuid.uuid4().hex[:12]
    seed_changes = save_changes = 0
    for node in graph.values():
        inputs = node.get('inputs', {})
        for name in ['seed', 'noise_seed']:
            if name in inputs and isinstance(inputs[name], int):
                inputs[name] = secrets.randbits(40)
                seed_changes += 1
        if node.get('class_type') == 'SaveImage':
            inputs['filename_prefix'] = f'PipelineSmoke/{run_id}'
            save_changes += 1
    if not seed_changes or not save_changes:
        raise ValueError('Smoke graph must have an integer seed and SaveImage node')
    request(args.url + '/system_stats')
    submission = request(args.url + '/prompt', {'prompt': graph, 'client_id': 'pipeline-smoke-' + run_id})
    prompt_id = submission.get('prompt_id')
    if not prompt_id or submission.get('node_errors'):
        raise RuntimeError(f'Workflow rejected: {submission}')
    deadline = time.monotonic() + args.timeout
    history = None
    while time.monotonic() < deadline:
        history = request(args.url + '/history/' + prompt_id).get(prompt_id)
        if history:
            status = history.get('status', {})
            if status.get('status_str') == 'error':
                raise RuntimeError(json.dumps({'prompt_id':prompt_id,'status':status}, ensure_ascii=False))
            if status.get('completed'):
                break
        time.sleep(1)
    else:
        raise TimeoutError(f'Job {prompt_id} exceeded {args.timeout}s; inspect /queue before cancelling it')
    outputs = []
    for node in history.get('outputs', {}).values():
        for image in node.get('images', []):
            if image.get('type') != 'output':
                continue
            target = (root / 'Output' / image.get('subfolder', '') / image['filename']).resolve()
            if not target.is_relative_to((root / 'Output').resolve()):
                raise RuntimeError('Output path escapes Output folder')
            with Image.open(target) as png:
                png.load()
                outputs.append({'path':str(target),'size':list(png.size),'mode':png.mode})
    if not outputs:
        raise RuntimeError(f'Job {prompt_id} completed without a local output PNG; confirm backend output-directory')
    report = {'prompt_id':prompt_id,'workflow':str(path),'outputs':outputs,'transport':'local HTTP API, not MCP'}
    (root / 'Logs').mkdir(exist_ok=True)
    (root / 'Logs/pipeline-smoke.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
