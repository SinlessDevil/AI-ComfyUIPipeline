"""Refine a ComfyUI cutout using its matching original RGB image."""

from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage


def nearest_indices(mask):
    return ndimage.distance_transform_edt(~mask, return_distances=False, return_indices=True)


def refine_cutout(raw, coarse):
    """Estimate coverage and remove background RGB in a narrow contour band."""
    if raw.size != coarse.size:
        raise ValueError('The RGB image and ComfyUI cutout must have matching dimensions.')
    original = np.asarray(raw.convert('RGB'), dtype=np.float32)
    previous = np.asarray(coarse.getchannel('A'), dtype=np.float32) / 255
    radius = max(2, min(5, round(min(raw.size)*.006)))
    solid = previous >= .90
    visible = previous >= .36
    foreground = ndimage.binary_erosion(solid, iterations=radius)
    dist = ndimage.distance_transform_edt(~visible)
    backdrop = (previous <= .035) & (dist >= radius+2) & (dist <= radius*4+6)
    if foreground.sum() < 24 or backdrop.sum() < 64:
        return coarse.copy(), {'status': 'insufficient_samples'}

    # RGB in the exported cutout is the original composite. Use the cleanest
    # samples around the contour to solve C = A*F + (1-A)*B in that band.
    bg_center = np.median(original[backdrop], axis=0)
    bg_error = np.linalg.norm(original-bg_center, axis=2)
    spread = float(np.percentile(bg_error[backdrop], 75))
    if spread > 38:
        return coarse.copy(), {'status': 'varying_background', 'background_spread': round(spread, 2)}

    reliable_bg = backdrop & (bg_error <= max(12, spread*2.2))
    if reliable_bg.sum() < 64:
        return coarse.copy(), {'status': 'insufficient_background'}
    distance_fg, foreground_index = ndimage.distance_transform_edt(~foreground, return_indices=True)
    background_index = nearest_indices(reliable_bg)
    band = ~foreground & (dist <= radius+2) & (distance_fg <= radius*2+3)
    rows, cols = np.nonzero(band)
    pixels = original[rows, cols]
    fg = original[tuple(foreground_index[:, rows, cols])]
    bg = original[tuple(background_index[:, rows, cols])]
    vec = fg-bg
    contrast = np.linalg.norm(vec, axis=1)
    estimate = np.sum((pixels-bg)*vec, axis=1) / np.maximum(contrast**2, 1)
    estimate = np.clip(estimate, 0, 1)
    error = np.linalg.norm(pixels-bg-estimate[:,None]*vec, axis=1)
    old = previous[rows, cols]
    confidence = np.clip((contrast-30)/45, 0, 1) * np.clip((28-error)/20, 0, 1)
    # Outside the detected shape, grow only when there is both an existing
    # soft edge and clear evidence of foreground in the original colors.
    confidence *= np.where(estimate > old, np.clip((old-.04)/.35,0,1), 1)
    # Smooth only the correction, preserving the original mask and its
    # hard shapes. This avoids speckled pixels where nearest samples switch.
    adjustment = np.zeros_like(previous)
    adjustment[rows, cols] = confidence*(estimate-old)
    adjustment = ndimage.gaussian_filter(adjustment, sigma=.65)
    current = np.clip(old+adjustment[rows, cols], 0, 1)
    clear = (current < .035) & (confidence > .4)
    current[clear] = 0
    alpha = previous.copy()
    alpha[rows, cols] = current

    recovered = (pixels-(1-current[:,None])*bg) / np.maximum(current[:,None], .08)
    low_alpha = np.clip(current/.28, 0, 1)[:,None]
    recovered = np.clip(recovered, 0, 255)*low_alpha+fg*(1-low_alpha)
    strength = (confidence * np.clip((1-current)/.18,0,1))[:,None]
    rgb = original.copy()
    rgb[rows, cols] = pixels*(1-strength)+recovered*strength
    rgb[alpha <= .001] = 0
    rgba = np.dstack((np.uint8(np.clip(rgb, 0, 255).round()), np.uint8(np.clip(alpha,0,1)*255+.5)))
    return Image.fromarray(rgba), {
        'status': 'refined',
        'background_spread': round(spread, 2),
        'edge_alpha_changed': int(np.count_nonzero(np.abs(alpha-previous) > 8/255)),
        'retained_alpha_percent': round(float(alpha.sum()/previous.sum()*100), 2),
    }


def refine_comfy_outputs(folder):
    output = folder.parent / 'Cutout'
    output.mkdir(exist_ok=True)
    results = []
    for raw_file in sorted(folder.glob('raw_*.png')):
        cutout_file = folder / raw_file.name.removeprefix('raw_')
        if not cutout_file.is_file():
            continue
        with Image.open(cutout_file) as before, Image.open(raw_file) as raw:
            if 'A' not in before.getbands():
                continue
            refined, metrics = refine_cutout(raw, before)
            refined.save(output / cutout_file.name)
        results.append({'file':cutout_file.name, **metrics})
    return results
