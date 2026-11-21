# Reference fidelity: treatment and acceptance

Use this guide for high-fidelity asset preparation or to diagnose a drifting attempt. Parameters depend on source size and artwork; the examples are decision patterns, not universal numeric settings.

## Treatment selection

Default order: generate UI elements in isolation (grouped into sheets), extract only unoccluded content-specific illustration, reconstruct simple stretchable surfaces. The rows below are listed in that priority.

| Evidence in the reference | Preferred starting treatment | What may change | What needs verification |
| --- | --- | --- | --- |
| A UI element (icon, badge, button, bookmark, frame, ornament) in a flattened mockup, touching or overlapping neighbors | Conditioned generation of the isolated element, grouped with its siblings in one sheet on a flat contrasting background or with native alpha | The whole element; it is fitted to the mockup's size and placement afterwards | Silhouette, proportions, palette and rim thickness against the mockup crop; consistency across the sheet; clean alpha on three mattes |
| A content-specific illustration that is fully visible (map, painting, scene art) | Original RGB plus traced or refined alpha | Transparency, crop, padding; narrowly justified edge decontamination | Color retention, contour, holes, fringes, native scale |
| Text, pins, or small UI overlays obscure part of artwork | Local repair with protected original | Declared repair regions and a small seam band | Original outside repairs; connections and material inside them |
| A panel has simple repeated geometry and readable material | Deterministic reconstruction from measured edges and samples | Hidden fill, repeated stretch region | Caps, rim widths, bevels, gradients, texture scale |
| Most of an object is hidden, but its coherent structure can be inferred | Whole-object reconstruction or generation, followed by fitting and splitting | Unknown interior or missing structure | Visible anchors and silhouette; coherent material; shared geometry |
| A wholly new asset is requested | Conditioned generation | The requested new asset | Reference style, identity constraints, intended crop, alpha and runtime use |

Several treatments can coexist within one asset. Document which portion came from original pixels, sampling, geometric reconstruction, or a generative model. Do not label a regenerated object as a direct extraction.

Switch a cut-out to generation when, after one retry, it still shows fragments of neighboring elements, background halos, doubled rims or seams: these come from the flattened source and another mask rarely removes them.

## Original-pixel extraction

1. Define the outline in original coordinates, retaining the source's slant, asymmetry, holes, and edge curvature.
2. Separate opacity from RGB. A segmentation model can estimate a mask without supplying replacement artwork.
3. Inspect white, dark, and saturated mattes. Pale paper can resemble highlights; dark leather can resemble background. Refine locally rather than applying one global material rule to every asset.
4. If background color contaminated a translucent edge, decontaminate only the supported edge band. Keep protected interior RGB unchanged and report the band separately.

Source screenshots usually lack an original alpha channel. A hand-traced or inferred outline is an estimate, even when the interior RGB is exact.

## Local reconstruction with a protected source

Use this when the scene is largely visible and overlays are localized.

1. Mark the entire overlay: label or pin, glyph, glow, shadow, and any contaminated seam. Keep a separate silhouette mask for the illustration itself.
2. Request the needed cleanup from an authorized editor. State exact landmarks and route connections to retain. If the tool lacks an enforced edit mask, assume its whole result may drift.
3. Fit the candidate to the reference coordinate system. Where necessary, align repaired patches to the known surrounding material; avoid using the obstructing overlay itself as an alignment feature.
4. Blend useful candidate content only inside the repair mask, with a seam appropriate to the source resolution. Restore original pixels outside it deterministically.
5. Inspect trail connections, repeated lines, corners, gradients, and texture continuity. Verify the protected region against the original file.

Masking does not make a bad repair good. A wrong route, poorly reconstructed frame, or visible seam remains a fidelity failure even if protected RGB is perfectly preserved.

## Deterministic surface reconstruction

Use visible geometry and material samples to build a blank button or panel when that is more faithful than unconstrained synthesis. Preserve the outer contour and border evidence. Use symmetry only where supported; the missing right side of an asymmetric frame cannot be assumed to equal the left side.

Do not erase text by replacing the entire interior with a flat color if the source contains grain, a gradient, recesses, or intrinsic shading. A stretchable export needs a tested safe center region and unaltered fixed caps.

## Coherent whole-object reconstruction

Use when much of a book cover or similar structure is hidden and small repairs would force an arbitrary patchwork.

- Start from the original reference and explicitly retain observable contour, material, perspective, and anchors. Request a complete clean object with the necessary hidden material.
- Review the clean object before splitting it into layers. Resolve large silhouette and material errors here.
- Establish a common canvas and shared hinge/spine before producing dependent pages, covers, rims, and tabs. Split related parts from a coherent base where possible.
- Fit exported dimensions mechanically after the object is acceptable. A fixed output canvas or a cutout node does not enforce the reference geometry.
- Review the whole reconstructed material when it may become visible during animation. A lower-rim crop cannot certify the hidden inner cover.

Conditioning from a previous candidate can be useful for a specific edit, but it must not replace comparison to the original. If iteration preserves the wrong grain, palette, or geometry, return to the original or change the treatment.

## Backend calibration and diagnosis

Inspect actual data flow before judging a workflow by its title. Reference conditioning provides information; it does not guarantee unchanged target pixels. Starting from a new target latent can be a valid model design, but it is not direct pixel extraction or an enforced local edit.

Before batching a difficult class, test a representative source and inspect the raw RGB, alpha, and assembled result. Useful diagnostics:

- Correct RGB with wrong transparency: repair the mask/matte, not the drawing.
- Correct silhouette with wrong material: change the reconstruction/prompt/backend, not just the alpha.
- Correct individual parts that fail to align: repair their shared geometry, not their style.
- A structurally drifting candidate: do not try to certify it by resizing or compositing it into a large unchanged screen.
- Repeated failure after meaningful changes: keep the best result as `REVIEW`, explain the defect, and propose a different route within user constraints.

Do not impose a generic gloss, shadow, bevel, or palette instruction on unrelated classes. Inspect appended prompts and toggles as well as the main prompt. Distilled sampling defaults and quantization are not proven causes without evidence from controlled comparisons. One workflow's failure does not establish a limit for all local or free models; one successful hosted edit does not establish universal superiority.

## Acceptance evidence

Use separate evidence for separate questions:

| Question | Suitable evidence | What it does not prove |
| --- | --- | --- |
| Are known visible pixels retained? | Aligned protected-region RGB/alpha comparison, region definition, pixel count, maximum/mean error | Correctness of hidden repairs or overall style |
| Is the observable shape aligned? | Native overlay, anchor displacement, silhouette comparison in known regions | Shape of portions hidden in the screenshot |
| Does material/style match? | Native crops of color, grain, bevels and highlights; recorded visual decision | An objective universal percentage of artistic quality |
| Does the screen fit together? | Assembly from the actual exported PNGs at recorded positions | Fidelity of each isolated object or animation behavior |
| Is the engine delivery functional? | File/import checks, then Editor/runtime checks when performed | Visual similarity merely from successful import |

RGB MAE, RMSE, SSIM, perceptual embeddings, or similar measures may assist a defined comparison. State alignment, matte, exclusions, region, units, and limitations. Do not convert them into a "90% quality" statement or substitute a screen average for per-object review. A silhouette score needs a trustworthy target mask; a traced or occluded target must be labeled as such.

If the user requests 85–95% similarity without defining a metric, retain the request as a qualitative fidelity target and use concrete acceptance criteria: preserved landmarks and proportions, matching material/palette, clean seams and alpha, correct geometry, and a side-by-side review. Do not claim that the percentage was measured. Clarify the metric only if the user needs a numerical acceptance gate.

## Status and iteration rules

Record technical checks separately from reference-fidelity acceptance. A file can be technically valid and still require visual revision. `READY` must come from an explicit asset-level acceptance decision, not a packaging loop that marks every export ready and clears its issues.

For each accepted candidate, record which checks support it and whether acceptance was the agent's visual review or explicit user approval. Preserve outstanding issues and the next action. If no comparable pixels exist in a hidden area, record the uncertainty and visual reconstruction decision rather than assigning a fictitious pixel score.

After a method changes, verify its intended invariant: source pixels remain protected, geometry aligns, the repaired seam is correct, or unchanged assets are actually unchanged. Repeating the same flawed method to consume a retry allowance is not an improvement strategy.
