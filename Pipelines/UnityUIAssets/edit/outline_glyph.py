"""Recolour a generated glyph and add an outline ring (e.g. a white check mark with a green outline).
Works at 4x the sprite size, then downsizes with premultiplied alpha; also writes <out>_hires.png at 4x.
Usage: python outline_glyph.py <raw.png> <out.png> W H ring_px_at_4x --fill "#ffffff" --outline "#447003" """
import os
import subprocess
import sys

import numpy as np
from PIL import Image
from scipy import ndimage


def hexrgb(s):
    s = s.lstrip('#')
    return np.array([int(s[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float64)


raw, out, W, H, ring = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
fill = hexrgb(sys.argv[sys.argv.index('--fill') + 1]) if '--fill' in sys.argv else np.array([255.0, 255, 250])
outline = hexrgb(sys.argv[sys.argv.index('--outline') + 1]) if '--outline' in sys.argv else np.array([68.0, 112, 3])
big = out + '.big.png'
subprocess.run([sys.executable, os.path.join(os.path.dirname(os.path.abspath(__file__)), 'key_bg.py'), raw, big,
                str(W * 4), str(H * 4), '--pad', str(ring + 2)], check=True, stdin=subprocess.DEVNULL)
a = np.asarray(Image.open(big).convert('RGBA')).astype(np.float64)
alpha = a[..., 3] / 255.0
lum = a[..., :3].mean(-1)
sel = alpha > 0.5
lo, hi = np.percentile(lum[sel], 5), np.percentile(lum[sel], 95)
t = np.clip((lum - lo) / max(hi - lo, 1), 0, 1)[..., None]
glyph = fill * (0.89 + 0.11 * t)
yy, xx = np.mgrid[-ring:ring + 1, -ring:ring + 1]
outer = ndimage.gaussian_filter(ndimage.grey_dilation(alpha, footprint=(xx ** 2 + yy ** 2) <= ring ** 2), 0.8)
rgb = outline * (1 - alpha[..., None]) + glyph * alpha[..., None]
img = np.dstack([rgb, np.maximum(outer, alpha) * 255])
Image.fromarray(np.clip(img, 0, 255).astype(np.uint8), 'RGBA').save(os.path.splitext(out)[0] + '_hires.png')
pm = img.copy()
pm[..., :3] *= img[..., 3:4] / 255
small = np.asarray(Image.fromarray(np.clip(pm, 0, 255).astype(np.uint8), 'RGBA').resize((W, H), Image.LANCZOS)).astype(np.float64)
sa = small[..., 3:4]
small[..., :3] = np.where(sa > 0, small[..., :3] * 255 / np.maximum(sa, 1), 0)
Image.fromarray(np.clip(small, 0, 255).astype(np.uint8), 'RGBA').save(out)
os.remove(big)
print(out)
