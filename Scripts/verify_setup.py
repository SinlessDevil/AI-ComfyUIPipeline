"""Exercise the six local starter workflows and verify saved PNGs."""
import json
from pathlib import Path
import re
import time
import urllib.error
import urllib.request
import uuid

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
URL = "http://127.0.0.1:8188"
OPENER = urllib.request.build_opener(urllib.request.ProxyHandler({}))


def request(path, data=None):
    payload = json.dumps(data).encode() if data is not None else None
    req = urllib.request.Request(URL + path, data=payload, headers={"Content-Type": "application/json"} if payload else {})
    with OPENER.open(req, timeout=30) as response:
        return response.read()


def main():
    html = request("/").decode()
    assert "<html" in html.lower()
    script_url = re.search(r'<script[^>]+src="([^"]+)"', html).group(1)
    script_url = "/" + script_url.lstrip("./")
    assert len(request(script_url)) > 1000
    schemas = json.loads(request("/object_info"))
    stats = json.loads(request("/system_stats"))
    assert stats["devices"][0]["type"] == "cuda", stats
    assert "sd15_base.safetensors" in schemas["CheckpointLoaderSimple"]["input"]["required"]["ckpt_name"][0]
    background_choices = schemas["LoadBackgroundRemovalModel"]["input"]["required"]["bg_removal_name"]
    choices = background_choices[0] if isinstance(background_choices[0], list) else background_choices[1]["options"]
    assert "birefnet.safetensors" in choices
    manager = json.loads(request("/v2/manager/queue/status"))
    model_directories = {name: json.loads(request(f"/models/{name}")) for name in ("loras", "controlnet", "upscale_models")}
    report = {"ui_http_passed": True, "ui_javascript_passed": True, "gpu": stats["devices"],
              "manager_status": manager, "model_directories": model_directories, "workflows": []}
    for path in sorted((ROOT / "Workflows" / "API").glob("*.json")):
        graph = json.loads(path.read_text(encoding="utf-8"))
        ui_graph = json.loads((ROOT / "Workflows" / path.name).read_text(encoding="utf-8"))
        # Also verify UI widget serialization maps to the exact tested API inputs.
        for node in ui_graph["nodes"]:
            spec = graph[str(node["id"])]
            widget_index = 0
            for section in ("required", "optional"):
                for name, descriptor in schemas[node["type"]]["input"].get(section, {}).items():
                    kind = descriptor[0]
                    if isinstance(kind, list) or kind in {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}:
                        assert node["widgets_values"][widget_index] == spec["inputs"][name], (node["type"], name)
                        widget_index += 1
                        if len(descriptor) > 1 and descriptor[1].get("control_after_generate"):
                            widget_index += 1
        started = time.monotonic()
        try:
            queued = json.loads(request("/prompt", {"prompt": graph, "client_id": str(uuid.uuid4()),
                                                      "extra_data": {"extra_pnginfo": {"workflow": ui_graph}}}))
        except urllib.error.HTTPError as error:
            raise RuntimeError(f"{path.name}: validation failed: {error.read().decode()}") from error
        assert not queued.get("node_errors"), queued
        prompt_id = queued["prompt_id"]
        print(f"Running {path.stem}: {prompt_id}", flush=True)
        while time.monotonic() - started < 600:
            history = json.loads(request(f"/history/{prompt_id}"))
            if prompt_id in history:
                entry = history[prompt_id]
                break
            time.sleep(1)
        else:
            raise RuntimeError(f"{path.name}: workflow timed out")
        assert entry["status"]["status_str"] == "success", entry["status"]
        images = []
        for node in entry["outputs"].values():
            for artifact in node.get("images", []):
                if artifact["type"] != "output":
                    continue
                output = ROOT / "Output" / artifact["subfolder"] / artifact["filename"]
                with Image.open(output) as image:
                    image.load()
                    assert image.format == "PNG"
                    assert "workflow" in image.info
                    details = {"file": str(output.relative_to(ROOT)), "mode": image.mode, "size": image.size}
                    if path.stem in {"04_Game_UI_Asset", "05_RemoveBackground"}:
                        assert image.mode == "RGBA"
                        alpha = np.array(image.getchannel("A"))
                        assert alpha.min() < 32 and alpha.max() > 224, (alpha.min(), alpha.max())
                        details["alpha_range"] = [int(alpha.min()), int(alpha.max())]
                    if path.stem == "03_Inpaint":
                        original = np.array(Image.open(ROOT / "Input" / "reference_masked.png").convert("RGB"))
                        alpha = np.array(Image.open(ROOT / "Input" / "reference_masked.png").getchannel("A"))
                        actual = np.array(image.convert("RGB"))
                        assert np.max(np.abs(actual[alpha == 255].astype(int) - original[alpha == 255].astype(int))) <= 1
                        details["outside_mask_preserved"] = True
                    if path.stem == "04_Game_UI_Asset":
                        assert image.size == (256, 256)
                    images.append(details)
        assert images, "No saved output images"
        result = {"workflow": path.stem, "prompt_id": prompt_id, "seconds": round(time.monotonic() - started, 2),
                  "status": "passed", "outputs": images}
        report["workflows"].append(result)
        (ROOT / "Logs" / "verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        print(json.dumps(result), flush=True)
    print("All six local workflows passed.", flush=True)


if __name__ == "__main__":
    main()
