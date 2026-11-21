"""Builds a Qwen-Image-Edit-2511 API graph: crop of the mockup -> edited isolated asset on flat gray -> raw PNG.
With remove_bg=True it also appends BiRefNet + GameArtCutoutFinish and saves an RGBA candidate; the edit route
(comfy_run.py) passes remove_bg=False and keys the gray background itself with key_bg.py.
Needs the `qwen_edit`, `qwen_encoder` and `qwen_vae` models (model profile `qwen` or `uiassets`)."""


def build(image_name, crop, prompt, seed, prefix, steps=30, cfg=4.0, megapixels=1.0, finish_mode='alpha_only',
          remove_bg=True):
    x, y, w, h = crop
    g = {
        '1': {'class_type': 'UNETLoader', 'inputs': {'unet_name': 'qwen_image_edit_2511_nvfp4.safetensors', 'weight_dtype': 'default'}},
        '2': {'class_type': 'CLIPLoader', 'inputs': {'clip_name': 'qwen_2.5_vl_7b_nvfp4.safetensors', 'type': 'qwen_image', 'device': 'default'}},
        '3': {'class_type': 'VAELoader', 'inputs': {'vae_name': 'qwen_image_vae.safetensors'}},
        '4': {'class_type': 'LoadImage', 'inputs': {'image': image_name}},
        '5': {'class_type': 'ImageCrop', 'inputs': {'image': ['4', 0], 'width': w, 'height': h, 'x': x, 'y': y}},
        '6': {'class_type': 'ImageScaleToTotalPixels', 'inputs': {'image': ['5', 0], 'upscale_method': 'lanczos', 'megapixels': megapixels, 'resolution_steps': 16}},
        '7': {'class_type': 'TextEncodeQwenImageEditPlus', 'inputs': {'clip': ['2', 0], 'prompt': prompt, 'vae': ['3', 0], 'image1': ['6', 0]}},
        '8': {'class_type': 'TextEncodeQwenImageEditPlus', 'inputs': {'clip': ['2', 0], 'prompt': '', 'vae': ['3', 0], 'image1': ['6', 0]}},
        '9': {'class_type': 'ModelSamplingAuraFlow', 'inputs': {'model': ['1', 0], 'shift': 3.1}},
        '10': {'class_type': 'CFGNorm', 'inputs': {'model': ['9', 0], 'strength': 1.0}},
        '11': {'class_type': 'VAEEncode', 'inputs': {'pixels': ['6', 0], 'vae': ['3', 0]}},
        '12': {'class_type': 'KSampler', 'inputs': {'model': ['10', 0], 'seed': seed, 'steps': steps, 'cfg': cfg, 'sampler_name': 'euler',
                                                     'scheduler': 'simple', 'positive': ['7', 0], 'negative': ['8', 0], 'latent_image': ['11', 0], 'denoise': 1.0}},
        '13': {'class_type': 'VAEDecode', 'inputs': {'samples': ['12', 0], 'vae': ['3', 0]}},
        '14': {'class_type': 'SaveImage', 'inputs': {'images': ['13', 0], 'filename_prefix': prefix + '/raw'}},
    }
    if remove_bg:
        g.update({
            '20': {'class_type': 'LoadBackgroundRemovalModel', 'inputs': {'bg_removal_name': 'birefnet.safetensors'}},
            '21': {'class_type': 'RemoveBackground', 'inputs': {'bg_removal_model': ['20', 0], 'image': ['13', 0]}},
            '22': {'class_type': 'InvertMask', 'inputs': {'mask': ['21', 0]}},
            '23': {'class_type': 'GameArtCutoutFinish', 'inputs': {'image': ['13', 0], 'alpha': ['22', 0], 'mode': finish_mode, 'blackpoint': 0.01,
                                                                    'whitepoint': 0.99, 'max_iterations': 1000, 'outer_margin': 2, 'edge_width': 1,
                                                                    'min_component_fraction': 0.0}},
            '24': {'class_type': 'JoinImageWithAlpha', 'inputs': {'image': ['23', 0], 'alpha': ['23', 1]}},
            '25': {'class_type': 'SaveImage', 'inputs': {'images': ['24', 0], 'filename_prefix': prefix + '/rgba'}},
        })
    return g
