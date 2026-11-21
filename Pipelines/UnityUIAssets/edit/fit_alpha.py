"""Fit an edited full-bleed painting to an existing sprite: resize raw to that sprite's size and reuse its alpha.
Usage: python fit_alpha.py <raw.png> <out.png> <sprite_with_alpha.png> [--inset px]"""
import sys

import numpy as np
from PIL import Image

raw, out, alpha_src = sys.argv[1:4]
inset = int(sys.argv[sys.argv.index('--inset') + 1]) if '--inset' in sys.argv else 0
ref = Image.open(alpha_src).convert('RGBA')
im = Image.open(raw).convert('RGB')
if inset:
    im = im.crop((inset, inset, im.width - inset, im.height - inset))
im = im.resize(ref.size, Image.LANCZOS)
Image.fromarray(np.dstack([np.asarray(im), np.asarray(ref)[..., 3]]), 'RGBA').save(out)
print(out, ref.size)
