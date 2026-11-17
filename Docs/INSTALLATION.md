# Installation and restoration

## Supported automated path

The bootstrap targets Windows x86_64 with an NVIDIA GPU. The reference installation uses Python 3.12.12, ComfyUI 0.39.1, PyTorch 2.14.1+cu130, comfy-mcp 0.10.0, and comfy-cli 1.25.0. Exact source commit and package snapshots are in `Config/`.

Install Git for Windows and a compatible NVIDIA driver first. Clone this private repository into the desired installation directory. Use a new directory for a clean restore; moving an existing virtual environment is not supported.

Run `Install.ps1` without flags to inspect the plan. `-Install` bootstraps the pinned uv archive, downloads local managed Python, checks out the pinned official ComfyUI release, creates separate application/MCP environments, installs the package snapshots, prepares synthetic example images, copies missing UI workflows, generates MCP snippets, and creates a root app shortcut.

`-DownloadModels -Profile ui` adds only that profile's weights. `-DesktopShortcut` adds the app shortcut to the user's actual desktop folder. `INSTALL.bat` supplies `-Install -DownloadModels -Profile ui` for a double-click setup.

The `-Root` parameter must match the checkout directory. To choose a different root, clone the repository there first. The installer will preserve an existing application checkout with another commit or local source changes by stopping with a clear error. It does not reset that checkout.

## Disk and network

Reserve space for selected models, the application environment, the separate MCP environment, and package/download caches. Model size alone is not the total installation size. Downloads use original pinned source URLs and verify SHA256. Existing weights are reused only if size and hash match; differing files are preserved with an error. Interrupted `.part` downloads can resume when the server supports byte ranges.

The first runtime install needs internet access to GitHub, PyPI, the PyTorch wheel index, Python distribution hosts used by uv, and Hugging Face for selected models. The script does not disable TLS verification or change system networking settings.

## Credentials and client connection

GitHub authentication for cloning the private repository belongs to the receiving device. Do not embed a token in a clone URL or commit it. Local generation needs no paid API key. If a model source later requires authentication, configure credentials locally outside this repository.

Merge `Logs/generated/codex-mcp.toml` or `Logs/generated/mcp.json` into the client's configuration. The generated files contain local paths and stay ignored. Reload/reconnect the client, then follow [MCP acceptance checks](MCP.md). Client configuration edits and reconnection depend on the client's supported interface.

Install the skill folder into the agent's discoverable user skill directory. For a Codex setup using `.agents/skills`, the destination is its `unity-ui-assets` subfolder. Inspect any existing installation first and update one copy rather than installing duplicate skill names in several scopes.

## Verify the new machine

1. Run the launcher tests and `Scripts/check_gpu.py`.
2. Open `ComfyUI.lnk` and verify `http://127.0.0.1:8188`.
3. With the `ui` models installed, run the HTTP smoke script below. It changes the seed, submits a new generation, waits for completion, and decodes the actual PNG.
4. Run the distinct registered-client MCP acceptance checks in `Docs/MCP.md`.

```powershell
.\ComfyUI\.venv\Scripts\python.exe Scripts\verify_pipeline.py
# For a starter-only installation instead:
.\ComfyUI\.venv\Scripts\python.exe Scripts\verify_pipeline.py --workflow Workflows\GameArt\GameArt_Local_v1_API.json
```

The HTTP smoke result is recorded in `Logs/pipeline-smoke.json`; it does not prove the client's MCP registration works. A failed job reports its backend status/messages, while a timeout leaves the job visible for inspection rather than blindly cancelling other work.

## References and user art

Installation creates synthetic button/mask fixtures for the original examples only when those filenames are absent. They are not the original game art. Supply your own screen in `Load Image` for UI Asset Extract and replace any reference selection as needed. The master screenshot and generated Puzzle packs are not uploaded here.

`WorkflowLibrary/` preserves current interface-visible copies independently of maintained `Workflows/` templates. Installation copies only missing library files. Review differences deliberately when updating an existing machine.

## Other platforms

ComfyUI supports other platforms through its [official manual installation guide](https://docs.comfy.org/installation/manual_install). On Linux, macOS, AMD/Intel GPUs, or CPU-only devices, have the agent select the correct PyTorch/backend and model precision. Do not install the Windows package snapshots there. Preserve the same shared directory layout, export client paths for that platform, and run the same behavioral acceptance checks. The current automatic launcher scripts are Windows-specific.

## Updates

Pulling this repository updates the recipe; it does not update ignored runtime folders or replace already saved UI copies. The root `UPDATE_COMFYUI.bat` is an explicit upstream-upgrade utility. After an intentional upgrade, capture new runtime/package locks, verify workflows and MCP, then commit the new recipe. Re-running the pinned installer against an unrelated upgraded checkout is deliberately refused.
