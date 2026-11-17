"""Create small frontend workflows and matching local API graphs from live node schemas."""
import json
from pathlib import Path
import uuid

from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
def load_schemas():
    path = ROOT / "Logs" / "object-info.json"
    if not path.exists():
        raise RuntimeError("Capture the running backend's /object_info response to Logs/object-info.json before rebuilding starter graphs")
    return json.loads(path.read_text(encoding="utf-8"))


class LazySchemas(dict):
    def __getitem__(self, key):
        if not self:
            self.update(load_schemas())
        return super().__getitem__(key)


SCHEMAS = LazySchemas()
PRIMITIVES = {"INT", "FLOAT", "STRING", "BOOLEAN", "COMBO"}
CHECKPOINT = "sd15_base.safetensors"
PROMPT = "game UI button, centered golden star emblem, polished blue rounded square, clean silhouette, front view, soft studio lighting, plain white background, high quality illustration"
NEGATIVE = "blurry, photograph, watermark, text, letters, clutter, cropped, low quality"


class Graph:
    def __init__(self):
        self.api = {}
        self.layout = {}

    def node(self, node_id, kind, title, position, **inputs):
        self.api[str(node_id)] = {"class_type": kind, "inputs": inputs, "_meta": {"title": title}}
        self.layout[str(node_id)] = position
        return node_id

    def export(self, name):
        nodes, links = [], []
        for key, spec in self.api.items():
            schema = SCHEMAS[spec["class_type"]]
            inputs, widgets = [], []
            for section in ("required", "optional"):
                for input_name, descriptor in schema["input"].get(section, {}).items():
                    datatype = descriptor[0]
                    options = descriptor[1] if len(descriptor) > 1 else {}
                    is_widget = isinstance(datatype, list) or datatype in PRIMITIVES
                    value = spec["inputs"].get(input_name)
                    if is_widget:
                        if value is None:
                            choices = datatype if isinstance(datatype, list) else options.get("options", [])
                            value = options.get("default", choices[0] if choices else None)
                        widgets.append(value)
                        if options.get("control_after_generate"):
                            widgets.append("fixed")
                    else:
                        inputs.append({"name": input_name, "type": datatype, "link": None})
            if spec["class_type"] == "LoadImage":
                widgets.append("image")
            outputs = [{"name": output_name, "type": datatype, "links": []}
                       for output_name, datatype in zip(schema["output_name"], schema["output"])]
            height = max(160, 80 + 28 * len(widgets), 70 + 25 * max(len(inputs), len(outputs)))
            if spec["class_type"] in ("CLIPTextEncode", "LoadImage", "PreviewImage", "SaveImage"):
                height = 320
            nodes.append({"id": int(key), "type": spec["class_type"], "title": spec["_meta"]["title"],
                          "pos": self.layout[key], "size": [300, height], "flags": {},
                          "order": len(nodes), "mode": 0, "inputs": inputs, "outputs": outputs,
                          "properties": {"Node name for S&R": spec["class_type"], "cnr_id": "comfy-core", "ver": "0.39.1"},
                          "widgets_values": widgets})
        lookup = {str(node["id"]): node for node in nodes}
        for key, spec in self.api.items():
            target = lookup[key]
            for input_name, value in spec["inputs"].items():
                if not isinstance(value, list):
                    continue
                origin, output_slot = value
                origin_node = lookup[origin]
                input_slot = next(i for i, item in enumerate(target["inputs"]) if item["name"] == input_name)
                datatype = origin_node["outputs"][output_slot]["type"]
                assert target["inputs"][input_slot]["type"] == datatype
                link_id = len(links) + 1
                links.append([link_id, int(origin), output_slot, int(key), input_slot, datatype])
                target["inputs"][input_slot]["link"] = link_id
                origin_node["outputs"][output_slot]["links"].append(link_id)
        workflow = {"id": str(uuid.uuid4()), "revision": 0, "last_node_id": max(node["id"] for node in nodes),
                    "last_link_id": len(links), "nodes": nodes, "links": links, "groups": [],
                    "config": {}, "extra": {"ds": {"scale": 0.6, "offset": [80, 80]}}, "version": 0.4}
        (ROOT / "Workflows" / f"{name}.json").write_text(json.dumps(workflow, indent=2), encoding="utf-8")
        (ROOT / "Workflows" / "API" / f"{name}.json").write_text(json.dumps(self.api, indent=2), encoding="utf-8")
        print(f"{name}: {len(nodes)} nodes, {len(links)} links")


def link(node_id, slot=0):
    return [str(node_id), slot]


def generation(mode):
    graph = Graph()
    graph.node(1, "CheckpointLoaderSimple", "Model: SD 1.5 (replace with compatible checkpoint)", [0, 0], ckpt_name=CHECKPOINT)
    graph.node(2, "CLIPTextEncode", "Positive prompt", [350, 0], text=PROMPT, clip=link(1, 1))
    graph.node(3, "CLIPTextEncode", "Negative prompt", [350, 370], text=NEGATIVE, clip=link(1, 1))
    if mode == "text":
        graph.node(4, "EmptyLatentImage", "Generation resolution: 512 x 512", [0, 380], width=512, height=512, batch_size=1)
        latent, denoise = 4, 1.0
    else:
        graph.node(4, "LoadImage", "Reference image / edit mask", [0, 380], image="reference_masked.png" if mode == "inpaint" else "reference.png")
        if mode == "inpaint":
            graph.node(5, "VAEEncodeForInpaint", "Encode masked image: white mask = replace", [350, 750], pixels=link(4), vae=link(1, 2), mask=link(4, 1), grow_mask_by=6)
            latent, denoise = 5, 0.85
        else:
            graph.node(5, "ImageScale", "Prepare reference: 512 x 512", [0, 750], image=link(4), upscale_method="lanczos", width=512, height=512, crop="center")
            graph.node(6, "VAEEncode", "Encode reference", [350, 750], pixels=link(5), vae=link(1, 2))
            latent, denoise = 6, 0.35 if mode == "game" else 0.55
    graph.node(7, "KSampler", "Generation: denoise controls reference preservation", [720, 0],
               model=link(1), positive=link(2), negative=link(3), latent_image=link(latent),
               seed=20261007, steps=20, cfg=7.0, sampler_name="dpmpp_2m", scheduler="karras", denoise=denoise)
    graph.node(8, "VAEDecode", "Decode image", [1080, 0], samples=link(7), vae=link(1, 2))
    image = 8
    if mode == "inpaint":
        graph.node(9, "ImageCompositeMasked", "Preserve pixels outside edit mask", [1430, 0],
                   destination=link(4), source=link(8), x=0, y=0, resize_source=False, mask=link(4, 1))
        image = 9
    if mode == "game":
        graph.node(9, "LoadBackgroundRemovalModel", "Local background model: BiRefNet", [1080, 380], bg_removal_name="birefnet.safetensors")
        graph.node(10, "RemoveBackground", "Find foreground", [1430, 0], bg_removal_model=link(9), image=link(8))
        graph.node(11, "InvertMask", "Convert foreground mask to transparency mask", [1430, 280], mask=link(10))
        graph.node(12, "JoinImageWithAlpha", "Create RGBA", [1790, 0], image=link(8), alpha=link(11))
        graph.node(13, "ImageScale", "Target asset size: 256 x 256", [2140, 0], image=link(12), upscale_method="lanczos", width=256, height=256, crop="disabled")
        image = 13
    output_x = 2490 if mode == "game" else 1790 if mode == "inpaint" else 1430
    graph.node(20, "PreviewImage", "Preview", [output_x, 0], images=link(image))
    graph.node(21, "SaveImage", "Save PNG to Output", [output_x, 380], images=link(image), filename_prefix={"text": "TextToImage", "image": "ImageToImage", "inpaint": "Inpaint", "game": "Game_UI_Asset"}[mode])
    return graph


def utilities():
    graph = Graph()
    graph.node(1, "LoadImage", "Source image", [0, 0], image="reference.png")
    graph.node(2, "LoadBackgroundRemovalModel", "BiRefNet", [0, 380], bg_removal_name="birefnet.safetensors")
    graph.node(3, "RemoveBackground", "Foreground mask", [350, 0], bg_removal_model=link(2), image=link(1))
    graph.node(4, "InvertMask", "Transparency mask", [350, 280], mask=link(3))
    graph.node(5, "JoinImageWithAlpha", "RGBA image", [700, 0], image=link(1), alpha=link(4))
    graph.node(6, "PreviewImage", "Preview", [1050, 0], images=link(5))
    graph.node(7, "SaveImage", "Save transparent PNG", [1050, 380], images=link(5), filename_prefix="Transparent")
    graph.export("05_RemoveBackground")
    graph = Graph()
    graph.node(1, "LoadImage", "Source image", [0, 0], image="reference.png")
    graph.node(2, "ImageScale", "Resize/upscale without extra model", [350, 0], image=link(1), upscale_method="lanczos", width=1024, height=1024, crop="disabled")
    graph.node(3, "PreviewImage", "Preview", [700, 0], images=link(2))
    graph.node(4, "SaveImage", "Save PNG", [700, 380], images=link(2), filename_prefix="Upscale_Resize")
    graph.export("06_Upscale_Resize")


def main():
    (ROOT / "Workflows" / "API").mkdir(exist_ok=True)
    image = Image.new("RGB", (512, 512), "#e9edf4")
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((95, 90, 417, 422), radius=62, fill="#1a3c7c", outline="#8daae2", width=12)
    draw.rounded_rectangle((108, 102, 404, 405), radius=50, fill="#3168bb")
    draw.polygon([(256, 146), (283, 218), (358, 218), (298, 265), (322, 341),
                  (256, 293), (190, 341), (214, 265), (154, 218), (229, 218)], fill="#f7ca48", outline="#f4ebad", width=6)
    image.save(ROOT / "Input" / "reference.png")
    masked = image.convert("RGBA")
    alpha = Image.new("L", image.size, 255)
    ImageDraw.Draw(alpha).ellipse((165, 155, 347, 335), fill=0)
    masked.putalpha(alpha)
    masked.save(ROOT / "Input" / "reference_masked.png")
    for mode, name in (("text", "01_TextToImage"), ("image", "02_ImageToImage"), ("inpaint", "03_Inpaint"), ("game", "04_Game_UI_Asset")):
        generation(mode).export(name)
    utilities()


if __name__ == "__main__":
    main()
