# Puzzle Memories edit-route recipe

`tasks.json` is the complete task list of the Puzzle Memories V6 run (2026-11-21): 40 Qwen Image Edit tasks that regenerated the sprites rejected in the V5 pack. All of them were accepted by the user. Three more sprites of that run were fixed without the editor, so they have no task here: one older V4 frame taken as is, one V4 ribbon recoloured to the reference colour, and one V5 plate with its green fringe pixels removed. The accepted `art_seaside` thumbnail was finally derived from the cleaned large painting rather than from its own task.

It is a worked example of how to write tasks, not a reusable crop list: crops and sizes belong to the private Puzzle Memories mockups, which are not in this repository.

## What to copy from it

- **Prompt pattern.** `subject` names the element and where it is in the crop; `geometry` states shape, exact colours read from the crop, and what must not appear ("Only the brown glyph, no plate behind it").
- **Classes.** Glyph icons use `"match": "flat"` (reference hue, own shading). Most badges, buttons and plates need no colour match. Paintings and large scenes (`art_seaside_large`, `home_puzzle_scene`, `nav_map_art`, `reward_card`, `museum_large_frame`) use a full `edit` prompt instead of `subject` + `geometry`. `size` on four calibration tasks is a leftover of the FLUX comparison and is ignored by the Qwen route.
- **Special cases.** `node_check` uses `ref_abs` to edit an earlier clean raw instead of the mockup (run `completed_badge` first). `art_seaside` and `art_seaside_large` use `fit: alpha_from` to reuse the previous pack's alpha. `profile_placeholder` carries the softer key thresholds (`--t1 8 --t2 30`) its pale silhouette needed.

## Running it again

1. Create `Pipelines/UnityUIAssets/runs/<new-run>/` and copy `run.json` and `tasks.json` into it.
2. In `run.json` set `ref_dir` to the folder that holds `Screens/*.png`, and `baseline_manifest` / `baseline_root` to the previous pack.
3. Follow the quick start in the [toolkit README](../../Pipelines/UnityUIAssets/README.md): one calibration task per class, then `--batch`.
