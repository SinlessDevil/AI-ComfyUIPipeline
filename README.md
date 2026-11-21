# AI ComfyUI Pipeline

Reproducible home for our ComfyUI game-art workflows, local launch tools, MCP connection, sprite edge cleanup, and UI asset skill.

## Install with an agent

Give a local agent this prompt:

```text
Install my ComfyUI pipeline from https://github.com/SinlessDevil/AI-ComfyUIPipeline.
Read AGENTS.md and Docs/INSTALLATION.md first. Inspect this machine and reuse an
existing suitable installation when possible. Choose a compatible model profile,
show the download size, then install the requested profile, configure one MCP
registration in my client, and install skills/unity-ui-assets once.
Start the local backend and verify workflow discovery, a fresh generation,
job completion, output retrieval, and a useful workflow error through MCP.
Report the actual image path and any remaining failures. Preserve existing art.
```

## Windows quick start

Requires 64-bit Windows, Git for Windows, an NVIDIA GPU with a compatible driver, and network access. The frozen environment was captured on RTX 5080; other hardware needs a compatibility check. See [hardware guidance](Docs/HARDWARE.md).

```powershell
git clone https://github.com/SinlessDevil/AI-ComfyUIPipeline.git C:\AI\ComfyUI
cd C:\AI\ComfyUI
# Preview the selected profile and model size, without installing anything:
.\Install.ps1 -Profile ui
# Install local Python, ComfyUI, dependencies, MCP, and selected models:
.\Install.ps1 -Install -DownloadModels -Profile ui -DesktopShortcut
```

Alternatively, double-click `INSTALL.bat` in the cloned folder. It installs the `ui` profile and downloads its weights. It creates the root app shortcut; the PowerShell option above also creates a desktop shortcut. The installer downloads a pinned, SHA256-checked uv executable and uses a local managed Python. No administrator installation or system PATH change is required by these scripts.

Open `ComfyUI.lnk` after installation. It starts a localhost backend and opens a Chrome/Edge app window. Use `STOP_COMFYUI.bat` to stop the backend. Closing the app window leaves it running.

## Model profiles

Exact files, fixed revisions, download URLs, sizes, and SHA256 values are recorded in [models.lock.json](Config/models.lock.json). Model weights are excluded from Git.

| Profile | Purpose |
|---|---|
| `ui` | Main FLUX.2 Klein + BiRefNet workflow, recommended starting profile for the reference machine |
| `uiassets` | `ui` plus Qwen Image Edit 2511 with its encoder and VAE: everything the mockup-to-sprites toolkit uses, about 26.7 GB |
| `starter` | Original SD 1.5 examples + BiRefNet |
| `zimage` | Z-Image comparison graphs + BiRefNet |
| `qwen` | Qwen generation and editing + shared encoder/VAE + BiRefNet |
| `3d` | Existing Pixal3D-related weights and archived 3D workflows; separate verification required |
| `all` | All 16 weights from the reference machine, about 57.65 GB before environments/caches |

Download another profile later using the installed local interpreter:

```powershell
.\ComfyUI\.venv\Scripts\python.exe Scripts\model_manager.py --profile qwen
.\ComfyUI\.venv\Scripts\python.exe Scripts\model_manager.py --profile qwen --download
```

See [the model guide](Docs/MODELS.md) for exact totals and workflow requirements.

## Connect your agent

Installation writes path-specific snippets to `Logs/generated/mcp.json` and `Logs/generated/codex-mcp.toml`. Merge the relevant server entry into your client's existing configuration and reload the client. This avoids overwriting unrelated MCP registrations. The installer does **not** silently edit your client configuration.

The wrapper adds `list_local_workflows` and `start_local_pipeline` to the official Comfy MCP server. Use the latter to start this installation with its shared directories. Follow [MCP setup and acceptance checks](Docs/MCP.md).

## Install the bundled skill

The complete English skill is in [skills/unity-ui-assets](skills/unity-ui-assets/SKILL.md), copied from our AI-UnityPipeline skill. The command remains `$unity-ui-assets`. It works with PNG exports and ComfyUI without requiring Unity to be installed.

```text
Install skills/unity-ui-assets from this repository into my agent's user skills
directory. If unity-ui-assets is already installed, compare and update that copy;
keep a single active installation of the skill.
```

Example request:

```text
Use $unity-ui-assets to break this screen into separate sprites. Keep reusable
parts separate and text live, except the approved logo. After the initial attempt,
allow up to three retries per asset. Save PNGs, the assembled screen, manifest,
QA report, and a Before/After Gallery.html in the output folder I provide.
```

## Turn a mockup into sprites

[Pipelines/UnityUIAssets](Pipelines/UnityUIAssets/README.md) is the toolkit the skill drives on this installation. Its default edit route image-edits each element's mockup crop with Qwen Image Edit 2511 onto flat gray, keys the background with its own matting, matches colour to the reference, and keeps small assets in two sizes (exact runtime PNG plus a high-resolution master). Jobs go to the queue as a batch; every attempt keeps its graph, seed, prompt ID, raw and final image; the user accepts each sprite on a review page before it counts as ready. Install the `uiassets` profile for it, then see [the game-art guide](GAME_ART_PIPELINE.md#mockup-to-sprites) and the worked [Puzzle Memories recipe](Examples/PuzzleMemories/README.md).

Example request:

```text
Use $unity-ui-assets with the local toolkit to turn the rejected sprites of this pack
into clean candidates. Sort what is already good first and give me a review page.
Generate the rest through the edit route in batches, up to four attempts each,
and keep small icons in two sizes.
```

## Repository contents

The maintained 2D graphs include selectable alpha/RGB edge cleanup and a dedicated gold/ivory glyph mode. Retouch preserves source alpha by default. See the [cutout guide](Docs/CUTOUT.md), including upgrade instructions for existing installations.

- `Workflows/`: maintained UI graphs and backend API forms, including the three `UIAssets` source-extraction, masked-repair and rebuild graphs.
- `WorkflowLibrary/`: snapshot of interface-visible Starter, GameArt, UIAssets, and 3D graphs. Installation copies missing files into the local UI library and preserves existing ones.
- `Pipelines/UnityUIAssets/`: mockup-to-sprites toolkit — edit route, prepare/export/review CLI, shared config. Its `runs/` folders stay local.
- `Scripts/`, `Tests/`: launch, model download/verification, smoke test, mask refinement, and tests.
- `Config/`: pinned runtime, application/MCP package snapshots, and model catalog.
- `CustomNodes/`: bundled local cutout node; the installer also restores the pinned upstream Image-Filters pack.
- `skills/`: bundled UI asset skill and gallery builder.
- `Examples/PuzzleChronicles/`: screen-specific extraction/reconstruction recipes from the existing pipeline.
- `Examples/PuzzleMemories/`: the 40-task edit-route recipe of an accepted production run.
- `Docs/`: installation, hardware, models, MCP, workflow guidance, and validation record.

ComfyUI itself, Python environments, downloaded models, credentials, user state, reference art, generated images, and caches stay local. The repository is a reconstruction recipe; maintain separate backups of valuable artwork.

See [validation and known limits](Docs/VALIDATION.md). New installations must run their own acceptance checks before being called ready.
