"""Download only the two approved starter artifacts, with SHA256 verification."""
import hashlib
import json
import os
from pathlib import Path
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = [
    ("Comfy-Org/stable-diffusion-v1-5-archive", "v1-5-pruned-emaonly-fp16.safetensors", "checkpoints/sd15_base.safetensors"),
    ("Comfy-Org/BiRefNet", "background_removal/birefnet.safetensors", "background_removal/birefnet.safetensors"),
]


def get_json(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return json.load(response)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main():
    manifest = []
    for repository, filename, relative in ARTIFACTS:
        metadata = get_json(f"https://huggingface.co/api/models/{repository}?blobs=true")
        artifact = next(item for item in metadata["siblings"] if item["rfilename"] == filename)
        expected = artifact["lfs"]["sha256"]
        size = artifact["size"]
        if size > 3 * 1024**3:
            raise RuntimeError(f"Unexpected size: {filename}: {size}; download stopped")
        revision = metadata["sha"]
        url = f"https://huggingface.co/{repository}/resolve/{revision}/{filename}"
        target = ROOT / "Models" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            partial = target.with_suffix(target.suffix + ".part")
            for attempt in range(1, 4):
                try:
                    offset = partial.stat().st_size if partial.exists() else 0
                    request = urllib.request.Request(url, headers={"Range": f"bytes={offset}-"} if offset else {})
                    with urllib.request.urlopen(request, timeout=120) as response:
                        append = offset > 0 and response.status == 206
                        received = offset if append else 0
                        last_report = time.monotonic()
                        print(f"Downloading {relative}: {size / 1024**2:.1f} MiB", flush=True)
                        with partial.open("ab" if append else "wb") as output:
                            while block := response.read(4 * 1024 * 1024):
                                output.write(block)
                                received += len(block)
                                if time.monotonic() - last_report > 15:
                                    print(f"  {received / size:.0%} ({received / 1024**2:.0f} MiB)", flush=True)
                                    last_report = time.monotonic()
                    if partial.stat().st_size != size or sha256(partial) != expected:
                        raise RuntimeError(f"Size/SHA256 mismatch: {partial}")
                    os.replace(partial, target)
                    break
                except (OSError, RuntimeError) as error:
                    print(f"Attempt {attempt}: {error}", flush=True)
                    if attempt == 3:
                        raise
        if target.stat().st_size != size or sha256(target) != expected:
            raise RuntimeError(f"Existing artifact failed verification: {target}")
        manifest.append({"file": relative, "bytes": size, "sha256": expected, "repository": repository, "revision": revision, "url": url})
        print(f"Verified: {relative}", flush=True)
        (ROOT / "Logs" / "models-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
