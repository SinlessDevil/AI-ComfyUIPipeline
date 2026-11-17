"""Reference-locked pilot for the Puzzle Chronicles master screen."""

import argparse
import os
import hashlib
import html
import json
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

MASTER_SIZE = (1448, 1086)
MASTER = Path(os.environ.get('PUZZLE_REFERENCE', str(Path(__file__).resolve().parents[3] / 'Input/PuzzleChronicles_UI_Reference.png')))
WORKSPACE = Path(__file__).resolve().parents[3]
V1 = WORKSPACE / 'outputs/PuzzleChronicles_UI_Breakdown/UI_Test_v1/Assets'
OUT = WORKSPACE / 'outputs/Puzzle_UI_v2'

# Cubic curves trace the original silhouettes in master-screen coordinates.
PLAY = [
    (257, 734), (553, 734), (596, 734, 631, 767, 631, 814),
    (631, 866, 603, 904, 552, 905), (253, 905),
    (210, 905, 183, 873, 182, 826), (180, 779, 210, 735, 257, 734),
]
PANEL = [
    (804, 222), (1222, 222), (1260, 222, 1282, 247, 1285, 281),
    (1291, 326), (1298, 356, 1278, 378, 1244, 379), (793, 380),
    (764, 380, 746, 361, 747, 331), (747, 282),
    (747, 248, 769, 222, 804, 222),
]
BADGE = [
    (822, 238), (839, 238), (870, 237, 891, 256, 891, 285),
    (891, 311), (891, 341, 873, 356, 843, 357), (816, 357),
    (788, 357, 770, 340, 770, 311), (770, 286),
    (770, 257, 792, 238, 822, 238),
]
GLYPH = [
    (793, 281), (831, 259), (869, 280), (868, 290), (864, 291),
    (864, 319), (869, 323), (869, 332), (794, 332), (794, 323),
    (800, 319), (800, 291), (794, 290),
]
GEM = [(787, 64), (806, 40), (850, 40), (868, 63), (828, 107)]
LEFT = [
    (146, 172), (160, 158, 388, 127, 479, 128),
    (582, 128, 686, 152, 723, 196), (723, 986),
    (662, 912, 471, 931, 300, 940), (170, 948, 86, 965, 59, 949),
]
RIGHT = [
    (723, 196), (782, 128, 901, 136, 1001, 144),
    (1097, 154, 1268, 158, 1300, 171), (1386, 947),
    (1370, 967, 1251, 950, 1150, 943),
    (941, 929, 792, 914, 723, 986),
]
BOOK = [
    (7, 929), (20, 927), (94, 270), (65, 282), (59, 267),
    (65, 219), (69, 197, 91, 188, 132, 188), (146, 172),
    *LEFT[1:3], *RIGHT[1:3], (1313, 188),
    (1357, 188, 1379, 197, 1383, 222), (1386, 269), (1377, 282),
    (1354, 268), (1437, 928), (1444, 937), (1447, 994),
    (1446, 1015, 1435, 1028, 1415, 1028), (1350, 1028),
    (1338, 1022), (802, 1022), (788, 1042, 768, 1048, 723, 1047),
    (678, 1047, 661, 1040, 648, 1021), (95, 1026),
    (90, 1029), (39, 1029), (17, 1029, 3, 1016, 3, 993),
]


def trace_mask(path):
    scale = 4
    canvas = Image.new('L', tuple(side * scale for side in MASTER_SIZE))
    points = [path[0]]
    for segment in path[1:]:
        if len(segment) == 2:
            points.append(segment)
            continue
        start = np.array(points[-1])
        first, second, end = np.array(segment).reshape(3, 2)
        for t in np.linspace(0, 1, 33)[1:]:
            points.append(tuple((1-t)**3*start + 3*t*(1-t)**2*first + 3*t*t*(1-t)*second + t**3*end))
    ImageDraw.Draw(canvas).polygon([(round(x*scale), round(y*scale)) for x, y in points], fill=255)
    return np.asarray(canvas.resize(MASTER_SIZE, Image.Resampling.BOX)).copy()


def ellipse(box):
    scale = 4
    canvas = Image.new('L', tuple(side * scale for side in MASTER_SIZE))
    ImageDraw.Draw(canvas).ellipse(tuple(round(v * scale) for v in box), fill=255)
    return np.asarray(canvas.resize(MASTER_SIZE, Image.Resampling.BOX)).copy()


def cut(alpha, holes):
    for hole in holes:
        alpha = ((alpha.astype(np.uint16) * (255 - hole) + 127) // 255).astype(np.uint8)
    return alpha


def rect_mask(boxes):
    mask = np.zeros(MASTER_SIZE[::-1], dtype=bool)
    for x0, y0, x1, y1 in boxes:
        mask[y0:y1, x0:x1] = True
    return mask


def paper_repair(master, repair, samples, radius=1.2):
    """Fit a low-frequency color field to unoccluded material pixels."""
    y, x = np.nonzero(samples)
    y, x = y[::4], x[::4]
    values = master[y, x].astype(float)
    center_x, center_y = np.mean(x), np.mean(y)
    scale_x, scale_y = max(np.std(x), 1), max(np.std(y), 1)

    def terms(xx, yy):
        u, v = (xx-center_x)/scale_x, (yy-center_y)/scale_y
        return np.column_stack((np.ones_like(u), u, v, u*u, u*v, v*v, u*u*u, u*u*v, u*v*v, v*v*v))

    design = terms(x, y)
    keep = np.ones(len(values), dtype=bool)
    for _ in range(3):
        coeff = np.linalg.lstsq(design[keep], values[keep], rcond=None)[0]
        residual = np.max(np.abs(design @ coeff - values), axis=1)
        keep = residual <= max(3, np.quantile(residual, .80))
    weight = ndimage.gaussian_filter(ndimage.binary_dilation(repair, iterations=3).astype(np.float32), radius)
    yy, xx = np.nonzero(weight > .003)
    fitted = np.clip(terms(xx, yy) @ coeff, 0, 255)
    result = master.copy()
    w = weight[yy, xx, None]
    result[yy, xx] = np.round(fitted*w + master[yy, xx]*(1-w)).astype(np.uint8)
    return result


def local_rows(master, box, left, right):
    """Rebuild a smooth horizontal fill using adjacent rows of original material."""
    x0, y0, x1, y1 = box
    result = master.copy()
    a = np.median(master[y0:y1, left[0]:left[1]], axis=1)
    b = np.median(master[y0:y1, right[0]:right[1]], axis=1)
    t = np.linspace(0, 1, x1-x0)[None, :, None]
    patch = a[:, None, :] * (1-t) + b[:, None, :] * t
    weight = np.ones(patch.shape[:2], dtype=np.float32)
    for i, value in enumerate((.18, .50, .82)):
        weight[i, :] *= value
        weight[-1-i, :] *= value
        weight[:, i] *= value
        weight[:, -1-i] *= value
    w = weight[..., None]
    result[y0:y1, x0:x1] = np.round(patch*w + master[y0:y1, x0:x1]*(1-w)).astype(np.uint8)
    return result


def make_asset(asset_id, master):
    if asset_id == 'gem':
        return master, trace_mask(GEM)
    if asset_id == 'avatar_frame':
        outer = ellipse((50.5, 17.3, 190.8, 156.1))
        inner = ellipse((59, 25.4, 182.5, 147.7))
        alpha = cut(outer, [inner])
        r, g, b = master.astype(np.int16).transpose(2, 0, 1)
        gold = (alpha > 160) & (r >= g) & (g-b > 24)
        spill = (alpha > 0) & ((b > g) | (g > r) | ((r-g > 38) & (g-b < 22)))
        nearest = ndimage.distance_transform_edt(~gold, return_distances=False, return_indices=True)
        result = master.copy()
        result[spill] = master[nearest[0][spill], nearest[1][spill]]
        return result, alpha
    glyph = trace_mask(GLYPH)
    if asset_id == 'museum_glyph':
        openings = [
            [(813, 292), (826, 292), (826, 319), (813, 319)],
            [(838, 292), (851, 292), (851, 319), (838, 319)],
        ]
        return master, cut(glyph, [trace_mask(hole) for hole in openings])
    if asset_id == 'play_base':
        return local_rows(master, (281, 759, 568, 871), (271, 280), (568, 579)), trace_mask(PLAY)
    if asset_id == 'menu_badge':
        alpha = ndimage.minimum_filter(trace_mask(BADGE), size=3)
        y, x = np.ogrid[:MASTER_SIZE[1], :MASTER_SIZE[0]]
        region = (x >= 785) & (x <= 876) & (y >= 251) & (y <= 341)
        repair = ndimage.binary_dilation(glyph > 64, iterations=3)
        samples = region & ~ndimage.binary_dilation(repair, iterations=3)
        return paper_repair(master, repair, samples), alpha
    if asset_id == 'menu_panel':
        alpha = trace_mask(PANEL)
        repair = rect_mask([(765, 233, 895, 362), (910, 243, 1111, 348),
                            (1123, 246, 1240, 361), (1246, 279, 1273, 321)])
        inner = ndimage.binary_erosion(alpha > 250, iterations=12)
        cream = (master[..., 0] >= 237) & (master[..., 1] >= 200) & (master[..., 2] >= 150)
        samples = inner & cream & ~ndimage.binary_dilation(repair, iterations=4)
        return paper_repair(master, repair & inner, samples), alpha
    if asset_id == 'currency_counter':
        path = [(831, 44), (1024, 44), (1053, 44, 1055, 99, 1025, 99),
                (831, 99), (801, 99, 803, 44, 831, 44)]
        alpha = trace_mask(path)
        result = master.copy()
        strip = np.median(master[44:100, 974:991], axis=1).astype(np.uint8)
        # The gem and plus hide both caps. Extend the adjacent trim and center fill.
        result[44:100, 805:1055] = strip[:, None, :]
        original = rect_mask([(868, 44, 998, 53), (868, 90, 998, 100),
                              (867, 53, 883, 90), (978, 53, 996, 90)])
        result[original] = master[original]
        distance = ndimage.distance_transform_edt(alpha > 127)
        cap = (alpha > 0) & rect_mask([(804, 44, 838, 100), (1019, 44, 1055, 100)])
        for depth, color in [(0, strip[3]), (1, strip[2]), (2, strip[1]), (3, strip[0])]:
            result[cap & (distance > depth) & (distance <= depth+1)] = color
        return result, alpha
    if asset_id == 'page_left_surface':
        alpha = trace_mask(LEFT)
        artwork = trace_mask([(216, 195), (397, 139), (512, 150), (682, 205), (706, 326),
                              (690, 400), (706, 728), (671, 763), (704, 838),
                              (650, 884), (595, 914), (181, 917), (156, 861),
                              (113, 855), (113, 756), (142, 730), (133, 624),
                              (141, 435), (164, 392), (190, 345), (173, 287)]) > 0
        repair = (artwork | rect_mask([(666, 788, 702, 852)])) & (alpha > 0)
        cream = (master[..., 0] >= 238) & (master[..., 1] >= 195) & (master[..., 2] >= 143)
        samples = (alpha > 250) & cream & ~ndimage.binary_dilation(repair, iterations=9)
        result = paper_repair(master, repair, samples, radius=2.5)
        border = (alpha > 0) & ~ndimage.binary_erosion(alpha > 0, iterations=4)
        blue = border & (master[..., 2] > master[..., 0]) & rect_mask([(0, 120, 725, 191)])
        alpha[blue] = 0
        return result, alpha
    if asset_id == 'book_base':
        outer = trace_mask(BOOK)
        pages = [trace_mask(LEFT), trace_mask(RIGHT)]
        # A one-pixel lip under each page avoids hairline seams in Unity.
        holes = [ndimage.minimum_filter(page, size=3) for page in pages]
        alpha = cut(outer, holes)
        result = master.copy()
        # Remove the small cyan fringe on the upper book contour.
        sky = (master[..., 2] > master[..., 0]) & rect_mask([(125, 120, 1310, 196)])
        alpha[sky] = 0
        # The bookmark covers the paper edge and leather. Interpolate the same
        # two materials across the obstruction with row-aligned samples.
        rows = np.arange(945, 1027)
        left = np.median(master[rows, 488:497], axis=1)
        right = np.median(master[rows+2, 626:634], axis=1)
        for x in range(497, 635):
            t = (x-497)/137
            weight = min(1, (x-497)/9, (635-x)/9)
            patch = left*(1-t) + right*t
            result[rows, x] = np.round(patch*weight + master[rows, x]*(1-weight)).astype(np.uint8)
        return result, alpha
    raise ValueError(f'No pilot recipe for {asset_id}')


RECIPES = [
    ('book_base', 'Book', 'RECONSTRUCT', 'book/page_block.png', 1536,
     'Под закладкой восстановлена часть корешка. Правая поверхность вне пилота. Сборку надо проверить в Unity.'),
    ('page_left_surface', 'Book page', 'RECONSTRUCT', 'book/page_left.png', 1024,
     'Большая закрытая область заполнена по соседней бумаге. Текстура в ней мягче оригинала.'),
    ('play_base', 'Play', 'RECONSTRUCT', 'play/base.png', 512, ''),
    ('menu_panel', 'Menu panel', 'RECONSTRUCT', 'menu/panel.png', 640,
     'Правая сторона слегка наклонена в оригинале. 9-slice требует проверки в Unity.'),
    ('menu_badge', 'Menu icons', 'RECONSTRUCT', 'menu/badge.png', 128, ''),
    ('museum_glyph', 'Menu icons', 'EXTRACT', 'menu/museum.png', 96, ''),
    ('currency_counter', 'Currency bar', 'RECONSTRUCT', 'currency/counter.png', 256,
     'Торцы скрыты за изумрудом и плюсом. Их геометрия восстановлена приблизительно.'),
    ('gem', 'Currency gem', 'EXTRACT', 'currency/gem.png', 96, ''),
    ('avatar_frame', 'Avatar', 'EXTRACT', 'avatar/frame.png', 160, ''),
]

# Inset distances from the occupied bounds at master resolution. Padding is
# added later, so the Unity border always includes the transparent margin.
SLICE = {
    'play_base': (85, 85, 22, 30),
    'menu_panel': (68, 79, 17, 21),
    'currency_counter': (31, 31, 10, 12),
}


def export_asset(asset_id, master, root, density, method, issues):
    raw, alpha = make_asset(asset_id, master)
    labels, count = ndimage.label(alpha > 127)
    if not count:
        raise ValueError(f'Empty mask for {asset_id}')
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    minimum = max(3, int(sizes.max() * .0002))
    islands = (labels > 0) & (sizes[labels] < minimum)
    cleaned = alpha.copy()
    cleaned[ndimage.binary_dilation(islands)] = 0
    bounds = Image.fromarray(cleaned).getbbox()
    x0, y0, x1, y1 = bounds
    # Carry nearby opaque RGB through the antialiased band. This avoids a
    # screenshot-colored matte without changing any opaque source pixels.
    core = cleaned == 255
    nearest = ndimage.distance_transform_edt(~core, return_distances=False, return_indices=True)
    edge = (cleaned > 0) & ~core
    rgb = raw.copy()
    rgb[edge] = raw[nearest[0][edge], nearest[1][edge]]
    rgb[cleaned == 0] = 0
    cropped = Image.fromarray(np.dstack((rgb, cleaned))).crop(bounds)
    px, py = (max(3, round(side*.07)) for side in cropped.size)
    source = Image.new('RGBA', (cropped.width+2*px, cropped.height+2*py))
    source.paste(cropped, (px, py))
    scale = min(1.0, density/max(source.size))
    unity = source.resize(tuple(round(side*scale) for side in source.size), Image.Resampling.LANCZOS)
    for folder, image in [
        ('Reference', Image.fromarray(master).crop(bounds)),
        ('Raw', Image.fromarray(raw).crop(bounds)),
        ('Source', source), ('Unity', unity),
    ]:
        target = root / folder
        target.mkdir(exist_ok=True)
        image.save(target / f'{asset_id}.png')
    unchanged = np.all(raw == master, axis=2)
    original_fraction = float(np.mean(unchanged[core]))
    core_count = np.count_nonzero(core)
    left, top, right, bottom = unity.getchannel('A').getbbox()
    border = min(left, top, unity.width-right, unity.height-bottom)
    check = np.asarray(unity)
    near_core = check[..., 3] >= 250
    near = ndimage.distance_transform_edt(~near_core, return_distances=False, return_indices=True)
    soft = (check[..., 3] >= 32) & (check[..., 3] < 250)
    edge_darkening = check[near[0][soft], near[1][soft], :3].mean(axis=1) - check[soft, :3].mean(axis=1)
    contamination = float(np.mean(edge_darkening > 24)) if edge_darkening.size else 0
    issue_list = [issues] if issues else []
    if border < 1 or core_count < 50:
        issue_list.append('Проверить прозрачную границу и размер маски.')
    if contamination > .18 and np.count_nonzero(edge_darkening > 24) > .002 * np.count_nonzero(near_core):
        issue_list.append('Часть полупрозрачного края заметно темнее соседних пикселей. Нужна проверка на светлой подложке.')
    confidence = round(max(.0, min(.98, .87 + .10*original_fraction - .14*bool(issues)
                                     - .20*(border < 1) - .12*contamination)), 2)
    status = 'READY' if not issue_list and confidence >= .85 else 'REVIEW'
    if border < 1 or core_count < 50:
        status = 'REGENERATE'
    slice_data = None
    if asset_id in SLICE:
        l, r, t, b = SLICE[asset_id]
        borders = [round((l+px)*scale), round((r+px)*scale),
                   round((t+py)*scale), round((b+py)*scale)]
        assert borders[0]+borders[1] < unity.width and borders[2]+borders[3] < unity.height
        slice_data = dict(zip(('left', 'right', 'top', 'bottom'), borders))
    return dict(id=asset_id, method=method, status=status, confidence=confidence, issues=issue_list,
                source_crop=list(bounds), master_offset=[x0-px, y0-py], source_size=list(source.size),
                unity_size=list(unity.size), unity_scale=scale, nineSlice=slice_data,
                stretch_axes=['x'] if slice_data else [],
                qa=dict(alpha_bbox=[left, top, right, bottom], transparent_border_px=border,
                        removed_islands=int(np.sum((sizes > 0) & (sizes < minimum))),
                        semi_transparent_dark_fringe_fraction=contamination,
                        original_opaque_rgb_fraction=round(original_fraction, 4)))


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')


def gallery(root, entries):
    colors = {'READY': '#8ee0a6', 'REVIEW': '#f1cc70', 'REGENERATE': '#ff9390'}
    cards = []
    for entry in entries:
        aid = entry['id']
        images = ''.join(
            f'<figure><div class="image"><img src="{folder}/{aid}.png" alt="{label}"></div><figcaption>{label}</figcaption></figure>'
            for folder, label in [('Reference', 'Master crop'), ('Previous', 'V1'), ('Raw', 'V2 raw'), ('Unity', 'V2 Unity PNG')]
        )
        issues = html.escape(' '.join(entry['issues']) or 'По проверкам пилота готов к импорту.')
        size = ' × '.join(map(str, entry['unity_size']))
        cards.append(f'<article id="{aid}"><h2>{aid} <span style="color:{colors[entry["status"]]}">{entry["status"]}</span></h2>'
                     f'<p>{entry["method"]} · {entry["confidence"]:.2f} · {size}</p><div class="row">{images}</div><p>{issues}</p></article>')
    css = '''
    body{font:16px system-ui;background:#151c24;color:#f2eee7;max-width:1280px;margin:36px auto;padding:0 20px}
    a{color:#a1d7ff} article{background:#222d39;padding:16px 22px;margin:20px 0;border-radius:12px}
    h2{font-size:19px} h2 span{font-size:13px;margin-left:10px}
    .row{display:grid;grid-template-columns:repeat(4,1fr);gap:12px} figure{margin:0;text-align:center}
    .image{height:165px;display:grid;place-items:center;background:repeating-conic-gradient(#82878e 0% 25%,#a0a5ab 0% 50%) 0/20px 20px}
    img{max-width:100%;max-height:165px} figcaption{padding-top:6px} p{line-height:1.5}
    @media(max-width:720px){.row{grid-template-columns:repeat(2,1fr)}}
    '''
    page = ('<!doctype html><html lang="ru"><meta charset="utf-8"><title>Puzzle UI v2</title>'
            f'<style>{css}</style><h1>Puzzle Chronicles · UI v2</h1>'
            '<p>Восемь контрольных групп, девять PNG. Confidence — оценка по геометрии, сохранению исходных пикселей и замечаниям. '
            'READY означает готовность к пробному импорту.</p>'
            '<p><a href="Master.png">Master reference</a> · <a href="ContactSheet.jpg">Сравнение стиля</a> · '
            '<a href="retry_list.json">Список на доработку</a></p>' + ''.join(cards) + '</html>')
    (root/'Gallery.html').write_text(page, encoding='utf-8')


def contact_sheet(root, entries):
    font = preview_font(18)
    sheet = Image.new('RGB', (1280, 1120), '#202a35')
    draw = ImageDraw.Draw(sheet)
    draw.text((18, 13), 'Puzzle Chronicles | Master, V1 and V2', font=font, fill='white')
    master = Image.open(root/'Master.png').convert('RGB')
    master.thumbnail((420, 350), Image.Resampling.LANCZOS)
    sheet.paste(master, (18, 48))
    draw.text((18, 378), 'Master reference', font=font, fill='white')
    for index, entry in enumerate(entries):
        if index < 4:
            x, y = 454+(index%2)*408, 48+(index//2)*180
        else:
            x, y = 18+((index-4)%3)*420, 423+((index-4)//3)*180
        draw.text((x, y), entry['id']+'  '+entry['status'], font=font, fill='white')
        for col, folder in enumerate(('Reference', 'Previous', 'Unity')):
            thumb = Image.open(root/folder/f'{entry["id"]}.png').convert('RGBA')
            thumb.thumbnail((124, 110), Image.Resampling.LANCZOS)
            tile = Image.new('RGB', (132, 116), '#90959d')
            ImageDraw.Draw(tile).rectangle((0, 0, 65, 57), fill='#aeb3ba')
            ImageDraw.Draw(tile).rectangle((66, 58, 131, 115), fill='#aeb3ba')
            tile.paste(thumb, ((132-thumb.width)//2, (116-thumb.height)//2), thumb)
            sheet.paste(tile, (x+col*134, y+28))
            draw.text((x+col*134+4, y+146), ('Master', 'V1', 'V2')[col], font=font, fill='white')
    sheet.crop((0, 0, 1280, 790)).save(root/'ContactSheet.jpg', quality=93)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--master', type=Path)
    parser.add_argument('--out', type=Path, default=Path(__file__).parent if Path(__file__).name == 'pipeline_v2.py' else OUT)
    parser.add_argument('--previous', type=Path, default=V1)
    parser.add_argument('--retry', action='store_true')
    args = parser.parse_args()
    root = args.out.resolve()
    root.mkdir(parents=True, exist_ok=True)
    master_path = args.master or (root/'Master.png' if (root/'Master.png').exists() and Path(__file__).name == 'pipeline_v2.py' else MASTER)
    image = Image.open(master_path).convert('RGB')
    if image.size != MASTER_SIZE:
        parser.error(f'The pilot masks use master coordinates {MASTER_SIZE}.')
    master = np.asarray(image)
    digest = hashlib.sha256(master_path.read_bytes()).hexdigest()
    existing = {}
    retry = set()
    if args.retry:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if manifest['master_sha256'] != digest:
            parser.error('Master differs from the saved pilot.')
        existing = {a['id']: a for a in manifest['assets']}
        retry = set(json.loads((root/'retry_list.json').read_text(encoding='utf-8'))['ids'])
    if master_path.resolve() != (root/'Master.png').resolve():
        shutil.copyfile(master_path, root/'Master.png')
    samples = {'green': [(400, 751), (240, 811), (582, 830)],
               'gold': [(299, 739), (262, 887), (108, 22)],
               'cream': [(1105, 364), (975, 356), (120, 730)]}
    profile = {
        'master_sha256': digest, 'master_size': list(MASTER_SIZE),
        'direction': 'Premium illustrated casual puzzle UI, light and warm',
        'palette': {name: [{'xy': [x, y], 'rgb': master[y, x].tolist()} for x, y in points]
                    for name, points in samples.items()},
        'green': 'Warm yellow-green and emerald, avoid teal and dark forest green',
        'gold': 'Warm yellow gold with restrained illustrated highlights',
        'cream': 'Warm ivory, paper and cream rather than neutral white',
        'shadows': 'Soft short downward contact shadows; preserve inner bevel shading',
        'highlights': 'Soft illustrated highlights, avoid plastic or metallic glare',
        'outlines': 'Warm brown, green and gold, preserve source silhouette',
        'normalization': 'Preserve source RGB at opaque edges and untouched regions. Reconstructed fills sample local material from the same master. No global hue shift.',
    }
    write_json(root/'style_profile.json', profile)
    (root/'Previous').mkdir(exist_ok=True)
    entries = []
    for aid, group, method, old_path, density, issues in RECIPES:
        if args.retry and (aid not in retry or existing[aid]['status'] == 'READY'):
            entries.append(existing[aid])
            continue
        entry = export_asset(aid, master, root, density, method, issues)
        entry['group'] = group
        entries.append(entry)
        previous = root/'Previous'/f'{aid}.png'
        if not previous.exists():
            shutil.copyfile(args.previous/old_path, previous)
        print(f'{aid}: {entry["status"]} ({entry["confidence"]:.2f})', flush=True)
    write_json(root/'manifest.json', {'version': 2, 'scope': '8 pilot groups', 'master_sha256': digest,
               'assets': entries, 'live_ui': [{'id': name, 'method': 'LIVE_UI'} for name in
                                             ('labels', 'currency_values', 'level_number', 'progress_value')],
               'book_alignment': 'Place Source layers by master_offset on a shared 1448x1086 canvas. Right page and bookmark are outside the pilot.'})
    write_json(root/'retry_list.json', {'ids': [e['id'] for e in entries if e['status'] in ('REVIEW', 'REGENERATE')]})
    gallery(root, entries)
    contact_sheet(root, entries)





def preview_font(size):
    for name in ['arial.ttf', 'DejaVuSans.ttf']:
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            pass
    return ImageFont.load_default(size=size)


if __name__ == '__main__':
    main()
