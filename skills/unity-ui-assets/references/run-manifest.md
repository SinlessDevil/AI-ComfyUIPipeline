# Run manifest and gallery

Keep one manifest per reference or revision. Use reference coordinates in pixels, measured from the top left. Crop bounds use `[left, top, right, bottom]` with exclusive right and bottom edges. Record positions for each placement even when several placements share one PNG. If padded source sprites need to align in a composite, record their padded top-left offsets. Record any 9-slice borders in exported Unity pixels, including transparent padding.

The gallery helper reads the image paths and status fields below. Other fields are available to the agent or existing batch scripts. The example shows one extracted icon, two placements, and an optional cutout comparison.

```json
{
  "title": "Adventure menu",
  "language": "en",
  "reference_image": "Reference.png",
  "reference_size": [1448, 1086],
  "assembled_image": "Preview/Assembled.png",
  "style_brief": "Warm cream paper, thin gold bevels, and green enamel with upper-left lighting.",
  "assets": [
    {
      "id": "menu_chevron",
      "method": "EXTRACT",
      "status": "READY",
      "crop": [1249, 284, 1269, 315],
      "placements": [{"x": 1249, "y": 284, "z": 8}, {"x": 1265, "y": 457, "z": 8}],
      "reference_crop": "Reference/menu_chevron.png",
      "previous_png": "Before/menu_chevron.png",
      "unity_png": "Unity/menu_chevron.png",
      "selected_attempt": 1,
      "issues": []
    }
  ],
  "cutout_comparisons": [
    {
      "id": "menu_chevron",
      "before_png": "Cutout/chevron-mask-before.png",
      "after_png": "Cutout/chevron-mask-after.png"
    }
  ]
}
```

Use run-relative file paths with forward slashes. Bring any previous PNGs shown in the gallery into the run folder so the delivery is portable. Omit `previous_png` to use `reference_crop`. For an inventory-only run, set `preview_is_layout` to `true`, set `assembled_image` to the layout preview, and omit `unity_png` for pending entries. Keep text entries in the inventory as `LIVE_UI`. The gallery only renders entries for image assets.

Use `READY` for visually accepted exports, `REVIEW` for exported candidates with outstanding defects, and `PENDING` for missing exports. For generated assets, record each attempted seed, prompt, workflow or settings, result file, and review. Store a `next_action` for unresolved entries. For cutout comparisons, export both RGBA versions from the same RGB canvas with matching dimensions and alignment.

## Fidelity evidence and status

Technical success and fidelity acceptance are separate. Packaging code must preserve an asset's review decision and issues; it must not set every exported asset to `READY`, remove issues, or report visual acceptance merely because files or jobs exist.

For fidelity-sensitive runs, record evidence such as the following optional fields:

```json
{
  "original_reference": "Reference/source.png",
  "fidelity_target": {
    "kind": "qualitative_reference_match",
    "user_description": "85–90% similarity",
    "percentage_measured": false
  },
  "assets": [
    {
      "id": "map_art",
      "method": "EXTRACT_AND_LOCAL_REPAIR",
      "technical_status": "PASS",
      "fidelity_status": "REVIEW",
      "status": "REVIEW",
      "known_region": "Masks/known-visible.png",
      "repair_mask": "Masks/repair.png",
      "contour_mask": "Masks/outline.png",
      "source_transform": {"scale": 1, "offset": [96, 268]},
      "checks": {
        "protected_pixels": {
          "pixel_count": 200000,
          "max_rgb_error": 0,
          "meaning": "Only source preservation outside repair and edge processing"
        },
        "visual_reference_review": {
          "reviewer": "agent",
          "result": "REVIEW",
          "issues": ["Trail connection shifts in the repaired region"]
        }
      },
      "next_action": "Realign the repaired segment to the visible trail before acceptance"
    }
  ]
}
```

The example's values are illustrative, not default thresholds. Record actual measured regions and counts. Add metric definitions, units, alignment, excluded regions, and uncertainty whenever numerical results are reported. Do not convert protected-pixel coverage or RGB error into a percentage of artistic quality. An asset-level issue remains actionable even when the whole-screen average improves.

Custom methods such as `EXTRACT_AND_LOCAL_REPAIR` may describe combined treatments. Keep their provenance explicit: source pixels, locally reconstructed pixels, and any generated content. Seeds or model identities may be `null` when the backend does not expose them.

## Gallery storage choices

The bundled helper below consumes `previous_png` or an existing `reference_crop` PNG. A project-specific gallery may instead display an inline SVG/window onto the original source using its crop coordinates, avoiding duplicate PNG crops. Verify that the chosen builder actually supports that representation; do not feed unsupported fields to the bundled helper and assume they will render.

If the user requests a lean current pack, keep canonical runtime files in `Unity/`, preserve raw/history material in a recoverable archive, and document its location. Distinct states and animated layers are not duplicate exports. Ensure active manifests and galleries contain no stale references after canonicalizing names or removing alternatives.

From the skill folder, run the helper with Python 3.9 or later. It uses only the standard library and verifies every referenced image file before writing the page. Choose `en` or `ru` for the built-in captions. For other languages, adapt the captions to the user's language.

```text
python scripts/build_gallery.py /path/to/run/manifest.json
```
