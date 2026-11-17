"""Build and verify the layered Puzzle Chronicles UI export."""

import argparse
import os
import html
import shutil
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage

import puzzle_ui_v2 as pilot
from puzzle2_shapes import PATHS, SEAMS
from puzzle_cutout import refine_comfy_outputs

ROOT = Path(__file__).resolve().parents[3] / 'outputs/Puzzle2'
SIZE = pilot.MASTER_SIZE
Y, X = np.ogrid[:SIZE[1], :SIZE[0]]
RESAMPLE = Image.Resampling.LANCZOS


def smooth_mask(distance):
    return np.round(np.clip(.5 - distance, 0, 1)*255).astype(np.uint8)


def path(name):
    return pilot.trace_mask(PATHS[name])


def mask_rect(box):
    x, y, r, b = box
    return (X >= x) & (X < r) & (Y >= y) & (Y < b)


def blend(fg, bg, weight):
    weight = np.asarray(weight)[..., None]
    return np.uint8(np.clip(fg*weight + bg*(1-weight), 0, 255).round())


def ramp(values, stops):
    positions, colors = zip(*stops)
    return np.stack([np.interp(values, positions, channel) for channel in zip(*colors)], axis=-1)


def capsule(box):
    x, y, r, b = box
    radius = (b-y)/2
    dx = X - np.clip(X, x+radius, r-radius)
    dy = Y - (y+radius)
    return np.hypot(dx, dy), dy, radius


def bevel_capsule(box, face, rim):
    distance, dy, radius = capsule(box)
    center = np.clip((dy+radius)/(2*radius), 0, 1)
    depth = radius-distance
    rgb = np.broadcast_to(ramp(center, face), (*SIZE[::-1], 3)).copy()
    rim_rgb = ramp(depth, rim)
    angle = np.broadcast_to(np.clip(dy/radius, -1, 1), SIZE[::-1])
    rim_rgb += np.where(angle < 0, -angle*10, -angle*12)[..., None]
    band = np.clip(rim[-1][0]+.5-depth, 0, 1)
    return blend(rim_rgb, rgb, band), smooth_mask(-depth)


def clean_alpha(rgb, alpha):
    core = alpha > 245
    if not np.any(core):
        return rgb
    nearest = ndimage.distance_transform_edt(~core, return_distances=False, return_indices=True)
    band = (alpha > 0) & ~core
    result = rgb.copy()
    result[band] = rgb[nearest[0][band], nearest[1][band]]
    result[alpha == 0] = 0
    return result


def finish_rgba(rgb, alpha):
    return Image.fromarray(np.dstack((clean_alpha(rgb, alpha), alpha)))


def warm_glyph_alpha(rgb, outline):
    """Refine a gold or cream glyph where it overlaps green artwork."""
    allowed = ndimage.binary_dilation(outline > 64, iterations=2)
    r, g, _ = rgb.astype(np.float32).transpose(2, 0, 1)
    warmth = np.clip((r-g+4)/11, 0, 1)
    brightness = np.clip((r-103)/83, 0, 1)
    strength = np.minimum(warmth, brightness)*allowed
    core = largest_region(strength >= .78)
    edge = ndimage.binary_dilation(core, iterations=2)
    alpha = np.where(core, 1, np.minimum(strength, .94)*edge)
    alpha[alpha < .10] = 0
    return np.uint8(np.round(alpha*255))


def generation(name):
    files = sorted((ROOT/'Generated').glob(f'{name}_[0-9]*.png'))
    if not files:
        return None
    refined = ROOT/'Cutout'/files[-1].name
    with Image.open(refined if refined.is_file() else files[-1]) as image:
        return image.convert('RGBA')


class Pack:
    def __init__(self, master):
        self.master = master
        self.entries = {}
        for folder in ('Source', 'Unity', 'Reference', 'Preview'):
            (ROOT/folder).mkdir(parents=True, exist_ok=True)

    def add(self, name, rgb, alpha, *, method='EXTRACT', limit=320, borders=None,
            review='', sample_box=None, full_bleed=False, soft=False):
        rgba = Image.fromarray(np.dstack((rgb, alpha))) if soft else finish_rgba(rgb, alpha)
        box = rgba.getchannel('A').getbbox()
        if not box:
            raise ValueError(f'Empty asset: {name}')
        visible = rgba.crop(box)
        pad = (0, 0) if full_bleed else tuple(max(3, round(side*.07)) for side in visible.size)
        source = Image.new('RGBA', tuple(side+2*p for side, p in zip(visible.size, pad)))
        source.paste(visible, pad)
        scale = min(1, limit/max(source.size))
        unity = source.resize(tuple(round(side*scale) for side in source.size), RESAMPLE)
        source.save(ROOT/f'Source/{name}.png')
        unity.save(ROOT/f'Unity/{name}.png')
        Image.fromarray(self.master).crop(sample_box or box).save(ROOT/f'Reference/{name}.png')
        sliced = None
        if borders:
            sliced = dict(zip(('left','right','top','bottom'),
                              [round((value+pad[i//2])*scale) for i, value in enumerate(borders)]))
            assert sliced['left']+sliced['right'] < unity.width
            assert sliced['top']+sliced['bottom'] < unity.height
        content = unity.getchannel('A').getbbox()
        safe = min(content[0], content[1], unity.width-content[2], unity.height-content[3])
        if safe < 1 and not full_bleed:
            raise ValueError(f'Missing transparent border: {name}')
        self.entries[name] = dict(id=name, method=method, status='REVIEW' if review else 'READY',
            issues=[review] if review else [], source_size=source.size, unity_size=unity.size,
            master_offset=[box[0]-pad[0], box[1]-pad[1]], master_bounds=box, nineSlice=sliced,
            stretch_axes=['x'] if borders else [], alpha_bounds=content, transparent_border_px=safe,
            full_bleed=full_bleed)

    def original(self, name, *, alpha=None, **kwargs):
        self.add(name, self.master, path(name) if alpha is None else alpha, **kwargs)

    def paste(self, canvas, name, *, offset=(0, 0), scale=(1, 1)):
        entry = self.entries[name]
        source = Image.open(ROOT/f'Source/{name}.png').convert('RGBA')
        if scale != (1, 1):
            source = source.resize(tuple(round(side*s) for side, s in zip(source.size, scale)), RESAMPLE)
        canvas.alpha_composite(source, tuple(round(a*s+d) for a, s, d in zip(entry['master_offset'], scale, offset)))


def hud(pack):
    m = pack.master
    distance = np.hypot(X-120.8, Y-87.3)
    rim = ramp(70-distance, [(0,(139,76,16)), (.85,(220,137,21)), (2,(250,187,42)),
        (3.7,(255,218,89)), (5.0,(255,237,143)), (6.3,(246,174,37)),
        (7.6,(229,137,15)), (9,(147,79,12))])
    rim += np.clip((87.3-Y)/70*.7+(120.8-X)/70*.3,-1,1)[..., None]*[19,30,36]
    pack.add('avatar_frame', np.uint8(np.clip(rim, 0, 255)),
        smooth_mask(np.maximum(distance-70, 61.5-distance)), method='RECONSTRUCT')
    circle = smooth_mask(distance-62.1)
    sky = np.broadcast_to(ramp(np.clip((Y-24)/125,0,1), [(0,(37,160,228)),
        (.45,(75,179,230)),(1,(156,214,236))]), (*SIZE[::-1],3)).copy()
    visible_blue = (m[...,2].astype(np.int16)-m[...,0] > 40) & (m[...,1] > 90)
    portrait_body = pilot.trace_mask([(59,111),(64,88),(70,80),(67,64),(72,50),
        (81,40),(86,30),(100,25),(125,23),(143,27),(156,34),(167,47),(171,60),
        (168,72),(166,80),(166,95),(163,103),(156,116),(147,124),(141,134),
        (153,147),(146,154),(80,154),(66,146),(56,129)])
    goggles = pilot.trace_mask([(97,43),(99,33),(111,27),(125,28),(137,30),
        (146,28),(157,36),(157,42),(150,45),(135,40),(129,43),(115,47),(104,47)]) > 0
    portrait = (portrait_body > 0) & (circle > 0) & (~visible_blue | goggles)
    portrait = ndimage.binary_fill_holes(ndimage.binary_closing(portrait, iterations=1))
    portrait &= ~((X < 102) & (Y < 47) & (distance > 56))
    portrait &= ~((m[...,1].astype(np.int16)-m[...,0] > 12) & mask_rect((130,132,165,154)))
    portrait = largest_region(portrait)
    signed = ndimage.distance_transform_edt(~portrait)-ndimage.distance_transform_edt(portrait)
    portrait_alpha = np.minimum(circle, smooth_mask(signed*.55))
    pack.add('avatar_background', np.uint8(sky), circle, method='RECONSTRUCT')
    pack.original('avatar_character', alpha=portrait_alpha)

    track = bevel_capsule((220,49,502,99), [(0,(179,115,69)),(.2,(222,168,123)),
        (1,(228,184,139))], [(0,(169,98,49)),(1.1,(232,159,86)),(3,(255,220,165)),
        (5.5,(255,245,211)),(7,(176,113,62))])
    pack.add('level_track', *track, method='RECONSTRUCT', borders=(29,29,10,10))
    fill = bevel_capsule((236,57,419,91), [(0,(170,224,52)),(.33,(141,209,17)),
        (.75,(86,174,3)),(1,(46,132,1))], [(0,(47,104,4)),(1.1,(77,151,5)),(2,(131,198,30))])
    pack.add('level_fill', *fill, method='RECONSTRUCT', borders=(18,18,4,4))
    star = path('level_star')
    star_rgb = pilot.local_rows(m, (208,51,255,88), (203,208),(253,258))
    pack.add('level_star', star_rgb, star, method='RECONSTRUCT')

    counter = bevel_capsule((815,44,1047,100), [(0,(71,39,22)),(.2,(80,46,28)),
        (.65,(83,49,33)),(1,(73,40,25))], [(0,(107,57,31)),(1,(178,100,48)),
        (2.2,(245,175,99)),(3.6,(255,215,156)),(4.5,(167,99,57))])
    pack.add('currency_counter', *counter, method='RECONSTRUCT', borders=(31,31,8,9))
    pack.original('gem', alpha=pilot.trace_mask(pilot.GEM))
    pack.original('coin', alpha=pilot.ellipse((1095.8,32.1,1175.6,112.5)))
    plus = pilot.ellipse((998.3,41,1059.6,101.1))
    symbol = pilot.trace_mask([(1025,55),(1032,55),(1033,57),(1033,65),(1042,65),
        (1045,67),(1045,74),(1042,76),(1034,76),(1034,85),(1031,87),(1025,87),
        (1023,84),(1023,76),(1015,76),(1012,73),(1012,68),(1015,65),(1023,65),(1023,57)])
    depth = 30-np.hypot(X-1028.7,Y-71.1)
    plus_rgb = ramp(depth,[(0,(38,85,10)),(1,(73,134,16)),(2.4,(151,200,55)),(3.6,(198,232,106)),
                            (4.7,(83,151,11)),(6,(126,184,27))])
    plus_face = np.broadcast_to(ramp(np.clip((Y-43)/56,0,1),[(0,(168,216,43)),(.4,(115,175,17)),
                                                        (1,(50,112,4))]),m.shape)
    plus_rgb = blend(plus_face,plus_rgb,np.clip(depth-5,0,1))
    pack.add('plus_base', plus_rgb, plus, method='RECONSTRUCT')
    pack.original('plus_symbol', alpha=symbol)
    pack.original('plus_complete', alpha=plus)


def menu(pack):
    m = pack.master
    for name in ('menu_panel', 'menu_badge', 'museum_glyph'):
        rgb, alpha = pilot.make_asset(name, m)
        kwargs = {'borders':(68,79,17,21), 'limit':640} if name == 'menu_panel' else {}
        if name == 'museum_glyph':
            alpha = warm_glyph_alpha(m, alpha)
        pack.add(name, rgb, alpha, method='EXTRACT' if name == 'museum_glyph' else 'RECONSTRUCT', **kwargs)
    pin = pilot.cut(path('map_glyph'), [pilot.ellipse((819,448,842,472))])
    pack.original('map_glyph', alpha=warm_glyph_alpha(m, pin))
    cards = path('collection_glyph')
    front = pilot.trace_mask([(783,630),(852,609),(857,609),(861,619),(875,675),(872,684),
        (805,699),(799,697),(785,641)])
    gold = m[...,0].astype(np.int16)-m[...,1] > 3
    cards = np.where((front > 0) | gold,cards,0).astype(np.uint8)
    pack.original('collection_glyph',alpha=cards)
    gear = pilot.cut(path('settings_glyph'), [pilot.ellipse((823,804,848,829))])
    pack.original('settings_glyph', alpha=warm_glyph_alpha(m, gear))
    pack.original('menu_chevron')
    pack.original('museum_art')
    pack.original('collection_art')

    # The map is feathered onto the paper in the reference. Keep the soft
    # color falloff and erase the overlapped title copy and arrow by mask.
    map_outline = pilot.trace_mask([(1087,470),(1099,455),(1110,445),(1119,428),(1126,451),
        (1137,412),(1146,448),(1161,433),(1170,426),(1194,412),(1223,406),
        (1245,421),(1254,429),(1255,447),(1255,476),(1256,505),(1237,521),
        (1211,535),(1175,535),(1138,531),(1119,520),(1128,512),(1127,492),
        (1108,493),(1094,485)])
    area = (map_outline > 0) & ~mask_rect((1086,490,1128,515))
    paper = np.array([255,231,181], dtype=float)
    contrast = np.max(np.abs(m.astype(np.float32)-paper),axis=2)
    edge = np.clip(ndimage.distance_transform_edt(area)/8,0,1)
    core = pilot.trace_mask([(1088,469),(1116,452),(1137,418),(1147,450),(1181,448),
        (1198,457),(1216,452),(1251,466),(1253,488),(1244,512),(1223,529),(1198,533),
        (1152,526),(1121,509),(1128,491),(1093,486)])
    weight = np.maximum(np.clip((contrast-11)/65,0,1), core/255)
    weight *= edge
    flag = mask_rect((1208,428,1252,482)) & (m[...,0] > 100) & (m[...,1] < 160)
    weight[flag & area] = 1
    matte = np.maximum(weight[...,None],.05)
    rgb = np.uint8(np.clip((m-paper*(1-matte))/matte,0,255))
    pack.add('map_art', rgb, np.uint8(weight*255), method='RECONSTRUCT', soft=True)

    leaf_box = mask_rect((1157,770,1278,879))
    rgb, alpha = pigment(m, leaf_box, (255,229,174), (204,162,60))
    pack.add('settings_art', rgb, alpha, method='EXTRACT', soft=True)


def largest_region(mask):
    labels, count = ndimage.label(mask)
    if count <= 1:
        return mask
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    return labels == sizes.argmax()


def pigment(master, region, paper, ink, *, one_shape=False):
    """Recover a flat printed motif from its original paper composite."""
    paper = np.asarray(paper, dtype=float)
    ink = np.asarray(ink, dtype=float)
    delta = paper-ink
    strength = np.sum((paper-master)*delta, axis=2)/np.dot(delta,delta)
    weight = np.clip((strength-.13)/.87,0,1)*region
    weight[weight < .07] = 0
    if one_shape:
        weight[~largest_region(weight > 0)] = 0
    alpha = np.uint8(np.round(weight*255))
    return np.uint8(np.broadcast_to(ink, master.shape)), alpha


def place_generated(image, box, color=None, preserve_aspect=True):
    rgba = np.array(image)
    alpha = rgba[...,3]
    labels, _ = ndimage.label(alpha > 140)
    sizes = np.bincount(labels.ravel())
    sizes[0] = 0
    core = (labels > 0) & (sizes[labels] > sizes.max()*.006)
    keep = ndimage.binary_dilation(core, iterations=4) & (alpha > 20)
    rgba[...,3] = np.where(keep, alpha, 0)
    sprite = Image.fromarray(rgba)
    sprite = sprite.crop(sprite.getchannel('A').getbbox())
    x, y, r, b = box
    if preserve_aspect:
        sprite.thumbnail((r-x,b-y), RESAMPLE)
        x += (r-x-sprite.width)//2
        y += (b-y-sprite.height)//2
    else:
        sprite = sprite.resize((r-x,b-y), RESAMPLE)
    placed = Image.new('RGBA', SIZE)
    placed.paste(sprite, (x,y))
    rgba = np.array(placed)
    rgb = rgba[...,:3]
    if color:
        rgb = color(rgb)
    return rgb, rgba[...,3]


def book(pack):
    m = pack.master
    base, alpha = pilot.make_asset('book_base',m)
    pack.add('book_base', base, alpha, method='RECONSTRUCT', limit=1600)
    ornaments = {
        'ornament_upper_left': ((155,169,263,262),(253,223,180),(216,145,53)),
        'ornament_lower_left': ((78,849,179,940),(253,226,184),(214,147,61)),
        'ornament_upper_right': ((1187,170,1291,255),(254,225,182),(217,151,56)),
        'ornament_lower_right': ((1275,864,1365,940),(252,224,182),(211,141,50)),
    }
    ornament_mask = np.zeros(SIZE[::-1], dtype=bool)
    for name, (box,paper,ink) in ornaments.items():
        region = mask_rect(box)
        rgb, alpha = pigment(m, region, paper, ink, one_shape=True)
        ornament_mask |= alpha > 10
        pack.add(name, rgb, alpha, soft=True)

    # Recreate the hairline rules as aligned overlays so the blank pages can
    # also be used as general-purpose backgrounds.
    for name, curves, width in (
        ('page_rules_left', [[(174,233),(261,186),(445,143),(581,161),(661,170),(708,205)],
                            [(138,936),(283,924),(476,896),(609,912),(683,937),(716,972)]], 2.2),
        ('page_rules_right', [[(727,219),(782,163),(897,161),(1000,171),(1171,180),(1267,221)],
                             [(729,966),(764,919),(860,898),(952,910),(1105,927),(1328,937)]], 2.2),
    ):
        alpha = stroke(curves, width, 90)
        pack.add(name, np.uint8(np.broadcast_to((208,137,63), m.shape)), alpha,
                 method='RECONSTRUCT', limit=900, soft=True)

    left_rgb, left = pilot.make_asset('page_left_surface',m)
    right = pilot.trace_mask(pilot.RIGHT)
    left_ink = mask_rect((77,850,181,941)) | mask_rect((153,169,265,261))
    right_ink = mask_rect((1186,168,1291,258)) | mask_rect((1270,861,1367,942))
    left_rules = Image.open(ROOT/'Source/page_rules_left.png').getchannel('A')
    right_rules = Image.open(ROOT/'Source/page_rules_right.png').getchannel('A')
    for name, page, rgb, ink, rule, extra in (
        ('left',left,left_rgb,left_ink,left_rules,(120,891,714,945)),
        ('right',right,m,right_ink,right_rules,(738,218,1342,905)),
    ):
        rule_image = Image.new('L',SIZE)
        rule_image.paste(rule,tuple(pack.entries[f'page_rules_{name}']['master_offset']))
        rules = ndimage.binary_dilation(np.asarray(rule_image)>10,iterations=6)
        for extra_box in (((164,150,694,236),) if name == 'left' else ((749,159,1285,217),(738,904,1366,945))):
            rules |= mask_rect(extra_box)
        repair = (ink | rules | mask_rect(extra)) & (page > 0)
        if name == 'left':
            repair |= ornament_mask & (page > 0)
        # Start from the unoccluded paper, excluding the cream bevel along
        # the edge. Keep actual color in exposed areas and fit missing parts.
        inner = ndimage.binary_erosion(page > 240, iterations=7)
        samples = inner & ~ndimage.binary_dilation(repair,iterations=8) & (rgb[...,0] > 241) & (rgb[...,1] > 200)
        field = repair_paper(rgb, repair & inner, samples)
        # Preserve the page's bevel while keeping isolated warm paper grain.
        grain = np.random.default_rng(5512).normal(0,.6,SIZE[::-1])
        shade = np.array(field,dtype=np.float32)
        core = repair & inner
        shade[core] = np.clip(shade[core], [241,194,139], [255,235,203])+grain[core,None]
        shade = np.uint8(np.clip(shade,0,255))
        pack.add(f'page_{name}_surface',shade,page,method='RECONSTRUCT',limit=1080)

    bookmark = path('bookmark')
    glyph = path('bookmark_glyph')
    patch = pilot.local_rows(m,(538,976,595,1034),(533,538),(595,599))
    bookmark = np.where(Y >= 948+np.maximum(0,X-532)*.085,bookmark,0).astype(np.uint8)
    pack.add('bookmark',patch,bookmark,method='RECONSTRUCT')
    pack.original('bookmark_glyph',alpha=warm_glyph_alpha(m, glyph))


def stroke(curves, width, opacity):
    scale = 3
    layer = Image.new('L',tuple(side*scale for side in SIZE))
    draw = ImageDraw.Draw(layer)
    for curve in curves:
        points = [curve[0]]
        for segment in curve[1:]:
            if len(segment) == 2:
                points.append(segment)
                continue
            start = np.array(points[-1])
            a,b,end = np.array(segment).reshape(3,2)
            for t in np.linspace(0,1,25)[1:]:
                points.append((1-t)**3*start+3*(1-t)**2*t*a+3*(1-t)*t*t*b+t**3*end)
        draw.line([(round(x*scale),round(y*scale)) for x,y in points],fill=opacity,
                  width=round(width*scale),joint='curve')
    return np.asarray(layer.resize(SIZE,Image.Resampling.BOX))


def leaf_color(rgb):
    r,g,b = rgb.astype(np.float32).transpose(2,0,1)
    return np.uint8(np.clip(np.stack((r*.81+17,g*.73+7,b*.74),axis=-1),0,255))


def repair_paper(rgb, area, samples):
    """Extend the parchment shading without amplifying sparse edge samples."""
    rows, cols = np.nonzero(samples)
    y, x = rows[::7], cols[::7]

    def terms(xx, yy):
        u, v = (xx-np.mean(x))/400, (yy-np.mean(y))/400
        return np.column_stack((np.ones_like(u),u,v,u*u,v*v))

    design = terms(x,y)
    data = rgb[y,x].astype(float)
    penalty = np.diag([0,0,0,120,120])
    coeff = np.linalg.solve(design.T@design+penalty, design.T@data)
    yy, xx = np.nonzero(area)
    estimate = np.clip(terms(xx,yy)@coeff,np.quantile(data,.08,axis=0),np.quantile(data,.92,axis=0))
    field = rgb.copy()
    field[yy,xx] = np.uint8(np.round(estimate))
    weight = ndimage.gaussian_filter(area.astype(np.float32),1.8)
    return blend(field,rgb,weight)


def logo_color(rgb):
    r,g,b = rgb.astype(np.float32).transpose(2,0,1)
    gold = np.clip((r-b-32)/65,0,1) * np.clip((r-g-3)/25,0,1)
    green = np.clip((g-r-4)/50,0,1)
    return np.uint8(np.clip(np.stack((r+gold*19+green*3,g+gold*12+green*17,b-gold*27-green*3),axis=-1),0,255))


def left_page(pack):
    m = pack.master
    for name in ('play_base','play_triangle'):
        if name == 'play_base':
            rgb, alpha = pilot.make_asset(name,m)
            pack.add(name,rgb,alpha,method='RECONSTRUCT',limit=512,borders=(85,85,22,30))
        else:
            pack.original(name, alpha=warm_glyph_alpha(m, path(name)))
    for side, box in [('left',(115,760,194,860)),('right',(623,760,696,860))]:
        sprite = generation(f'leaves_{side}_v2') or generation(f'leaves_{side}')
        if sprite:
            pack.add(f'play_leaves_{side}',*place_generated(sprite,box,leaf_color),method='GENERATE',soft=True)
        else:
            pack.original(f'play_leaves_{side}')

    plaque = path('logo_plaque')
    ribbon = path('logo_ribbon')
    puzzle = path('logo_puzzle')
    logo_leaves = [path('logo_leaves_left'),path('logo_leaves_right')]
    depth = ndimage.distance_transform_edt(plaque > 127)
    gold = ramp(depth,[(0,(127,70,11)),(1,(173,95,15)),(3,(241,158,25)),(5,(255,208,49)),
                       (8,(254,224,110)),(10,(213,128,18)),(11,(47,78,14))])
    leaf_green = ramp(np.clip((Y-188)/210,0,1),[(0,(55,118,34)),(.5,(28,86,28)),(1,(23,68,26))])
    blank = blend(leaf_green,gold,np.clip(depth-10,0,1))
    pack.add('logo_plaque',blank,plaque,method='RECONSTRUCT',limit=600)
    for name, alpha in zip(('logo_ribbon','logo_puzzle','logo_leaves_left','logo_leaves_right'),
                           (ribbon,puzzle,*logo_leaves)):
        if name.startswith('logo_leaves'):
            alpha = pilot.cut(alpha,[plaque])
        if name == 'logo_puzzle':
            alpha = warm_glyph_alpha(m, alpha)
        pack.original(name,alpha=alpha)
    pack.original('logo_master',alpha=np.maximum.reduce([plaque,ribbon,puzzle,*logo_leaves]),limit=600)
    logo = generation('logo')
    if logo:
        pack.add('logo_complete',*place_generated(logo,(182,149,695,412),logo_color,preserve_aspect=False),
                 method='GENERATE',limit=600,soft=True)

    inner,outer = path('puzzle_inner'),path('puzzle_outer')
    border = pilot.cut(outer,[inner])
    white = np.array([255,242,218])
    depth = ndimage.distance_transform_edt(outer > 127)
    side = np.clip((Y-405)/315,0,1)
    bevel = np.uint8(np.clip(white - np.exp(-depth/2)[...,None]*(side*.5+.5)[...,None]*[17,29,39],0,255))
    pack.add('puzzle_border',bevel,border,method='RECONSTRUCT',limit=720)
    seams = stroke(SEAMS,2.0,182)
    seams = np.minimum(seams,inner)
    ink = np.uint8(np.broadcast_to((25,82,131),m.shape))
    pack.add('puzzle_seams',ink,seams,method='RECONSTRUCT',limit=720,soft=True)
    # Preserve the illustrated houses and boat. Close the visible break in
    # the vertical seam and extend the faint right seam to the border.
    extensions = stroke([[(478,602),(477,609,477,620,477,640)],
                         [(598,591),(607,600,613,603,626,600),(655,598),(678,592)],
                         [(293,504),(306,519,301,534,284,533),(275,530,267,539,267,553),
                          (269,575,256,577,244,572),(228,566,221,579,227,590),
                          (239,604,226,615,208,612),(156,610)]],1.65,111)
    art = blend(ink,m,np.minimum(extensions,inner)/255)
    pack.add('puzzle_art',art,inner,method='RECONSTRUCT',limit=720)
    pack.add('puzzle_scene',blend(art,bevel,inner/255),outer,method='RECONSTRUCT',limit=720)
    scene = generation('puzzle_scene')
    if scene:
        pack.add('puzzle_scene_generated',*place_generated(scene,(137,400,697,726),preserve_aspect=False),
                 method='GENERATE',limit=720,soft=True)


def background(pack):
    m = pack.master
    generated = generation('background_v2') or generation('background')
    if generated:
        source = generated.convert('RGB')
        rows = np.asarray(source).astype(np.int16)
        horizon = int(np.argmax(np.mean(rows[...,0]-rows[...,2],axis=1) > 24))
        if not 50 < horizon < source.height*.7:
            horizon = round(source.height*.41)
        source_sky = source.crop((0,0,source.width,horizon))
        source_wood = source.crop((0,horizon+3,source.width,source.height))
        sky = np.asarray(source_sky.resize((SIZE[0],226),RESAMPLE),dtype=np.float32)
        wood = np.asarray(source_wood.resize((SIZE[0],SIZE[1]-226),RESAMPLE),dtype=np.float32)
    else:
        sky = np.asarray(Image.fromarray(m[:226,508:785]).resize((SIZE[0],226),RESAMPLE),dtype=np.float32)
        wood = np.asarray(Image.fromarray(m[1073:]).resize((SIZE[0],SIZE[1]-226),RESAMPLE),dtype=np.float32)
    # Preserve the color at the visible tabletop edges while borrowing
    # continuous grain in the center. Gradually warm the near edge.
    original_bands = np.array([(126,78,60),(147,88,63),(155,91,60),(178,106,76)],dtype=float)
    levels = ramp(np.linspace(0,1,wood.shape[0]),list(zip((0,.35,.72,1),original_bands)))
    grain = (wood-ndimage.gaussian_filter(wood,(18,32,0)))*.55
    wood = np.uint8(np.clip(levels[:,None,:]+grain,0,255))
    sky[...,0] = sky[...,0]*.94
    sky[...,1] = sky[...,1]*1.03
    scene = np.vstack((np.uint8(np.clip(sky,0,255)),wood))
    pack.add('scene_background',scene,np.full(SIZE[::-1],255,dtype=np.uint8),method='GENERATE',
             limit=1600,full_bleed=True,review='Замок и листва перерисованы. Сохранены высота горизонта и тёплый тон стола.')


def assemble(pack):
    canvas = Image.new('RGBA',SIZE)
    layers = []

    def draw(name, shift=(0,0), scale=(1,1)):
        pack.paste(canvas,name,offset=shift,scale=scale)
        layers.append(dict(id=name,offset=shift,scale=scale))

    draw('scene_background')
    for name in ('book_base','bookmark','bookmark_glyph','page_left_surface','page_right_surface',
                 'page_rules_left','page_rules_right','ornament_upper_left','ornament_upper_right',
                 'ornament_lower_left','ornament_lower_right','puzzle_scene','logo_complete',
                 'play_leaves_left','play_leaves_right','play_base','play_triangle'):
        if name in pack.entries:
            draw(name)
    for index, (y,width,glyph,art) in enumerate([
        (222,548,'museum_glyph','museum_art'),(392,564,'map_glyph','map_art'),
        (566,581,'collection_glyph','collection_art'),(742,590,'settings_glyph','settings_art'),
    ]):
        scale = (width/548,1)
        draw('menu_panel',(round(746*(1-scale[0])),y-222),scale)
        draw('menu_badge',(0,y-222))
        draw(glyph)
        draw(art)
        draw('menu_chevron',([0,16,36,42][index],[0,173,348,515][index]))
    for name in ('avatar_background','avatar_character','avatar_frame','level_track','level_fill','level_star',
                 'currency_counter','gem','plus_complete'):
        draw(name)
    draw('currency_counter',(351,0))
    draw('coin')
    draw('plus_complete',(351,0))
    canvas.save(ROOT/'Preview/Assembled.png')
    return layers


def comparisons():
    master = Image.open(ROOT/'Master.png').convert('RGB')
    assembled = Image.open(ROOT/'Preview/Assembled.png').convert('RGB')
    compare = Image.new('RGB',(1448,570),'#22262d')
    font = pilot.preview_font(16)
    draw = ImageDraw.Draw(compare)
    for index,(image,label) in enumerate(((master,'Референс'),(assembled,'Сборка из PNG'))):
        x = index*724
        image.thumbnail((724,543),RESAMPLE)
        compare.paste(image,(x,27))
        draw.text((x+12,4),label,font=font,fill='white')
    compare.save(ROOT/'Preview/Comparison.jpg',quality=95)


def slice_horizontal(image, size, borders):
    left, right = borders['left'], borders['right']
    center = size-left-right
    if center < 1:
        return image.resize((size,image.height),RESAMPLE)
    result = Image.new('RGBA',(size,image.height))
    result.paste(image.crop((0,0,left,image.height)),(0,0))
    middle = image.crop((left,0,image.width-right,image.height))
    result.paste(middle.resize((center,image.height),RESAMPLE),(left,0))
    result.paste(image.crop((image.width-right,0,image.width,image.height)),(size-right,0))
    return result


def qa_preview(pack):
    canvas = Image.new('RGBA',(1390,570),'#22262d')
    d = ImageDraw.Draw(canvas)
    font = pilot.preview_font(16)
    for x, color in [(14,'#faf5e8'),(471,'#223149'),(928,'#c9d0c9')]:
        d.rounded_rectangle((x,33,x+443,551),radius=14,fill=color)
    d.text((14,8),'Ободок и плашка на трёх подложках · 5%, 50% и 100% уровня · растяжение плашек',font=font,fill='white')

    def load(name):
        return Image.open(ROOT/f'Unity/{name}.png').convert('RGBA')

    for index, percent in enumerate((.05,.5,1)):
        x = 14+index*457
        frame = load('avatar_frame')
        canvas.alpha_composite(frame,(x+10,49))
        counter = load('currency_counter')
        wide = slice_horizontal(counter,round(counter.width*(.82+.13*index)),pack.entries['currency_counter']['nineSlice'])
        canvas.alpha_composite(wide,(x+147,92))
        track = load('level_track')
        canvas.alpha_composite(track,(x+105,229))
        fill = load('level_fill')
        width = max(1,round(track.width*.90*percent))
        fill = slice_horizontal(fill,width,pack.entries['level_fill']['nineSlice'])
        canvas.alpha_composite(fill,(x+121,238))
        star = load('level_star')
        canvas.alpha_composite(star,(x+22,211))
        panel = load('menu_panel')
        panel = slice_horizontal(panel,302+index*64,pack.entries['menu_panel']['nineSlice'])
        canvas.alpha_composite(panel,(x+(443-panel.width)//2,300))
        for j,name in enumerate(('menu_chevron','map_glyph','play_leaves_left','play_leaves_right')):
            part = load(name)
            part.thumbnail((86,74),RESAMPLE)
            canvas.alpha_composite(part,(x+43+j*100,473))
    canvas.convert('RGB').save(ROOT/'Preview/Controls.jpg',quality=95)


def cutout_details(results):
    samples = [row['file'] for row in results if row['status'] == 'refined']
    if not samples:
        return
    canvas = Image.new('RGB',(1192,184*((len(samples)+1)//2)+35),'#22262d')
    font = pilot.preview_font(15)
    draw = ImageDraw.Draw(canvas)
    draw.text((12,8),'Тот же кадр и тот же участок кромки крупным планом',font=font,fill='white')
    for i,name in enumerate(samples):
        x,y = (i%2)*596, 35+(i//2)*184
        with Image.open(ROOT/'Generated'/name) as image:
            before = image.convert('RGBA')
        with Image.open(ROOT/'Cutout'/name) as image:
            after = image.convert('RGBA')
        a,b = np.array(before,dtype=np.int16),np.array(after,dtype=np.int16)
        changes = np.abs(a[...,3]-b[...,3]) + np.abs(a[...,:3]-b[...,:3]).max(axis=2)*(b[...,3]/255)
        yy,xx = np.unravel_index(ndimage.uniform_filter(changes.astype(float),size=45).argmax(),changes.shape)
        left, top = np.clip(xx-56,0,before.width-112), np.clip(yy-31,0,before.height-62)
        box = (left,top,left+112,top+62)
        draw.text((x+12,y+4),name.removesuffix('_00001_.png'),font=font,fill='white')
        for j,(sprite,label) in enumerate(((before,'До · BiRefNet'),(after,'После · фильтр края'))):
            x0 = x+12+j*292
            draw.text((x0,y+28),label,font=font,fill='white')
            part = sprite.crop(box).resize((224,124),RESAMPLE)
            tile = Image.new('RGB',part.size,'#f7f2e6')
            ImageDraw.Draw(tile).rectangle((112,0,224,124),fill='#18263a')
            tile.paste(part,(0,0),part)
            canvas.paste(tile,(x0,y+50))
    canvas.save(ROOT/'Preview/CutoutDetails.jpg',quality=95)


def gallery(pack, matte_results=()):
    def panel(title, path):
        return (f'<figure><figcaption>{title}</figcaption><a href="{path}">'
                f'<img loading="lazy" src="{path}" alt="{title}"></a></figure>')

    cards = []
    for asset in pack.entries.values():
        name = asset['id']
        status = asset['status']
        note = html.escape(' '.join(asset['issues']))
        size = ' × '.join(map(str,asset['unity_size']))
        before = f'Before/{name}.png'
        if (ROOT/before).is_file():
            before_title = 'До · предыдущий PNG'
        else:
            before = f'Reference/{name}.png'
            before_title = 'До · референс'
        updated = panel(before_title,before) + panel('После · PNG для Unity',f'Unity/{name}.png')
        cards.append(f'<article><h3>{name}</h3><p>{asset["method"]} · {status} · {size}</p>'
                     f'<div class="row">{updated}</div>'
                     f'<p><a href="Reference/{name}.png">Фрагмент референса</a> {note}</p></article>')

    matte = []
    for row in matte_results:
        name = html.escape(row['file'], quote=True)
        if row['status'] == 'refined':
            detail = f'Изменено пикселей альфы: {row["edge_alpha_changed"]:,}'.replace(',', ' ')
        else:
            detail = 'Использована исходная маска: мало надёжных образцов цвета.'
        comparisons = (panel('До · BiRefNet',f'Generated/{name}')
                       +panel('После · уточнение края',f'Cutout/{name}'))
        matte.append(f'<article><h3>{name.removesuffix(".png")}</h3><div class="row">{comparisons}</div>'
                     f'<p>{detail} · <a href="Generated/raw_{name}">Исходный RGB</a></p></article>')

    run_name = html.escape(ROOT.name)
    page = '''<!doctype html><html lang="ru"><meta charset="utf-8"><meta name="viewport" content="width=device-width">
<title>Puzzle Chronicles</title><style>
body{margin:32px auto;padding:0 18px;max-width:1330px;background:#191d25;color:#f6eddc;font:16px system-ui}
h1{margin:0 0 10px} h3{font-size:16px;overflow-wrap:anywhere} a{color:#a5d8ff}
main{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:14px}
article{background:#252d36;padding:12px 16px;border-radius:9px} .row{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.row a{display:grid;place-items:center;height:138px;background:repeating-conic-gradient(#89909b 0% 25%,#a9afb8 0% 50%) 0/20px 20px}
.row img{max-width:100%;max-height:135px} .compare{width:100%;height:auto}
figure{margin:0;min-width:0} figcaption{font-size:13px;margin:0 0 6px}
</style>'''
    links = ['<a href="Preview/Assembled.png">Собранный экран</a>',
             '<a href="Preview/Controls.jpg">Рамка, валюта и растяжение</a>',
             '<a href="manifest.json">Манифест</a>']
    if (ROOT/'Preview/Edges.jpg').is_file():
        links.append('<a href="Preview/Edges.jpg">Проверка краёв</a>')
    if matte:
        links.append('<a href="#cutout">Тест вырезания фона</a>')
    comparison = ('<a href="Preview/Comparison.jpg"><img class="compare" src="Preview/Comparison.jpg" '
                  'alt="Референс и сборка"></a>')
    page += f'<h1>Puzzle Chronicles · {run_name}</h1><p>{" · ".join(links)}</p>{comparison}'
    if matte:
        page += '<h2 id="cutout">Вырезание фона</h2><p>В обеих колонках одна и та же генерация.</p>'
        if (ROOT/'Preview/CutoutDetails.jpg').is_file():
            page += '<p><a href="Preview/CutoutDetails.jpg">Края крупным планом</a></p>'
        page += f'<main>{"".join(matte)}</main>'
    page += f'<h2>Спрайты Unity</h2><main>{"".join(cards)}</main></html>'
    (ROOT/'Gallery.html').write_text(page,encoding='utf-8')


def main():
    global ROOT
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    parser.add_argument('--baseline', type=Path, help='Previous export directory containing Unity PNGs')
    parser.add_argument('--refine', action='store_true', help='Refine cutouts from the matching ComfyUI RGB output')
    args = parser.parse_args()
    ROOT = args.output.resolve()
    ROOT.mkdir(parents=True, exist_ok=True)
    if args.baseline:
        before = ROOT/'Before'
        before.mkdir(exist_ok=True)
        for image in (args.baseline/'Unity').glob('*.png'):
            shutil.copy2(image,before/image.name)
    matte_results = refine_comfy_outputs(ROOT/'Generated') if args.refine else []
    if matte_results:
        pilot.write_json(ROOT/'cutout_report.json',matte_results)
    master = Image.open(pilot.MASTER).convert('RGB')
    pack = Pack(np.array(master))
    master.save(ROOT/'Master.png')
    hud(pack)
    menu(pack)
    book(pack)
    left_page(pack)
    background(pack)
    layers = assemble(pack)
    comparisons()
    qa_preview(pack)
    cutout_details(matte_results)
    gallery(pack,matte_results)
    assets = list(pack.entries.values())
    pilot.write_json(ROOT/'manifest.json',dict(master_size=SIZE,assets=assets,layers=layers,
        live_ui=['level_value','gem_count','coin_count','play_label','menu_titles','menu_descriptions']))
    pilot.write_json(ROOT/'retry_list.json',[entry['id'] for entry in assets if entry['status']!='READY'])
    print(f'Exported {len(assets)} PNG sprites in Source and Unity')


if __name__ == '__main__':
    main()
