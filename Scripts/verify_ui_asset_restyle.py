"""Validate and execute the UI polishing graph on transparent and rectangular RGB inputs."""

import copy
import json
from pathlib import Path
import time
from urllib.error import HTTPError
import uuid

import numpy as np
from PIL import Image, ImageDraw

from create_ui_asset_restyle import NAME
from verify_setup import request

ROOT = Path(__file__).resolve().parents[1]


def validate_graph(ui, api, schemas):
    nodes = {node["id"]: node for node in ui["nodes"]}
    assert set(map(str, nodes)) == set(api), "UI and API node sets differ"
    links = {link[0]: link for link in ui["links"]}
    assert len(links) == len(ui["links"]), "Duplicate link IDs"
    for node in nodes.values():
        spec = api[str(node["id"])]
        assert node["type"] == spec["class_type"]
        assert node["mode"] == 0
        index = 0
        for section in ("required", "optional"):
            for name, descriptor in schemas[node["type"]]["input"].get(section, {}).items():
                kind = descriptor[0]
                if isinstance(kind, list) or kind in {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}:
                    assert node["widgets_values"][index] == spec["inputs"][name], (node["type"], name)
                    index += 1
                    if len(descriptor) > 1 and descriptor[1].get("control_after_generate"):
                        index += 1
        for slot, socket in enumerate(node["inputs"]):
            if socket["link"] is None:
                continue
            connection = links[socket["link"]]
            _, source_id, source_slot, target_id, target_slot, kind = connection
            assert (target_id, target_slot) == (node["id"], slot)
            origin = nodes[source_id]["outputs"][source_slot]
            assert origin["type"] == socket["type"] == kind
            assert connection[0] in origin["links"]
            assert spec["inputs"][socket["name"]] == [str(source_id), source_slot]
        for slot, socket in enumerate(node["outputs"]):
            for link_id in socket["links"]:
                assert links[link_id][1:3] == [node["id"], slot]
    assert api["9"]["inputs"]["latent_image"] == ["8", 0], "Sampler must use the encoded source"
    assert api["5"]["class_type"] == "ResizeAndPadImage", "Preparation must preserve aspect ratio"
    assert api["15"]["inputs"]["image"] == ["14", 0], "Alpha must be added at final size"


def execute(ui, graph):
    started = time.monotonic()
    try:
        queued = json.loads(request("/prompt", {
            "prompt": graph, "client_id": str(uuid.uuid4()),
            "extra_data": {"extra_pnginfo": {"workflow": ui}},
        }))
    except HTTPError as error:
        raise RuntimeError(error.read().decode()) from error
    assert not queued.get("node_errors"), queued
    prompt_id = queued["prompt_id"]
    print(f"Running {graph['2']['inputs']['image']}: {prompt_id}", flush=True)
    deadline = started + 300
    while time.monotonic() < deadline:
        history = json.loads(request(f"/history/{prompt_id}"))
        if prompt_id in history:
            entry = history[prompt_id]
            break
        time.sleep(1)
    else:
        raise RuntimeError(f"Timed out: {prompt_id}")
    assert entry["status"]["status_str"] == "success", entry["status"]
    artifacts = entry["outputs"]["16"]["images"]
    assert len(artifacts) == 1
    artifact = artifacts[0]
    assert artifact["type"] == "output"
    path = ROOT / "Output" / artifact["subfolder"] / artifact["filename"]
    with Image.open(path) as image:
        image.load()
        assert image.format == "PNG" and image.mode == "RGBA" and image.size == (256, 256)
        embedded = json.loads(image.info["workflow"])
        assert embedded["id"] == ui["id"]
        alpha = np.asarray(image.getchannel("A"))
        assert alpha.min() < 32 and alpha.max() > 224, (int(alpha.min()), int(alpha.max()))
        foreground = float((alpha > 127).mean())
        assert 0.01 < foreground < 0.90, foreground
        result = {"input": graph["2"]["inputs"]["image"], "prompt_id": prompt_id,
                  "output": str(path.relative_to(ROOT)), "size": list(image.size), "mode": image.mode,
                  "alpha_range": [int(alpha.min()), int(alpha.max())],
                  "foreground_fraction": round(foreground, 4),
                  "seconds": round(time.monotonic() - started, 2)}
    print(json.dumps(result), flush=True)
    return result


def main():
    ui = json.loads((ROOT / "Workflows" / f"{NAME}.json").read_text(encoding="utf-8"))
    api = json.loads((ROOT / "Workflows" / "API" / f"{NAME}.json").read_text(encoding="utf-8"))
    schemas = json.loads(request("/object_info"))
    validate_graph(ui, api, schemas)
    # A non-square fixture exercises white padding instead of stretching/cropping.
    fixture_name = "ui_restyle_rectangular_rgb_test.png"
    fixture_path = ROOT / "Input" / fixture_name
    if not fixture_path.exists():
        fixture = Image.new("RGB", (640, 320), "white")
        draw = ImageDraw.Draw(fixture)
        draw.rounded_rectangle((100, 75, 540, 245), radius=60, fill="#3873ce", outline="#16396b", width=8)
        draw.rounded_rectangle((118, 92, 522, 120), radius=12, fill="#77adf0")
        fixture.save(fixture_path)
    report = {"workflow": NAME, "schema_and_links": "passed", "cases": []}
    for image in ("Default_Full.png", fixture_name):
        graph = copy.deepcopy(api)
        case_ui = copy.deepcopy(ui)
        graph["2"]["inputs"]["image"] = image
        next(node for node in case_ui["nodes"] if node["id"] == 2)["widgets_values"][0] = image
        report["cases"].append(execute(case_ui, graph))
    (ROOT / "Logs" / "ui-asset-restyle-verification.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    print("Transparent PNG and rectangular RGB cases passed.")


if __name__ == "__main__":
    main()
