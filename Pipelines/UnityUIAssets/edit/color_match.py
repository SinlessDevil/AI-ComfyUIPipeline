"""Match the colours of a generated glyph to the reference glyph (per-channel mean/std in Lab, opaque pixels only).
Usage: python color_match.py <final.png> <reference.png> x y w h
Reference object pixels = pixels of the crop far from the crop's border colour (the paper behind the glyph)."""
import sys

import numpy as np
from PIL import Image, ImageCms

final, ref, x, y, w, h = sys.argv[1], sys.argv[2], *map(int, sys.argv[3:7])
FLAT = '--flat' in sys.argv  # monochrome glyph: take the reference hue/chroma exactly, keep only lightness shading
srgb = ImageCms.createProfile('sRGB')
lab = ImageCms.createProfile('LAB')
to_lab = ImageCms.buildTransform(srgb, lab, 'RGB', 'LAB')
to_rgb = ImageCms.buildTransform(lab, srgb, 'LAB', 'RGB')

crop = Image.open(ref).convert('RGB').crop((x, y, x + w, y + h))
c = np.asarray(crop).astype(np.float64)
border = np.concatenate([c[0], c[-1], c[:, 0], c[:, -1]])
bg = np.median(border, axis=0)
d = np.sqrt(((c - bg) ** 2).sum(-1))
mask = d > max(60.0, np.percentile(d, 85))
ref_lab = np.asarray(ImageCms.applyTransform(crop, to_lab)).astype(np.float64)[mask]
if '--colors-from' in sys.argv:
    # take the target colours from an already accepted sibling sprite instead of the crop
    sib = Image.open(sys.argv[sys.argv.index('--colors-from') + 1]).convert('RGBA')
    sa = np.asarray(sib)
    ref_lab = np.asarray(ImageCms.applyTransform(Image.fromarray(sa[..., :3]), to_lab)).astype(np.float64)[sa[..., 3] > 200]

im = Image.open(final).convert('RGBA')
a = np.asarray(im)
alpha = a[..., 3]
gen_lab = np.asarray(ImageCms.applyTransform(Image.fromarray(a[..., :3]), to_lab)).astype(np.float64)
sel = alpha > 128
g = gen_lab[sel]
out = gen_lab.copy()
for ch in range(3):
    gm, gs = g[:, ch].mean(), g[:, ch].std() + 1e-6
    rm, rs = ref_lab[:, ch].mean(), ref_lab[:, ch].std() + 1e-6
    # lightness: match mean and spread; chroma (a, b): move the mean, never amplify the spread
    k = min(rs / gs, 1.3) if ch == 0 else (0.0 if FLAT else min(rs / gs, 1.0))
    out[..., ch] = (gen_lab[..., ch] - gm) * k + rm
out = np.clip(out, 0, 255).astype(np.uint8)
rgb = np.asarray(ImageCms.applyTransform(Image.fromarray(out, 'LAB'), to_rgb))
res = np.dstack([rgb, alpha])
Image.fromarray(res, 'RGBA').save(final)
print('matched', final, 'ref px', int(mask.sum()))
