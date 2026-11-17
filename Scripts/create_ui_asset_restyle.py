"""Create only the UI asset polishing workflow; never overwrite existing graphs."""

import json
from pathlib import Path
import shutil

import create_workflows as workflows

NAME = "05_UI_Asset_Restyle_256"
ROOT = Path(__file__).resolve().parents[1]
POSITIVE = (
    "clean casual mobile game UI asset, polished shape, soft highlights, "
    "readable silhouette, smooth shading, vibrant but controlled colors, "
    "game-ready icon, high clarity, single isolated object, plain white background"
)
NEGATIVE = (
    "messy details, extra objects, distorted shape, blurry, noisy, "
    "background clutter, text, watermark, photorealistic, cropped"
)


def build_graph():
    graph = workflows.Graph()
    node, link = graph.node, workflows.link
    node(1, "CheckpointLoaderSimple", "Модель: установленная SD 1.5", [0, 420],
         ckpt_name="sd15_base.safetensors")
    node(2, "LoadImage", "1. Загрузи свой PNG", [0, 20], image="Default_Full.png")
    node(3, "EmptyImage", "Белая подложка для прозрачных областей", [0, 640],
         width=512, height=512, batch_size=1, color=16777215)
    node(4, "ImageCompositeMasked", "2. Прозрачные области → белый фон", [360, 20],
         destination=link(2), source=link(3), x=0, y=0, resize_source=True, mask=link(2, 1))
    node(5, "ResizeAndPadImage", "3. Вписать в 512×512 без обрезки", [360, 360],
         image=link(4), target_width=512, target_height=512,
         padding_color="white", interpolation="lanczos")
    node(6, "CLIPTextEncode", "4. PROMPT — стиль и описание объекта", [760, 20],
         text=POSITIVE, clip=link(1, 1))
    node(7, "CLIPTextEncode", "NEGATIVE — чего избегать", [760, 400],
         text=NEGATIVE, clip=link(1, 1))
    node(8, "VAEEncode", "5. Картинка → latent (img2img)", [760, 780],
         pixels=link(5), vae=link(1, 2))
    node(9, "KSampler", "6. Полировка — denoise 0.30", [1130, 20],
         model=link(1), positive=link(6), negative=link(7), latent_image=link(8),
         seed=20261008, steps=20, cfg=5.5, sampler_name="dpmpp_2m", scheduler="karras", denoise=0.30)
    node(10, "VAEDecode", "7. Latent → готовая картинка", [1130, 400],
         samples=link(9), vae=link(1, 2))
    node(11, "LoadBackgroundRemovalModel", "BiRefNet — уже установлен", [1130, 780],
         bg_removal_name="birefnet.safetensors")
    node(12, "RemoveBackground", "8. Найти объект / убрать фон", [1520, 20],
         bg_removal_model=link(11), image=link(10))
    node(13, "InvertMask", "Маска прозрачности", [1520, 290], mask=link(12))
    node(14, "ImageScale", "9. Финальный размер: 256×256", [1520, 560],
         image=link(10), upscale_method="lanczos", width=256, height=256, crop="disabled")
    node(15, "JoinImageWithAlpha", "10. Собрать прозрачный RGBA", [1900, 20],
         image=link(14), alpha=link(13))
    node(16, "SaveImage", "11. PNG 256×256 — результат и сохранение", [1900, 290],
         images=link(15), filename_prefix="UI_Asset_Restyle_256")
    return graph


def main():
    ui_path = ROOT / "Workflows" / f"{NAME}.json"
    api_path = ROOT / "Workflows" / "API" / f"{NAME}.json"
    user_path = ROOT / "User" / "default" / "workflows" / "Starter" / f"{NAME}.json"
    for path in (ui_path, api_path, user_path):
        if path.exists():
            raise FileExistsError(f"Refusing to overwrite {path}")
    workflows.SCHEMAS = json.loads((ROOT / "Logs" / "restyle-object-info.json").read_text(encoding="utf-8"))
    build_graph().export(NAME)
    ui = json.loads(ui_path.read_text(encoding="utf-8"))
    ui["groups"] = [
        {"title": "ВХОД · твой PNG и подготовка", "bounding": [-25, -60, 725, 1050],
         "color": "#3f789e", "font_size": 24, "flags": {}},
        {"title": "IMG2IMG · prompt + мягкая полировка", "bounding": [735, -60, 725, 1050],
         "color": "#7564a2", "font_size": 24, "flags": {}},
        {"title": "ВЫХОД · прозрачный PNG 256×256", "bounding": [1495, -60, 735, 1050],
         "color": "#3e8a6a", "font_size": 24, "flags": {}},
    ]
    ui["extra"]["ds"] = {"scale": 0.52, "offset": [70, 110]}
    ui_path.write_text(json.dumps(ui, ensure_ascii=False, indent=2), encoding="utf-8")
    user_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(ui_path, user_path)
    print(f"UI workflow: {ui_path}\nComfyUI library: Starter/{NAME}")


if __name__ == "__main__":
    main()
