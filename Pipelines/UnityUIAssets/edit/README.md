# Edit route — mockup crop → clean sprite (proven on Puzzle Memories V6, 2026-11-21)

This folder holds the reusable tools of the route that produced the accepted Puzzle Memories V6 set
(43 regenerated sprites, all accepted by the user after review, most on the first or second attempt).
It is the default route for UI elements cut from a flattened mockup. Run every attempt in a new folder
under `../runs/`; never write into these tools from a run.

## Run folder layout

```
runs/<run-name>/
  run.json        {"ref_dir": ".../References", "baseline_manifest": ".../manifest.json", "baseline_root": ".../V5"}
  tasks.json      one entry per asset (below)
  Attempts/<id>/a<N>/  graph_api.json, record.json (seed, prompt id), raw.png, final.png, [final_hires.png]
  Review/         review sheets and lists
  selection.json  {id: [attempt, note]} — the chosen attempt per asset
```

`run.json` paths may be absolute or relative to the run folder. `baseline_*` point at the previous pack and are
used only by `fit: alpha_from` tasks. Optional `"style"` replaces the default style sentence of the FLUX route.

`tasks.json` entry:

```json
{"id": "home_button", "engine": "qwen", "ref": "Screens/01-map.png", "crop": [x, y, w, h],
 "subject": "the round home button", "geometry": "exact colours, rim, glyph...", "target": [110, 112],
 "match": false | true | "flat", "colors_from": "optional accepted sibling sprite for the colour match",
 "edit": "optional full prompt instead of subject+geometry",
 "ref_abs": "optional input image instead of ref (absolute or relative to the run), e.g. an earlier raw.png",
 "fit": "alpha_from", "alpha_from": "Unity/Museum/Art/painting.png",
 "key_args": ["--t1", "8", "--t2", "30"], "steps": 30, "cfg": 4.0, "mp": 1.0}
```

| Field | Meaning |
|---|---|
| `crop` | `[x, y, width, height]` in the reference's native pixels, with a small margin around the element |
| `subject` + `geometry` | Become the prompt: isolate the subject, remove neighbours and text, complete hidden parts, keep colours, flat gray background |
| `target` | Exact runtime size of the sprite. A long side under 128 px also produces `final_hires.png` |
| `match` | `true`: Lab colour transfer from the reference crop; `"flat"`: reference hue for monochrome glyphs, own shading |
| `fit: alpha_from` | Paintings: resize the edited raw to an existing sprite (relative to `baseline_root`) and reuse its alpha |
| `engine` | `qwen` (default). Anything else uses the FLUX `GameArt_UI_Asset_Extract` graph, kept for comparison |

## Tools

| Script | What it does |
|---|---|
| `comfy_run.py tasks.json id... [--attempt N] [--seed S] [--batch]` | Builds the Qwen Image Edit 2511 graph (or the FLUX Extract graph when `engine` is not `qwen`), uploads the reference, submits to ComfyUI, downloads `raw.png`, then keys, colour-matches and writes `final.png` (+ `final_hires.png` for small assets). `--batch` submits all jobs first and collects afterwards, so the GPU never idles between jobs. Default seed is deterministic per asset and attempt. |
| `qwen_edit_graph.py` | The API graph: crop → Qwen edit (30 steps, cfg 4, CFGNorm, AuraFlow shift 3.1, euler/simple) → raw PNG. Only installed models and nodes. |
| `key_bg.py raw out W H` | Removes the flat gray generation background: border-connected flood region + enclosed key-coloured holes, PyMatting alpha and foreground colours, trim, aspect-preserving fit. Use instead of BiRefNet for UI objects: BiRefNet dropped badge bodies and kept only the glyph. Softer `--t1 8 --t2 30` for pale objects (cream borders, beige silhouettes). |
| `color_match.py final ref x y w h [--flat] [--colors-from sprite.png]` | Lab mean/std transfer onto opaque pixels, chroma gain capped so thin icons do not turn pink. `--flat` for monochrome glyphs (reference hue, own shading). `--colors-from` when the reference crop is contaminated by a neighbouring plate: take colours from an accepted sibling sprite. |
| `fit_alpha.py raw out alpha.png` | Paintings: resize the edited raw to an existing sprite and reuse its alpha. |
| `reprocess.py tasks.json id:aN [key args]` | Re-key / re-match from `raw.png` without the GPU. |
| `merge_double_stroke.py raw out radius` | When the model draws a doubled outline for a line icon, closes the gap into one stroke. |
| `outline_glyph.py raw out W H ring --fill #fff --outline #4a7010` | Recolours a glyph and adds an outline ring at 4x, then downsizes; also writes `_hires`. |
| `reconstruct_plate.py ref out x y w h col0 col1 W H` | RECONSTRUCT for stretchable plates: stadium of the exact sprite size from the vertical colour profile of the reference plate. Rims stay equal thickness around the caps. |
| `make_review.py tasks.json out.txt id[:a1,a2]...` + `review_sheet.ps1 list out.png [cell]` | Review sheet: reference crop, then each attempt on dark / light / contrasting mattes. |

## Environment

- Python for the image tools: the installation's `ComfyUI/.venv` (numpy, Pillow, scipy, pymatting). `comfy_run.py`,
  `make_review.py` and `reprocess.py` run with any Python 3 and call that interpreter for image work.
- `COMFY_HOST` overrides the backend address (default `http://127.0.0.1:8188`); `COMFY_PIPELINE_ROOT` the
  installation root (default: three folders above `edit/`); `UNITY_UI_ASSETS_PYTHON` the image-tool interpreter.
- Models: `qwen_image_edit_2511_nvfp4`, `qwen_2.5_vl_7b_nvfp4`, `qwen_image_vae` (profile `uiassets` or `qwen`).

## What to watch for

- Tiny crops (under ~60 px) make the editor guess colour; describe colours explicitly and colour-match.
- If the model keeps drawing the whole parent element (e.g. a badge instead of its check mark), feed an earlier
  clean raw as `ref_abs` and ask for the part only.
- Pale objects on gray key poorly with default thresholds; use `key_args` `--t1 8 --t2 30`.
- A plate can have the right colour and still the wrong thickness for its fill: check dependent layers assembled.
