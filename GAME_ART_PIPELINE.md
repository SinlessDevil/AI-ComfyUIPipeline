# Game-art workflow entry points

The main UI graphs are `Workflows/GameArt/GameArt_Text_Final.json`, `GameArt_Style_Final.json`, `GameArt_Retouch_Final.json`, and `GameArt_UI_Asset_Extract.json`. Each has a separate `*_API.json` for backend submission.

The default `ui` model profile provides the Klein and BiRefNet components used by these four graphs. Style, retouch, and extraction also need an appropriate input image; select your reference after opening the graph. Installed synthetic fixtures are clearly described in the installation guide and do not reproduce the original game art.

`WorkflowLibrary/GameArt/` preserves interface-visible copies, which can contain user layout/widget edits. Keep those edits separate from source templates when updating. Earlier `*_v1` model-comparison graphs remain available and may require another model profile.

The UI Asset Extract graph generates one candidate at a time from a reference crop and text conditions. The bundled skill coordinates inventory, per-element prompts, extraction/reconstruction, bounded retries, edge review, packaging, and the gallery. It is not a single node that automatically cuts every part of any screenshot.

## Mockup to sprites

A flattened mockup has no layers: elements overlap, edges blend into the background and labels are baked in. Cutting UI elements out of it leaves neighbour fragments, halos and seams. The proven default is therefore **generate first, extract by exception**:

| Asset class | Treatment |
|---|---|
| Icons, badges, buttons, bookmarks, frames, ornaments | Image-edit the mockup crop into the isolated element (edit route, Qwen Image Edit 2511), key the gray background, colour-match, fit to size |
| Fully visible content-specific illustration (maps, paintings, scene art) | `UIAssets/01_Extract_Source`, plus `02_Repair_Masked` for small overlays |
| Simple stretchable surfaces (pills, rows, tracks, counters) | Rebuild as 9-slice from measured geometry, or generate one clean plate |
| Mostly hidden structures (book cover, page stack) | `UIAssets/03_Rebuild_Object`, then split by shared geometry |

The tools live in [Pipelines/UnityUIAssets](Pipelines/UnityUIAssets/README.md):

- `edit/` — the edit route: batch runner on the local backend, gray keying with PyMatting, Lab colour match, deterministic fixes, review sheets. Assets with a long side under 128 px are kept in two sizes: the exact runtime PNG and a high-resolution master (≥ 256 px, ≥ 4x). Needs the `uiassets` or `qwen` model profile.
- `pipeline.ps1` + `scripts/` — prepare, export, review and report for the three `UIAssets` graphs, with source-pixel preservation checks and a SHA-bound review gate.
- `config/pipeline.json` — shared models, defaults, edit-route settings and treatment priority. Per-screen data goes into a run's `tasks.json` or a `projects/*.json` recipe, never into the shared scripts.

The `UIAssets` graphs are in `Workflows/UIAssets/` (UI and API forms) and `WorkflowLibrary/UIAssets/` (interface-visible copies). [Examples/PuzzleMemories](Examples/PuzzleMemories/README.md) holds the 40-task recipe of an accepted production run.

Use [the skill](skills/unity-ui-assets/SKILL.md), [model guide](Docs/MODELS.md), [MCP guide](Docs/MCP.md), and the reference-specific examples for [Puzzle Chronicles](Examples/PuzzleChronicles/README.md) and [Puzzle Memories](Examples/PuzzleMemories/README.md).
