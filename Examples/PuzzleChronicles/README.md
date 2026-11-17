# Puzzle Chronicles reference-specific recipes

These scripts preserve the working extraction, reconstruction, narrow-band matte cleanup, and gallery logic used for the original 1448x1086 screen. Their crops, paths, and layer geometry are specific to that screen. They are an example for adaptation, not automatic segmentation of an arbitrary new reference.

Set `PUZZLE_REFERENCE` to the original full-resolution screen path before running the example. The reference art and previous generated packs are private runtime inputs and are not included. `puzzle2_jobs.py` prepares per-candidate graph files; submission/retrieval is handled by the agent through MCP. The copied workflow template is `asset_extract_base.json`.

```powershell
$env:PUZZLE_REFERENCE='C:\Art\PuzzleChronicles_UI_Reference.png'
.\ComfyUI\.venv\Scripts\python.exe Examples\PuzzleChronicles\scripts\puzzle2_jobs.py --output outputs\PuzzleTest
.\ComfyUI\.venv\Scripts\python.exe Examples\PuzzleChronicles\scripts\puzzle2_pack.py --output outputs\PuzzleTest --baseline outputs\PreviousPack --refine
```

Before generation, put the same reference into ComfyUI Input and select its filename in the prepared graphs. Example jobs retain the original master filename. Omit `--baseline` for a first run with no previous pack. Review the script's input requirements before running.

For a new screen use the bundled skill to create a new inventory, masks, and prompts. The reusable edge-cleaning implementation is also available as `Scripts/refine_cutout.py`; the generic gallery builder lives in the skill's `scripts/` folder.
