"""Prepare local ComfyUI jobs using the installed GameArt FLUX graph."""

import argparse
import os
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'outputs/Puzzle2'
BASE = Path(__file__).resolve().parents[1] / 'asset_extract_base.json'

JOBS = {
    'leaves_left': ((116, 754, 198, 866), (512, 640), True,
        'One small leafy sprig, three broad yellow-olive green leaves with subtle veins, '
        'tilting from a joined stem at bottom right toward the upper left. Same silhouette and warm light as reference.'),
    'leaves_right': ((617, 754, 703, 866), (512, 640), True,
        'One small leafy sprig, three broad yellow-olive green leaves with subtle veins, '
        'tilting from a joined stem at bottom left toward the upper right. Same silhouette and warm light as reference.'),
    'puzzle_scene': ((135, 399, 699, 729), (864, 512), True,
        'Recreate this one illustrated Mediterranean coastal village jigsaw icon, exact composition: white and warm pink '
        'buildings with terracotta roofs on the left, tall gold-domed bell tower near the middle, castle on a green cliff '
        'at upper right, deep blue sea and white sailboat lower right. One wide irregular jigsaw silhouette with a thin '
        'ivory bevel. Complete the dark blue curved interlocking seams across the art, keep them thin and readable.'),
    'logo': ((182, 147, 696, 411), (864, 480), True,
        'Recreate the supplied complete logo. Preserve the two exact words "Puzzle Chronicles" in the same cream '
        'chunky serif lettering, same gold trim, dark leaf green plaque, top gold jigsaw piece, two leaf sprigs and '
        'an empty curved gold ribbon underneath. Keep exact spelling. Single front-facing logo, clear silhouette.'),
    'avatar_frame': ((47, 14, 197, 159), (512, 512), True,
        'An empty perfectly round thin illustrated gold portrait ring from this crop, concentric circle, with narrow '
        'bright yellow-gold top-left highlight and deeper warm orange lower-right bevel. Empty center and even rim. '
        'Remove portrait, background and lettering. Match the original ring width closely.'),
    'currency': ((786, 33, 1062, 114), (768, 288), True,
        'An empty wide slim chocolate brown UI counter plate, matching the portion behind the white numerals. '
        'Thin light warm gold edge and darker brown inset bevel. Both rounded caps clean and visible. No writing, '
        'no gem, no plus button, no coin, no symbols. Width four and a half times height.'),
    'background': ((0, 0, 1448, 1086), (1024, 768), False,
        'Reconstruct ONLY the scenery behind the open book and HUD. Completely remove the book, all icons and UI. '
        'The top 20 percent shows a softly defocused blue sky, a small sunlit distant castle at top center, soft blue-green '
        'hills and foliage from the top corners. The lower 80 percent is one continuous empty warm brown wooden '
        'tabletop with subtle horizontal planks, darker at the far edge and warmer toward the bottom foreground. '
        'Match the screenshot palette and height of the horizon precisely. No objects on table. Full bleed.'),
    'leaves_left_v2': ((116, 754, 198, 866), (512, 640), True,
        'Exactly three fresh spring-green leaves on a thin sprig curving toward the bottom right. '
        'One upper leaf points up, one leaf points left, one lower leaf points down left. Bright lime and '
        'grassy greens, very thin green stem, broad clean shapes, restrained veins. No brown, no yellow, no gold.'),
    'leaves_right_v2': ((617, 754, 703, 866), (512, 640), True,
        'Exactly three fresh spring-green leaves on a thin sprig curving toward the bottom left. '
        'One upper leaf points up, one leaf points right, one lower leaf points down right. Bright lime and '
        'grassy greens, very thin green stem, broad clean shapes, restrained veins. No brown, no yellow, no gold.'),
    'background_v2': ((0, 0, 1448, 1086), (1024, 768), False,
        'Empty warm walnut tabletop with subtle horizontal wood grain fills ALL of the LOWER FOUR FIFTHS '
        'of the image, starting at exactly one fifth from the top. A slim horizontal strip ONLY in the top '
        'one fifth shows cyan sky, soft white clouds, distant tiny cream castle at center with red roof, '
        'muted green shrubs and soft hanging leaves in both upper corners. The wood meets the distant scene '
        'on a level straight edge across the entire frame. No objects, book, lettering, badges or foreground decor.'),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=OUT)
    parser.add_argument('--seed-offset', type=int, default=0)
    args = parser.parse_args()
    graphs = args.output / 'Workflows'
    graphs.mkdir(parents=True, exist_ok=True)
    for index, (name, (crop, size, alpha, prompt)) in enumerate(JOBS.items()):
        graph = json.loads(BASE.read_text(encoding='utf-8'))
        x0, y0, x1, y1 = crop
        graph['40']['inputs'].update(x=x0, y=y0, width=x1-x0, height=y1-y0)
        graph['5']['inputs']['value'], graph['6']['inputs']['value'] = size
        graph['9']['inputs']['noise_seed'] = 830121 + index + args.seed_offset
        graph['20']['inputs']['value'] = prompt
        graph['21']['inputs']['value'] = (
            'Match the reference warm illustrated casual puzzle UI. One isolated asset centered, generous empty margin. '
            'Solid neutral medium gray background with the same color in all corners and openings. '
            'Crisp edges, preserve intrinsic bevel and shading. No texture, gradient, vignette, or cast shadow on background.' if alpha else
            'Match the illustrated reference, soft focus and warm daylight. Full frame landscape, no text.')
        graph['22']['inputs']['value'] = alpha
        graph['15']['inputs']['filename_prefix'] = f'JigaSwagPuzzle/{args.output.name}/{name}'
        graph['42']['inputs']['filename_prefix'] = f'JigaSwagPuzzle/{args.output.name}/raw_{name}'
        for node in ('14', '41'):
            graph.pop(node, None)
        (graphs / f'{name}.json').write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
