# Unity UI Assets — reference-to-sprite toolkit

Turns a flattened UI mockup into separate, clean PNG sprites for Unity (or any engine). It lives at `Pipelines/UnityUIAssets` under the installation root and drives the local ComfyUI backend on `http://127.0.0.1:8188`.

## Requirements

| Route | Needs |
|---|---|
| Edit route (`edit/`, default) | Model profile `uiassets` or `qwen` (Qwen Image Edit 2511, Qwen 2.5 VL encoder, Qwen VAE). The installed `ComfyUI/.venv` Python with numpy, Pillow, scipy and pymatting (all in the pinned application lock). Windows PowerShell for review sheets. |
| Extract / repair / rebuild (`pipeline.ps1`) | Model profile `ui` (FLUX.2 Klein, BiRefNet). PowerShell 7, Node.js and System.Drawing. |

No custom node beyond the bundled `GameArt_CutoutLab` is needed. Download the edit models with `Scripts\model_manager.py --profile uiassets --download`, or install with `.\Install.ps1 -Install -DownloadModels -Profile uiassets`.

## Quick start: edit route

Run from the installation root with ComfyUI started:

```powershell
# 1. New run folder (runs/ is local and ignored by Git)
New-Item -ItemType Directory Pipelines\UnityUIAssets\runs\my-screen-01
# 2. Put run.json (where the mockups and the previous pack are) and tasks.json (one entry per asset) there.
#    Start from Examples\PuzzleMemories\run.json and tasks.json; edit/README.md documents every field.
# 3. Calibrate one asset per class, then submit the whole pass as one batch
.\ComfyUI\.venv\Scripts\python.exe Pipelines\UnityUIAssets\edit\comfy_run.py Pipelines\UnityUIAssets\runs\my-screen-01\tasks.json home_button
.\ComfyUI\.venv\Scripts\python.exe Pipelines\UnityUIAssets\edit\comfy_run.py Pipelines\UnityUIAssets\runs\my-screen-01\tasks.json icon_sound icon_music map_pin --batch
# 4. Review sheet: reference crop, then every attempt on dark / light / contrasting mattes
.\ComfyUI\.venv\Scripts\python.exe Pipelines\UnityUIAssets\edit\make_review.py Pipelines\UnityUIAssets\runs\my-screen-01\tasks.json review.txt icon_sound icon_music
powershell -File Pipelines\UnityUIAssets\edit\review_sheet.ps1 review.txt review.png
# 5. Retry only failures, with a diagnosed change, as --attempt 2, 3, 4
```

Each attempt lands in `runs/<run>/Attempts/<id>/a<N>/` with the graph, seed, prompt ID, `raw.png`, `final.png` and, for small assets, `final_hires.png`. Record the chosen attempt per asset in `selection.json`, show the user a review page, and move a sprite into the runtime set only after the user accepts it.

This is a working toolkit coordinated by the `unity-ui-assets` agent skill. It does not automatically understand and split an arbitrary screenshot. The agent inventories the original, chooses treatments, writes the project JSON, runs jobs, inspects candidates and records acceptance. Approximately 95% similarity is a qualitative target, not a computed score or model guarantee.

## Persistent files

| Location | Contents |
|---|---|
| `config/pipeline.json` | Installed model filenames, default processing sizes, padding, feathering, sampling, agent retry budget, the `edit_route` settings and the `treatment_priority` |
| `edit/` | Edit-route tools: Qwen Image Edit graph, batch runner, gray keying, colour match, deterministic fixes, review sheets. See [edit/README.md](edit/README.md) |
| `projects/*.json` | Original reference path, stable asset IDs, native crop coordinates, contours, repair regions, route, prompt, seed and visual criteria |
| `scripts/AssetRaster.cs` | Source-preserving crops, contour masks, bounded composites, size fitting, export and matte previews |
| `scripts/workflows.cjs` | API graph construction from the per-asset recipe |
| `pipeline.ps1` | Prepare, export, explicit review and report entry point |
| `runs/<new-attempt>/` | Local only, ignored by Git. Frozen source, configuration snapshots, masks, graphs, raw outputs, selected candidates, exports, checks, review decisions and gallery |
| `workflows/UI`, `workflows/API` | Three runnable calibration templates; browser copies are under `User/default/workflows/UIAssets` |

Keep shared mechanics here. Keep project-specific shapes and prompts in project JSON, not in the common scripts or skill. For a new project use its own project file and run folders. The original reference remains the acceptance reference throughout retries.

## Edit route — the default (2026-11-21)

`edit/` contains the route that produced the accepted Puzzle Memories V6 set (43 sprites, all accepted by the user). Steps: one task per asset with the mockup crop → Qwen Image Edit 2511 isolates the element on flat gray → own gray keying with PyMatting (not BiRefNet) → colour match to the reference → deterministic fixes where a defect is systematic → review sheets → user acceptance. Small assets (long side < 128 px) are also exported as a high-resolution master (≥ 256 px, ≥ 4x) next to the exact-size PNG. Jobs are submitted as a batch (`--batch`) so the GPU stays busy. Details and commands: [edit/README.md](edit/README.md). The full 40-task recipe of that run is in [Examples/PuzzleMemories](../../Examples/PuzzleMemories/README.md).

The algorithm, in the order it is applied:

1. **Sort before generating.** Review every existing sprite on dark and light mattes; reuse a clean older version before regenerating. Give the user a numbered review page and read their decisions back.
2. **One task per asset**: reference screen, crop with a small margin, one-line subject, exact geometry and colour description, target size.
3. **Edit, don't synthesize.** Qwen Image Edit 2511 on the crop, flat gray `#c8c8c8` background. Calibrate one representative per class (glyph, badge, plate, illustration) before the batch.
4. **Key the background yourself** with `key_bg.py`: border flood fill, enclosed holes, PyMatting alpha and foreground colours. BiRefNet dropped badge bodies and kept only the glyph.
5. **Small assets: generate large, keep two sizes.** Long side under 128 px → also a master with long side ≥ 256 px and ≥ 4x. The exact-size PNG is the runtime default; the master survives later rescaling in the engine.
6. **Colour-correct against the reference** (`color_match.py`): Lab transfer; `--flat` for monochrome glyphs; `--colors-from` an accepted sibling when the crop contains a neighbouring plate.
7. **Deterministic fixes over more retries** when a defect is systematic: recolour, merge a doubled stroke, glyph outline ring, rebuild a stretchable plate from the reference's colour profile.
8. **Check in context**: assemble dependent layers (track + fill, frame + art) before accepting.
9. **Batches**: submit the whole pass with `--batch`, review on sheets, retry only failures; up to 3–4 attempts per asset; keep every graph, seed, prompt ID, raw and final.
10. **Candidates, then user acceptance.** Candidates go to their own folder with a manifest; READY only after the user accepts each one.

## Routes

**Priority (changed 2026-11-21): generate first, extract by exception.** A flattened mockup hides overlapped parts, blends edges into the background and bakes in text, so cutting UI elements out of it leaves neighbor fragments, halos and seams. On Puzzle Memories V5 every asset generated in isolation with real alpha passed review; almost every rejected one was cut from the mockup. Default per asset class:

- **UI elements** (icons, badges, buttons, bookmarks, frames, ornaments): generate in isolation with the mockup crop as reference — `03_Rebuild_Object`, `GameArt_UI_Asset_Extract` or `GameArt_Style_Final`. Group siblings into one sheet when possible so light, gold, green and rim thickness stay consistent. Fit to the mockup size and placement afterwards.
- **Content-specific illustration that is fully visible** (chapter maps, museum paintings, scene art): `01_Extract_Source`, plus `02_Repair_Masked` for small overlays such as labels or level pins.
- **Simple stretchable surfaces** (pills, rows, tracks, counters): rebuild as a 9-slice from measured geometry, or generate one clean plate.
- **Mostly hidden structures** (book cover, page stack): `03_Rebuild_Object`, then split by shared geometry.

If a cut-out still shows neighbor fragments, halos or seams after one retry, switch that asset to generation. Previous route descriptions below remain accurate for what each graph does.

1. **01_Extract_Source**: use original RGB and an explicit contour or an automatically estimated foreground mask. No diffusion redraw. Manual masks are suitable when the artwork is visible but foreground segmentation fails.
2. **02_Repair_Masked**: reference-conditioned local generation, followed by compositing into the native original crop. Pixels outside the declared feathered edit region are restored from the original. This protects known material but cannot guarantee a good reconstruction inside the mask.
3. **03_Rebuild_Object**: generate an entire coherent object when most of its structure is hidden; cut out, fit and review it. This route can change palette, material and geometry. It must pass visual review before later splitting or reuse.

The older `GameArt_UI_Asset_Extract` graph also synthesizes reference-conditioned candidates. Its name does not mean exact pixel extraction. It remains available, alongside the three other existing Final graphs.

## Project recipe

`crop` is `[left, top, right, bottom]`, in original native pixels. `outline` and `repair` use the same absolute coordinate space. The supported compact path commands are uppercase `M`, `L`, `C`, `Q`, `Z`, plus `E x y width height` and `R x y width height`. Multiple subpaths use even-odd filling. The outlines are authored/checked by the agent; a script rasterizes them with supersampling. They are not automatically inferred contours.

Each asset needs `id`, `route`, `crop`, and `review_criteria`. Use `alpha_source: contour` with `outline`, or `automatic` for foreground estimation. A repair needs `outline`, `repair` and `prompt`; a rebuild needs `prompt`. Optional settings include `seed`, `padding`, `feather_px`, `steps`, `reference_megapixels`, `generation_megapixels`, `finish_mode` and `include_in_layout`.

For a full production pack also record screen/layer membership, z-order, anchors, runtime role, shared placements and requested split geometry. This pilot demonstrates routing and review; it does not implement a universal book-splitting algorithm. Split a successfully accepted coherent book using that book's shared geometry rather than synthesizing independent mismatched halves.

## Run through the agent

```powershell
cd Pipelines\UnityUIAssets
& ./pipeline.ps1 -Action prepare -Project ./projects/puzzle-memories-pilot.json -Out ./runs/new-attempt
```

`source` in a project file is resolved relative to that project file. The two bundled projects expect the private Puzzle Memories home screen at `Input/01-home.png` of the installation; replace it with your own reference.

Use a new folder per attempt. `prepare` creates native crops, masks and `jobs.json`. Using the existing Comfy MCP tools, the agent uploads each job's `input_files`, validates the API graph, submits it asynchronously, follows that prompt ID and fetches all outputs into `Raw/<asset-id>`. Save submission IDs in `submitted.json`. Choose the output whose original filename starts with `candidate`, not diagnostic `raw_edit` or `raw_rgb`.

Register the selected files in `candidates.json`:

```json
{
  "play_base": {
    "file": "Raw/play_base/downloaded-candidate.png",
    "kind": "composite",
    "prompt_id": "actual-backend-prompt-id"
  }
}
```

Use `kind: composite` for this repair graph, because the graph already performed feathered compositing. `kind: raw` is for a raw native-sized edit that still needs the exporter's local blend. Do not feather a composite twice.

```powershell
& ./pipeline.ps1 -Action export -Run ./runs/new-attempt
& ./pipeline.ps1 -Action review -Run ./runs/new-attempt -Asset play_base `
  -Decision REVIEW -Note 'Concrete observed defect and next treatment'
& ./pipeline.ps1 -Action report -Run ./runs/new-attempt
```

Review at native/display size and on light, dark and contrasting mattes. Record PASS only after inspection. READY requires both technical PASS and visual PASS bound to the exact exported PNG SHA256. Changing that PNG invalidates an older decision. Editing the frozen original stops reporting. `manifest.json` is the delivery snapshot; `run.json` is its working counterpart. They are synchronized by `report`.

Retry only failing asset IDs, with a diagnosed change to contour, mask, reference, method or authorized backend. `max_retries` is the agent's budget, not a self-running loop in the CLI. Preserve accepted PNGs and their manifests byte-for-byte in the selected production pack; no regeneration is needed for them. This CLI prepares the listed assets only and does not automatically merge separate attempts into a production pack. Keep the selected-attempt mapping in that pack's manifest. Never replace a better accepted result with a later regression.

## Mask convention

Comfy `LoadImage` MASK is transparency: 0 = opaque, 1 = transparent. Contour PNG alpha is 255 inside the object, 0 outside; its loaded MASK goes directly into `JoinImageWithAlpha`. BiRefNet's foreground mask is inverted first. Edit-mask PNG alpha is 0 inside editable regions and 255 outside, so its loaded MASK marks the editable area. Confusing these conventions produces an inverted cutout.

The exporter retains source RGB for extraction, restores source RGB outside local repairs, and checks disagreement between manual candidate alpha and the prepared contour. These checks establish only the stated preservation properties. Rebuilds have no such protected-pixel guarantee. All masks still need visual inspection for clipped artwork, paper halos and accidental retained pixels.

## Pilot results — 2026-11-20

Five real local Comfy jobs completed: four initial assets and one treatment change. All three graph routes ran. No paid partner nodes were used. Their gallery and run folders stay on the machine that ran them; they are not in Git.

- `map_badge`: accepted after contour extraction and three-matte inspection; 11,887 opaque reference pixels retained without RGB changes.
- `map_decoration`, automatic: rejected because only the flag survived. A contour retry retained the landscape and 16,684 opaque reference pixels, but still has a paper halo; remains REVIEW.
- `play_base`: text was removed, but tonal seams/ghosting and a stray leaf fragment remain; REVIEW.
- `book_cover`: coherent binding candidate, but wrong texture, palette and corner proportions; REVIEW. It does not replace the accepted v4 book.

The partial layouts deliberately omit all unprepared UI. An overlay on the original is labelled partial and is never evidence of a fully reconstructed screen. Unity Editor was not launched. This is an operational routing/review toolkit with a documented local-model fidelity limit on these examples, not a claim that a new complete pack reached 95% fidelity.


## Repair-mask union fix — 2026-11-20

Overlapping rectangular and elliptical repair regions now use a union (winding fill); export contours retain even-odd filling so transparent holes remain open. A regression check covers overlapping rectangles, rectangles/ellipses, and contour holes. Previously prepared run masks remain frozen; new runs use the corrected preparation. This changes mask mechanics, not an artistic acceptance threshold.

## Puzzle Memories V6 — 2026-11-21

The edit route regenerated the 43 sprites that failed review in the V5 pack (glyph icons, badges, plates, toggles, paintings, logo). The user accepted all 43, most on attempt 1 or 2. Four needed a deterministic fix: a doubled stroke merged, a glyph recoloured with an outline ring, a progress track rebuilt from the reference profile, a thumbnail derived from the large painting. 26 small sprites also received high-resolution masters. Known, accepted imperfections: one card's parchment is slightly cooler than the reference, one painting was redrawn by the model, one map has a faint gray fringe near its clouds, and an 18×20 lock glyph stays soft. The pack was checked as PNGs on three mattes and as an assembled track and fill, not in the Unity Editor.
