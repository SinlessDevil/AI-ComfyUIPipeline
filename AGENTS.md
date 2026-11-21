# AI ComfyUI Pipeline

This repository stores our setup recipe and workflow source. Runtime folders at its root are ignored. Read `README.md`, `Docs/INSTALLATION.md`, and `Docs/HARDWARE.md` before installing.

## Installation and existing machines

- Inspect the target OS, GPU/VRAM, free disk space, existing ComfyUI installations, and client MCP registration. Reuse suitable installations and preserve edited workflows, user settings, source art, and outputs.
- The unattended installer and frozen package sets target Windows x86_64 with NVIDIA CUDA. Other platforms need a compatible runtime selected from official ComfyUI instructions. Quantized model compatibility must be checked separately.
- `Install.ps1` defaults to a read-only plan. `-Install` creates local runtime components. `-DownloadModels` explicitly downloads only the selected profile, with fixed revisions and SHA256 verification. Do not download `all` when a smaller profile meets the request.
- Existing application checkouts at a different commit or with modified tracked source are preserved; do not reset them as an installation shortcut.
- Read upstream `ComfyUI/AGENTS.md` before changing upstream code. Keep project behavior in our scripts/workflows where possible.

## MCP and verification

Merge the generated entry into the client's existing configuration without duplicating another server for the same installation. Never commit credentials or a client's complete private config.

Call `server_info` first. Use the wrapper's `start_local_pipeline` or the root shortcut to launch with the shared Models/Input/Output/User directories. `comfy-cli`'s generic launch command is not configured with these directory flags.

Do not claim MCP integration is complete from repository checkout, environment installation, or static graph validation. Verify discovery, fresh submission, job completion, image retrieval, and a useful failure through the registered MCP. Record the prompt ID and actual output. HTTP-only smoke checks must be labeled as such. Do not invoke paid partner nodes for acceptance tests.

## UI asset runs

Use the bundled `skills/unity-ui-assets/SKILL.md` when applicable. Keep a single active installed copy. It allows an initial attempt plus up to three retries per asset unless the user sets another limit. Keep the best attempt and identify unresolved assets.

With the local toolkit (`Pipelines/UnityUIAssets`), generate UI elements first and extract only fully visible illustration; the edit route in `edit/` is the default. Sort existing sprites and reuse clean older versions before generating, and read the user's review decisions back instead of guessing. Calibrate one asset per class, then submit each pass as a batch. Key the gray background with `key_bg.py` rather than BiRefNet. Keep assets with a long side under 128 px in two sizes: the exact runtime PNG and a high-resolution master. Prefer a deterministic fix over another retry when a defect is systematic. Each attempt goes in a new `runs/` folder, which stays out of Git. Candidates become ready only after the user accepts them.

After every full screen breakdown or full production run, provide `Gallery.html` alongside PNGs. Show the source screen and assembled result, then labeled Before/After columns per asset. Use a labeled reference crop when no prior PNG exists. Show transparency, make full images clickable, and verify local links. For mask comparisons apply both masks to the same generation with the same crop, scale, and background. Include the gallery link in the handoff.

## Maintenance

Keep documentation in English. Runtime and model upgrades are deliberate changes; update lock files and validate affected workflows together. Before publishing, inspect the explicit file list and run `Scripts/validate_repository.py`. Do not commit weights, environments, caches, credentials, personal paths, or generated packs. Preserve separate user-modified UI graphs when synchronizing the library.
