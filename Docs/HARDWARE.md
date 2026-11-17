# Hardware and compatibility

The source workstation has Windows x86_64, NVIDIA RTX 5080 with 16 GB VRAM, and approximately 32 GB RAM. The pinned environment uses CUDA 13.0 PyTorch wheels. The installer verifies CUDA operation through an actual tensor computation, but this does not establish that every optional graph fits memory.

The default `ui` profile contains the FLUX.2 Klein FP8 diffusion weights, its FP4 text encoder, its VAE, and BiRefNet. It was used by the existing UI pipeline on the reference workstation. Start with one image per batch. High resolution and multiple references increase memory requirements.

The Qwen and Z-Image comparison profiles contain NVFP4 weights selected for the reference hardware. An older NVIDIA architecture, different GPU vendor, macOS, or CPU-only machine may need different weights, kernels, offload settings, and a matching workflow. Do not infer compatibility from a filename alone. The full 57.65 GB inventory describes disk content, not VRAM demand.

For another device, inspect its GPU model, VRAM/RAM, driver, disk space, and intended task before downloading. Use the [official ComfyUI installation guide](https://docs.comfy.org/installation/manual_install) and each model's source linked in the lock file. Keep an alternate hardware profile separate from the captured Windows/NVIDIA lock files and validate a real output there.

The `3d` profile is an archive of existing model files and interface workflows. It is not part of the validated 2D UI flow. Check its node schemas, required native dependencies, and generation result separately before treating it as usable on another device.
