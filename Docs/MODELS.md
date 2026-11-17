# Model catalog and profiles

All files were matched to local SHA256 on 2026-11-18. Sizes are decimal GB; installation also needs environments, caches, and output space. Exact URLs/revisions/hashes are in [models.lock.json](../Config/models.lock.json).

| Profile | Files | Total GB |
|---|---:|---:|
| `starter` | 2 | 2.577 |
| `ui` | 4 | 8.700 |
| `zimage` | 4 | 8.769 |
| `qwen` | 5 | 30.094 |
| `3d` | 5 | 9.289 |
| `all` | 16 | 57.650 |

Profiles overlap and reuse the same local files. `all` is the union, not the sum of profile totals. The default `ui` profile covers Text Final, Style Final, Retouch Final, and UI Asset Extract. Original SD 1.5 Starter workflows require `starter`. Model presence does not verify a workflow or hardware compatibility.

| Local file under Models | GB | Pinned source |
|---|---:|---|
| `checkpoints/sd15_base.safetensors` | 2.133 | [Comfy-Org/stable-diffusion-v1-5-archive](https://huggingface.co/Comfy-Org/stable-diffusion-v1-5-archive/tree/9cfd069101959ca3828bf9c04a4419870832b74f) |
| `background_removal/birefnet.safetensors` | 0.444 | [Comfy-Org/BiRefNet](https://huggingface.co/Comfy-Org/BiRefNet/tree/884af709e9b795d89dafbf97f29c8d6a2386f5c6) |
| `diffusion_models/flux-2-klein-4b-fp8.safetensors` | 4.071 | [black-forest-labs/FLUX.2-klein-4b-fp8](https://huggingface.co/black-forest-labs/FLUX.2-klein-4b-fp8/tree/5b4408e59397a4a37ccb46afe426d8ed86379441) |
| `text_encoders/qwen_3_4b_fp4_flux2.safetensors` | 3.848 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/tree/5b3abca5c0dc1ecd4eaf3340868d09063fc1c965) |
| `vae/flux2-vae.safetensors` | 0.336 | [Comfy-Org/Flux-2-Klein-4B](https://huggingface.co/Comfy-Org/Flux-2-Klein-4B/tree/5b3abca5c0dc1ecd4eaf3340868d09063fc1c965) |
| `diffusion_models/z_image_turbo_nvfp4.safetensors` | 4.510 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/tree/6fc90a3b1b653e935a0d175e260736de25b84df5) |
| `text_encoders/qwen_3_4b_fp4_mixed.safetensors` | 3.479 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/tree/6fc90a3b1b653e935a0d175e260736de25b84df5) |
| `vae/ae.safetensors` | 0.335 | [Comfy-Org/Z-Image-Turbo](https://huggingface.co/Comfy-Org/Z-Image-Turbo/tree/6fc90a3b1b653e935a0d175e260736de25b84df5) |
| `diffusion_models/qwen_image_2512_nvfp4.safetensors` | 11.640 | [naxneri/Qwen-image-2512-nvfp4](https://huggingface.co/naxneri/Qwen-image-2512-nvfp4/tree/ff66c7645cf015f035e6b7894a65ad90f8378d48) |
| `diffusion_models/qwen_image_edit_2511_nvfp4.safetensors` | 11.640 | [naxneri/Qwen_image_edit_2511_nvfp4](https://huggingface.co/naxneri/Qwen_image_edit_2511_nvfp4/tree/e019a4bd5c2f06d167333d47024fcb85ecff9610) |
| `text_encoders/qwen_2.5_vl_7b_nvfp4.safetensors` | 6.114 | [Comfy-Org/Qwen-Image](https://huggingface.co/Comfy-Org/Qwen-Image/tree/1f12b17be14c89b026c51a91d67c32f84bb047bc) |
| `vae/qwen_image_vae.safetensors` | 0.254 | [Comfy-Org/Qwen-Image](https://huggingface.co/Comfy-Org/Qwen-Image/tree/1f12b17be14c89b026c51a91d67c32f84bb047bc) |
| `diffusion_models/pixal3d_multiview_int8_convrot.safetensors` | 5.585 | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/tree/f37641be376725d324c56626007cc477f1249a69) |
| `clip_vision/dino_v3_L_naf_fp32.safetensors` | 1.215 | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/tree/f37641be376725d324c56626007cc477f1249a69) |
| `vae/trellis_2_shape_vae_bf16.safetensors` | 1.096 | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/tree/f37641be376725d324c56626007cc477f1249a69) |
| `vae/trellis_2_texture_vae_bf16.safetensors` | 0.948 | [Comfy-Org/Pixal3D](https://huggingface.co/Comfy-Org/Pixal3D/tree/f37641be376725d324c56626007cc477f1249a69) |

## Download or verify

```powershell
.\ComfyUI\.venv\Scripts\python.exe Scripts\model_manager.py --profile ui
.\ComfyUI\.venv\Scripts\python.exe Scripts\model_manager.py --profile ui --download
.\ComfyUI\.venv\Scripts\python.exe Scripts\model_manager.py --profile ui --verify
```

Without an action flag the manager only prints the selected files/size. Downloads use immutable source revisions, verify size and SHA256, and preserve existing mismatched files. Partial downloads can resume. A failed checksum quarantines the partial file with an `.invalid` suffix for inspection.

No LoRA, ControlNet, or neural upscale model was present in the captured shared inventory. The weights used by these graphs are sufficient for the captured 2D pipeline; additional weights should be requested for a concrete task. See [hardware compatibility](HARDWARE.md) and [workflow guide](WORKFLOWS.md).
