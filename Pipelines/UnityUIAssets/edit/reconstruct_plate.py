"""RECONSTRUCT a stretchable plate (track, pill, counter) from the reference.
Samples the vertical colour profile of a clean stretch of the plate and draws a stadium of the exact sprite size,
so rims and inner shadows keep their thickness around the rounded ends.
Usage: python reconstruct_plate.py <reference.png> <out.png> x y w h col0 col1 W H
  x y w h   crop of the plate in the reference (with a little paper above and below)
  col0 col1 clean column range inside that crop (no label, no fill, no caps)
  W H       sprite size"""
import sys

import numpy as np
from PIL import Image

ref, out = sys.argv[1], sys.argv[2]
x, y, w, h, c0, c1, W, H = map(int, sys.argv[3:11])
SS = 4
crop = np.asarray(Image.open(ref).convert('RGB').crop((x, y, x + w, y + h))).astype(np.float64)
cols = crop[:, c0:c1]
prof = np.median(cols, axis=1)
paper = np.median(np.concatenate([cols[:2].reshape(-1, 3), cols[-2:].reshape(-1, 3)]), axis=0)
rows = np.nonzero(np.sqrt(((prof - paper) ** 2).sum(-1)) > 18)[0]
track = prof[rows.min():rows.max() + 1]
n = len(track)
hs, ws = H * SS, W * SS
yy, xx = np.mgrid[0:hs, 0:ws].astype(np.float64) + 0.5
r = hs / 2.0
cx = np.clip(xx, r, ws - r)
d = r - np.sqrt((xx - cx) ** 2 + (yy - r) ** 2)
edge_row = np.minimum(yy, hs - yy)
t = np.where(d < edge_row, np.where(yy < r, d, hs - d), yy) / hs
idx = np.clip(t * (n - 1), 0, n - 1)
lo = np.floor(idx).astype(int)
hi = np.minimum(lo + 1, n - 1)
fr = (idx - lo)[..., None]
rgb = track[lo] * (1 - fr) + track[hi] * fr
img = np.dstack([rgb, (d > 0) * 255.0])
pm = img.copy()
pm[..., :3] *= img[..., 3:4] / 255
small = pm.reshape(H, SS, W, SS, 4).mean(axis=(1, 3))
a = small[..., 3:4]
small[..., :3] = np.where(a > 0, small[..., :3] * 255 / np.maximum(a, 1e-6), 0)
Image.fromarray(np.clip(small, 0, 255).astype(np.uint8), 'RGBA').save(out)
print(out, 'profile rows', n)
