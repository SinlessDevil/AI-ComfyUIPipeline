"""Create synthetic smoke-test inputs without replacing user images."""
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]


def main():
    (ROOT / 'Input').mkdir(exist_ok=True)
    image = Image.new('RGBA', (512, 512), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rounded_rectangle((72, 136, 440, 376), radius=76, fill='#237d37', outline='#efb63b', width=14)
    draw.polygon([(222, 200), (222, 310), (320, 255)], fill='#fff1bb')
    for name in ['reference.png', 'Default_Full.png', 'GameArt_Reference_v1_Button.png', 'GameArt_Benchmark_Play_Reference.png']:
        target = ROOT / 'Input' / name
        if not target.exists():
            image.save(target)
    masked = image.copy()
    ImageDraw.Draw(masked).ellipse((226, 210, 300, 284), fill=(0, 0, 0, 0))
    for name in ['reference_masked.png', 'GameArt_Final_Play_Mask_v3.png']:
        target = ROOT / 'Input' / name
        if not target.exists():
            masked.save(target)
    (ROOT / 'Assets').mkdir(exist_ok=True)
    icon = ROOT / 'Assets/comfyui.ico'
    if not icon.exists():
        image.resize((256, 256)).save(icon, sizes=[(32,32), (48,48), (256,256)])
    print('Synthetic demo inputs are ready. Supply your real screen for UI Asset Extract.')


if __name__ == '__main__':
    main()
