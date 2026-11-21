# Workflow guide

The four maintained 2D GameArt graphs now include selectable cutout finishing. See [cutout modes and upgrade notes](CUTOUT.md). `Tests/GameArt_Cutout_Finish_Test` compares the previous BiRefNet export with the new stage on the same image; choose your own isolated asset in its LoadImage node. Material modes require an appropriate glyph region and must not be used on the whole green plate.

## Starter workflows

These graphs use built-in nodes. SD 1.5 is the small baseline model; its settings are not interchangeable with FLUX, Qwen, or Z-Image.

| UI JSON under `Workflows/` | Purpose |
|---|---|
| `01_TextToImage.json` | Prompt, checkpoint, sampling, VAE decode, save; 512x512, 20 steps |
| `02_ImageToImage.json` | Reference, 512x512 resize, VAE encode, sampling; denoise 0.55 |
| `03_Inpaint.json` | Masked encode, sampling, composite; preserves pixels outside the mask |
| `04_Game_UI_Asset.json` | Reference img2img, BiRefNet, alpha, 256x256 PNG |
| `05_RemoveBackground.json` | BiRefNet cutout of an existing image without diffusion |
| `06_Upscale_Resize.json` | Lanczos resize to 1024x1024 without extra model weights |
| `05_UI_Asset_Restyle_256.json` | Low-denoise img2img polish and 256x256 RGBA export |

The two files starting with `05` are distinct workflows. `Input/reference.png` is a drawn test asset, and `reference_masked.png` has a transparent region for inpainting. `Scripts/create_workflows.py` recreates starter JSON and sample inputs, so do not run it over edited files.

For the current game-art entry points and the image-conditioned UI asset graph, see [GAME_ART_PIPELINE.md](../GAME_ART_PIPELINE.md). Original/API graphs and interface-visible user copies have separate roles. Keep user changes when synchronizing them.

## UIAssets workflows

The first three graphs are driven by the [reference-to-sprite toolkit](../Pipelines/UnityUIAssets/README.md), which prepares their inputs and masks; they can also be opened in the browser for inspection. They use the `ui` profile.

| UI JSON under `Workflows/UIAssets/` | Purpose |
|---|---|
| `01_Extract_Source.json` | Original RGB plus a traced or estimated alpha mask; no diffusion redraw |
| `02_Repair_Masked.json` | Reference-conditioned local generation composited back into the original crop; protected source pixels retained |
| `03_Rebuild_Object.json` | Coherent whole-object generation, followed by cutout and explicit review |

The toolkit's default edit route builds its Qwen Image Edit 2511 API graph per asset with `Pipelines/UnityUIAssets/edit/qwen_edit_graph.py` (crop → edit on flat gray → raw PNG) and keys and colour-matches the result outside ComfyUI. `Workflows/UIAssets/04_Edit_Isolate_API.json` is one such graph with placeholder values, for MCP submission or inspection: set the image, crop and instruction, then key the raw PNG with `edit/key_bg.py`. It needs the `uiassets` or `qwen` profile and has no separate browser layout; `GameArt/GameArt_QwenEdit2511_v1` is the closest interactive graph (same model family, no crop step).

## Masks and reference images

For inpainting, open Mask Editor from `Load Image`. White marks replacement and black marks preservation. Loading a PNG yields a mask of `1 - alpha`; mask and image dimensions must agree. SD 1.5 examples use dimensions divisible by eight. A specialized inpaint checkpoint can be added for a specific task.

Img2img encodes the reference as the starting latent. Lower denoise, often 0.2-0.4, retains more structure; higher values change it more. Native reference-conditioning graphs such as Klein editing provide a different mechanism from ordinary latent img2img.

## Transparency

BiRefNet estimates a foreground mask. `Invert Mask` converts it for `Join Image with Alpha`, which expects a transparency mask. Inspect fine details and shadows against light and dark backgrounds. To retain a panel's background, bypass cutout and save RGB.

Diffusion does not guarantee clean alpha or exact geometry. Review each asset and refine its mask when necessary. Add ordinary UI labels in the engine; generate baked text only when explicitly requested for branding.

## Optional LoRA and ControlNet wiring

LoRA files belong in `Models/loras/` and must match the base architecture. For checkpoint-based SD workflows, connect checkpoint MODEL/CLIP to `Load LoRA`, then its MODEL to the sampler and CLIP to both text encoders. A starting experiment is strength 0.7 for model and CLIP, with the author's trigger words.

Compatible ControlNet weights belong in `Models/controlnet/`. Connect the control model and control image to `Apply ControlNet`, then route positive/negative conditioning to the sampler. A starting experiment is strength 0.7 over the full sampling range. Newer patch-based models may use `Models/model_patches/` and different author-provided graphs.

No substantial LoRA or ControlNet weight files were found in those shared folders during this cleanup. Node availability alone does not establish model availability.

## Upscale

`06_Upscale_Resize` is ordinary interpolation. Neural upscale additionally requires compatible weights in `Models/upscale_models/` and `Load Upscale Model -> Upscale Image (using Model) -> Image Scale -> Save Image`. No substantial upscale weights were found in that folder. If the upscale node cannot process RGBA, upscale RGB before composing alpha.
