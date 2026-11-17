# Gentle PNG restyling to 256x256

This is the legacy SD 1.5 polishing workflow, not the complete screen-to-assets pipeline. UI graph: `Workflows/05_UI_Asset_Restyle_256.json`; interface copy: `Starter/05_UI_Asset_Restyle_256`. It uses installed SD 1.5, BiRefNet, and built-in nodes.

## Use

1. Launch ComfyUI, refresh its workflow list if needed, and open the graph or drag in its UI JSON.
2. Choose your PNG in `Load Image`. The original default is `Input/Default_Full.png`.
3. Prepend an English object description to the positive prompt, for example `a red cartoon submarine, blue glass windows`.
4. Start with denoise 0.30, 20 steps, CFG 5.5, and seed 20261008.
5. Run. Results are saved as `Output/UI_Asset_Restyle_256_*.png`.

## Processing

| Node or stage | Role |
|---|---|
| `CheckpointLoaderSimple` | Load SD 1.5 MODEL, CLIP, and VAE |
| `LoadImage` | Load source RGB and transparency mask |
| `EmptyImage` / `ImageCompositeMasked` | Composite onto white using source alpha, including partially transparent edges |
| `ResizeAndPadImage` | Fit to 512x512 with white padding, preserving aspect ratio |
| Positive/negative `CLIPTextEncode` | Describe the asset/style and undesirable details |
| `VAEEncode` / `KSampler` / `VAEDecode` | Encode the source, perform low-denoise img2img, decode RGB |
| `LoadBackgroundRemovalModel` / `RemoveBackground` | Load BiRefNet and estimate the new foreground mask |
| `InvertMask` | Convert foreground mask to transparency-mask convention |
| `ImageScale` | Resize RGB to 256x256 with Lanczos |
| `JoinImageWithAlpha` | Fit the mask to the output dimensions and compose RGBA |
| `SaveImage` | Save PNG with workflow metadata |

## Parameters

| Parameter | Initial value | Adjustment |
|---|---|---|
| Denoise | 0.30 | Try 0.20-0.25 for more similarity or 0.30-0.35 for stronger changes |
| Steps | 20 | 20-28 is an experiment range; more steps do not guarantee improvement |
| CFG | 5.5 | Try 4.5-6.5; excessive values can produce harsh contours/highlights |
| Output size | 256x256 | Set in the final scale node; retain 512px preparation for SD 1.5 |
| Seed | 20261008, fixed | Keep fixed when comparing settings; change for a new candidate |

Positive prompt:

```text
clean casual mobile game UI asset, polished shape, soft highlights, readable silhouette, smooth shading, vibrant but controlled colors, game-ready icon, high clarity, single isolated object, plain white background
```

Negative prompt:

```text
messy details, extra objects, distorted shape, blurry, noisy, background clutter, text, watermark, photorealistic, cropped
```

Edit the subject, color, material, and defect descriptions per asset. For highlights try `soft highlights, smooth shading`; for a flat appearance try `flat stylized illustration`.

## Limits and verification

The original alpha only helps prepare the white-backed input. VAE and diffusion operate on RGB; BiRefNet predicts new alpha afterward. Shapes, detail counts, shadows, and fine tips can change. Review edges on light and dark backgrounds. For opaque output connect the final RGB scale directly to `SaveImage`.

Other model families require compatible graphs and parameters. See [the current model inventory](MODELS.md) rather than the original installation's proposed-download list. This cleanup installs no new weights.

`Scripts/verify_ui_asset_restyle.py` checks graph links/serialization, submits alpha and RGB examples to a running local backend, and checks PNG format, dimensions, transparency, and workflow metadata. It creates two images and `Logs/ui-asset-restyle-verification.json`.

```powershell
.\ComfyUI\.venv\Scripts\python.exe Scripts\verify_ui_asset_restyle.py
```

`Scripts/create_ui_asset_restyle.py` creates this graph and refuses existing files. Do not use the general starter generator to update user-customized workflows.
