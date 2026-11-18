"""Local material-guided trimaps for small UI glyphs on green plates."""
import numpy as np
import torch
from scipy import ndimage
from pymatting import estimate_alpha_cf, estimate_foreground_ml, fix_trimap


class GameArtGlyphTrimap:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'image': ('IMAGE',),
            'region_mask': ('MASK',),
            'material': (['warm_gold', 'ivory'],),
            'outer_margin': ('INT', {'default': 2, 'min': 0, 'max': 8}),
            'edge_width': ('INT', {'default': 1, 'min': 1, 'max': 8}),
            'min_component_fraction': ('FLOAT', {'default': 0.0, 'min': 0.0, 'max': 0.1, 'step': 0.005,
                'tooltip': 'Fraction of largest component. Keep zero when fine disconnected details matter.'}),
        }}

    RETURN_TYPES = ('MASK',)
    RETURN_NAMES = ('trimap',)
    FUNCTION = 'build_trimap'
    CATEGORY = 'GameArt/Cutout Lab'
    DESCRIPTION = 'Refine a coarse glyph region using material contrast. For gold or ivory icons on green plates; not for portraits or full UI screenshots.'

    def build_trimap(self, image, region_mask, material, outer_margin, edge_width, min_component_fraction):
        rgb=image.detach().cpu().numpy()[...,:3]*255
        masks=region_mask.detach().cpu().numpy()
        if masks.ndim==2: masks=masks[None]
        if masks.shape[-2:]!=rgb.shape[1:3] or len(masks) not in (1,len(rgb)):
            raise ValueError('Glyph RGB and region mask must have matching canvas sizes and compatible batches.')
        results=[]
        for i,pixels in enumerate(rgb):
            prior=masks[min(i,len(masks)-1)]
            allowed=prior>.05
            if outer_margin:
                allowed=ndimage.binary_dilation(allowed,iterations=outer_margin)
            r,g,b=pixels.transpose(2,0,1)
            if material=='ivory':
                ink=(r>185)&(g>180)&(b>125)&(r-g>-20)&allowed
            else:
                ink=(r-g>3)&(r-b>15)&allowed
            labels,_=ndimage.label(ink)
            counts=np.bincount(labels.ravel()); counts[0]=0
            minimum=max(1,int(counts.max()*min_component_fraction))
            ink&=counts[labels]>=minimum
            foreground=ndimage.binary_erosion(ink,iterations=edge_width)
            background=~ndimage.binary_dilation(ink,iterations=edge_width)
            if not foreground.any() or not background.any():
                raise ValueError('No reliable glyph foreground/background. Choose the correct material, a tighter region, or a smaller edge width.')
            trimap=np.full(prior.shape,.5,dtype=np.float32)
            trimap[foreground]=1
            trimap[background]=0
            results.append(trimap)
        return (torch.from_numpy(np.stack(results)),)


class GameArtCutoutFinish:
    @classmethod
    def INPUT_TYPES(cls):
        return {'required': {
            'image': ('IMAGE',),
            'alpha': ('MASK', {'tooltip': 'Comfy transparency mask: 0 = opaque, 1 = transparent, as used by JoinImageWithAlpha.'}),
            'mode': (['off', 'alpha_only', 'alpha_and_rgb', 'rgb_only', 'gold_on_green', 'ivory_on_green'],),
            'blackpoint': ('FLOAT', {'default': .01, 'min': 0, 'max': .49, 'step': .01}),
            'whitepoint': ('FLOAT', {'default': .99, 'min': .51, 'max': 1, 'step': .01}),
            'max_iterations': ('INT', {'default': 1000, 'min': 10, 'max': 10000}),
            'outer_margin': ('INT', {'default': 2, 'min': 0, 'max': 8}),
            'edge_width': ('INT', {'default': 1, 'min': 1, 'max': 8}),
            'min_component_fraction': ('FLOAT', {'default': 0., 'min': 0., 'max': .1, 'step': .005}),
        }}

    RETURN_TYPES = ('IMAGE', 'MASK')
    RETURN_NAMES = ('image', 'alpha')
    FUNCTION = 'finish'
    CATEGORY = 'GameArt/Cutout'
    DESCRIPTION = ('Refine alpha without preblur; RGB cleanup is optional. Gold/ivory modes require a coarse region around one glyph, excluding its parent rim. '
                   'Use off for exact preservation; rgb_only preserves source alpha. No new models or network calls.')

    def finish(self, image, alpha, mode, blackpoint=.01, whitepoint=.99,
               max_iterations=1000, outer_margin=2, edge_width=1, min_component_fraction=0.):
        if mode == 'off':
            return image, alpha
        if mode not in self.INPUT_TYPES()['required']['mode'][0]:
            raise ValueError('Unknown cutout finish mode.')
        rgb = image.detach().cpu().numpy()[..., :3].astype(np.float64)
        masks = alpha.detach().cpu().numpy()
        if masks.ndim == 2:
            masks = masks[None]
        if masks.shape[-2:] != rgb.shape[1:3] or len(masks) not in (1, len(rgb)):
            raise ValueError('Cutout RGB and transparency mask must have matching canvases and compatible batches.')
        matte = 1. - np.broadcast_to(masks, (len(rgb), *masks.shape[-2:])).astype(np.float64)
        if mode in ('gold_on_green', 'ivory_on_green'):
            material = 'warm_gold' if mode == 'gold_on_green' else 'ivory'
            matte = GameArtGlyphTrimap().build_trimap(image, torch.from_numpy(matte), material,
                        outer_margin, edge_width, min_component_fraction)[0].numpy().astype(np.float64)
        foreground = rgb.copy()
        for i, pixels in enumerate(rgb):
            if mode != 'rgb_only':
                trimap = fix_trimap(matte[i], blackpoint, whitepoint)
                # Completely empty/full masks have no boundary to solve.
                if np.all(trimap == 0) or np.all(trimap == 1):
                    continue
                if not np.any(trimap == 0) or not np.any(trimap == 1):
                    raise ValueError('Cutout matting needs known foreground and background. Adjust blackpoint/whitepoint or use off.')
                if np.any((trimap > 0) & (trimap < 1)):
                    matte[i] = estimate_alpha_cf(pixels, trimap, laplacian_kwargs={'epsilon': 1e-6},
                                                 cg_kwargs={'maxiter': max_iterations})
                else:
                    matte[i] = trimap
            if mode != 'alpha_only':
                foreground[i] = estimate_foreground_ml(pixels, matte[i])
        out_image = image if mode == 'alpha_only' else torch.from_numpy(foreground.astype(np.float32))
        out_alpha = alpha if mode == 'rgb_only' else torch.from_numpy((1. - matte).astype(np.float32))
        return out_image, out_alpha


NODE_CLASS_MAPPINGS={'GameArtGlyphTrimap':GameArtGlyphTrimap, 'GameArtCutoutFinish':GameArtCutoutFinish}
NODE_DISPLAY_NAME_MAPPINGS={'GameArtGlyphTrimap':'GameArt · Glyph Trimap', 'GameArtCutoutFinish':'GameArt · Cutout Finish'}
