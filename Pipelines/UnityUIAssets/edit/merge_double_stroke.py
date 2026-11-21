"""Merge a doubled outline into one thick stroke: dark-stroke mask -> morphological closing -> repaint on the gray key.
Usage: python merge_double_stroke.py <raw.png> <out_raw.png> <radius>"""
import sys

import numpy as np
from PIL import Image
from scipy import ndimage

src, out, rad = sys.argv[1], sys.argv[2], int(sys.argv[3])
a = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
border = np.concatenate([a[0], a[-1], a[:, 0], a[:, -1]])
key = np.median(border, axis=0)
dist = np.sqrt(((a - key) ** 2).sum(-1))
stroke = dist > 60
yy, xx = np.mgrid[-rad:rad + 1, -rad:rad + 1]
disk = (xx ** 2 + yy ** 2) <= rad ** 2
closed = ndimage.binary_closing(stroke, structure=disk)
# soft edge: blur the closed mask slightly
soft = ndimage.gaussian_filter(closed.astype(np.float64), 1.2)[..., None]
color = np.median(a[stroke], axis=0)
res = key * (1 - soft) + color * soft
Image.fromarray(np.clip(res, 0, 255).astype(np.uint8), 'RGB').save(out)
print('stroke px', int(stroke.sum()), 'closed px', int(closed.sum()), 'color', color.round())
