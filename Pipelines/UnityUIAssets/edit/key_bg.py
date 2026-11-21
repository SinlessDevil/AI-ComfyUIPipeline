"""Remove a flat generation background by colour key + PyMatting, then trim and fit.

Usage: python key_bg.py <raw.png> <out.png> <target_w> <target_h> [--t1 18] [--t2 60] [--pad 2]
- Background colour = median of the border pixels.
- Background region = pixels connected to the border whose colour distance < t2 (flood fill), so a gray
  hole inside the object stays only if it is enclosed... enclosed holes of background colour are added too
  when they are close to the key colour (t1), which keeps gear/ring holes transparent.
- Trimap: sure background (dist < t1 and connected or enclosed-key), sure foreground (dist > t2), unknown band.
- Alpha: pymatting closed-form; colours: pymatting foreground estimation (removes gray spill on edges).
- Then crop to the alpha bbox and scale to fit target size keeping aspect, centred on a transparent canvas.
"""
import sys

import numpy as np
from PIL import Image
from pymatting import estimate_alpha_cf, estimate_foreground_ml
from scipy import ndimage


def main():
    a = sys.argv[1:]
    src, out, tw, th = a[0], a[1], int(a[2]), int(a[3])
    opt = {'--t1': 18.0, '--t2': 60.0, '--pad': 2, '--hole': 0.0003}
    for k in opt:
        if k in a:
            opt[k] = type(opt[k])(a[a.index(k) + 1])
    img = np.asarray(Image.open(src).convert('RGB')).astype(np.float64)
    h, w, _ = img.shape
    border = np.concatenate([img[0], img[-1], img[:, 0], img[:, -1]])
    key = np.median(border, axis=0)
    dist = np.sqrt(((img - key) ** 2).sum(-1))

    near = dist < opt['--t2']
    lab, _ = ndimage.label(near)
    edge_labels = set(np.unique(np.concatenate([lab[0], lab[-1], lab[:, 0], lab[:, -1]]))) - {0}
    connected = np.isin(lab, list(edge_labels))
    # enclosed holes: regions very close to the key colour and reasonably large
    tight = dist < opt['--t1']
    tl, n = ndimage.label(tight)
    sizes = ndimage.sum(np.ones_like(dist), tl, range(1, n + 1))
    enclosed = np.isin(tl, [i + 1 for i, s in enumerate(sizes) if s > opt['--hole'] * h * w])
    bg_sure = (connected & tight) | enclosed
    fg_sure = ~(connected | enclosed)
    fg_sure = ndimage.binary_erosion(fg_sure, iterations=2)
    bg_sure = ndimage.binary_erosion(bg_sure, iterations=1)
    trimap = np.full((h, w), 0.5)
    trimap[bg_sure] = 0.0
    trimap[fg_sure] = 1.0

    rgb = img / 255.0
    alpha = estimate_alpha_cf(rgb, trimap)
    alpha = np.clip(alpha, 0, 1)
    alpha[alpha < 0.02] = 0
    alpha[alpha > 0.98] = 1
    fg = estimate_foreground_ml(rgb, alpha)
    rgba = np.dstack([np.clip(fg, 0, 1) * 255, alpha * 255]).astype(np.uint8)

    ys, xs = np.nonzero(alpha > 0.02)
    y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
    im = Image.fromarray(rgba, 'RGBA').crop((x0, y0, x1, y1))
    pad = opt['--pad']
    s = min((tw - 2 * pad) / im.width, (th - 2 * pad) / im.height)
    nw, nh = max(1, round(im.width * s)), max(1, round(im.height * s))
    # premultiplied resize to avoid dark/gray fringes
    arr = np.asarray(im).astype(np.float64)
    pm = arr.copy()
    pm[..., :3] *= arr[..., 3:4] / 255.0
    pm_im = Image.fromarray(pm.astype(np.uint8), 'RGBA').resize((nw, nh), Image.LANCZOS)
    r = np.asarray(pm_im).astype(np.float64)
    al = r[..., 3:4]
    r[..., :3] = np.where(al > 0, r[..., :3] * 255.0 / np.maximum(al, 1), 0)
    small = Image.fromarray(np.clip(r, 0, 255).astype(np.uint8), 'RGBA')
    canvas = Image.new('RGBA', (tw, th), (0, 0, 0, 0))
    canvas.paste(small, ((tw - nw) // 2, (th - nh) // 2))
    canvas.save(out)
    print(out, 'key', key.round(), 'bbox', (x0, y0, x1, y1), '->', (nw, nh), 'in', (tw, th))


if __name__ == '__main__':
    main()
