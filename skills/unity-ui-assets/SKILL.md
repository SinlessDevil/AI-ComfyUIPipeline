---
name: unity-ui-assets
description: Extract and reconstruct reference-faithful layered Unity PNG sprites from game UI mockups, including selective regeneration, explicit fidelity review, and comparison galleries. Use for a screen breakdown or targeted sprite-pack revision.
---

# Unity UI Assets

This skill is maintained in AI-ComfyUIPipeline; it originated in AI-UnityPipeline, which no longer ships it. Keep the existing skill name when installing; use one active copy per agent. The workflow uses ComfyUI for image generation and exports PNGs without requiring a Unity installation.

Turn the user's UI reference into independently usable sprites while preserving its visual identity. A valid PNG or a completed generation is not evidence of reference fidelity. If the user requests a breakdown first, deliver that breakdown before production.

## Establish the reference and intended fidelity

- Keep the original reference immutable and available in every revision. A candidate may be an edit input, but does not replace the original as the acceptance reference.
- Give each asset a stable ID, original crop, layer order, intended runtime use, and treatment: `EXTRACT`, `RECONSTRUCT`, `GENERATE`, or `LIVE_UI`. Record visible material, occlusions, and which pixels or geometry can actually be verified.
- Record palette, silhouette, proportions, lighting, bevels, texture scale, line weight, and intrinsic shadows. Ordinary labels and values stay live; preserve brand lettering when requested.
- Identify shared geometry before producing related layers: canvas, spine or hinge, anchors, perspective, and contour. Map one reusable asset to multiple placements.
- Treat a request such as "90% similar" as an intended level of fidelity until an actual measurement and its scope are defined. Do not present an RGB error, preserved-pixel fraction, or number of successful jobs as a percentage of artistic quality.

## Choose treatment per asset

Read [fidelity-workflows.md](references/fidelity-workflows.md) when choosing between generation, extraction, local repair and deterministic reconstruction, or when a prior attempt has drifted.

**Priority: generate first, extract by exception.** A flattened mockup has no layers: overlapping elements hide each other, edges are blended into the background, and labels are baked in. Cutting a UI element out of it leaves neighbor fragments, background halos and seams, and its hidden parts must be invented anyway — in patches. When the mockup is itself AI-generated, its pixels are not sacred: the goal is a clean sprite set that looks like the mockup once reassembled, not a pixel copy. On Puzzle Memories V5, every asset generated in isolation with real alpha passed review, while almost every rejected asset was cut from the flattened mockup.

1. **Default — GENERATE each element by image-editing its mockup crop.** Give an instruction-following image editor the crop and ask it to isolate that one element, remove neighbors and text, complete hidden parts, keep exact colors and shading, on a flat uniform gray background. This reproduces the element itself; text- or style-conditioned generation only reproduces "something in the style" (colors, rims and bevels drift). Optionally generate siblings together in one sheet for consistency. Then key the background, fit to the mockup's size and placement. See the proven algorithm below.
2. **EXTRACT only unoccluded, content-specific illustration** that generation cannot reproduce exactly: chapter maps with their trail, museum paintings, large scene art. Use original RGB with an explicit alpha mask; repair small overlays (labels, level pins) locally with protected source pixels.
3. **RECONSTRUCT simple stretchable surfaces** (pills, rows, progress tracks, counters) as a 9-slice from measured geometry and material, or generate one clean plate per style. Do not cut them out of the mockup.
4. **Mostly hidden coherent structures** (book cover, page stack): generate the whole clean object, then fit and split it using shared geometry.

If an asset is cut out and shows neighbor fragments, halos or seams after one retry, switch it to GENERATE instead of retrying the cut. Preserve the reference's irregular silhouette: do not extend art to a rectangle or substitute a standard rounded rectangle merely to simplify export. Size fitting comes after the shape and composition pass review.

Use the user's authorized backend and applicable image-tool workflow. A workflow named "extract" may perform full synthesis: inspect its actual reference conditioning, target generation, masking, and output compositing. Save prompts, source, RGB, masks, RGBA, settings, and seeds when exposed. Do not invent an undisclosed model or seed.

For the configured local Comfy toolkit, read [local-comfy-pipeline.md](references/local-comfy-pipeline.md) when using its shared scripts, project recipes and review gate.

## Proven algorithm (Puzzle Memories V6, 2026-11-21)

This sequence fixed 43 rejected sprites; the user accepted every one, most on the first or second attempt. Follow it unless the project says otherwise.

1. **Sort before generating.** Review every existing sprite on dark and light mattes. Reuse a clean earlier version (an older pack) before regenerating anything. Give the user a numbered review page (reference crop + sprite on mattes, Ready/Fix toggle, a note field) and read their decisions back instead of guessing.
2. **One task per asset**: reference screen, crop with a small margin, a one-line subject, an exact geometry/colour description, target size. Name colours from the crop; say what must not appear.
3. **Edit, don't synthesize.** Image-edit the crop (on the local toolkit: Qwen Image Edit 2511) onto a flat gray background. Calibrate on one representative per class (glyph, badge, plate, illustration) before the batch.
4. **Key the background yourself.** Flood-fill the gray from the border, keep enclosed key-coloured holes transparent (gear, pin, ring), refine with matting and foreground colour estimation. Generic salient-object removers (BiRefNet) can keep only the glyph and drop a badge's body. Use softer thresholds for pale objects.
5. **Small assets: generate large, keep two sizes.** When the target's long side is under ~128 px, generate and key at high resolution (long side ≥ 256 px, at least 4x) and export both a high-resolution master and the exact-size runtime PNG. Small crops make the model guess colour and detail; a large master downsamples cleanly and survives later rescaling in the engine.
6. **Correct colour against the reference.** Match Lab mean/spread of the opaque pixels to the reference object. Monochrome glyphs: take the reference hue exactly, keep only the generated shading. If the crop contains a neighbouring plate, take colours from an accepted sibling instead.
7. **Deterministic fixes over more retries** when a defect is systematic: recolour an earlier geometry, derive a thumbnail from a clean large version, merge a doubled outline, recolour a glyph and add an outline ring, rebuild a stretchable plate from a vertical colour profile of the reference at the exact sprite size.
8. **Check in context.** Assemble dependent layers as the screen places them (track + fill, frame + art, ring + portrait) before accepting; a plate can be the right colour and still the wrong thickness for its fill.
9. **Run in batches.** Submit all jobs of a pass to the queue, collect afterwards, review on sheets (reference, then every attempt on three mattes), then retry only failures with a diagnosed change. Up to 3–4 attempts per asset; keep every graph, seed, prompt id, raw and final.
10. **Package as candidates, accept by the user.** Candidates go to their own folder with a manifest; move each into the runtime set only after the user accepts it on the review page.

Before expanding a generation batch, review a representative of each difficult asset class. A runnable backend is not a calibrated fidelity workflow. Do not continue a failing class merely because other classes passed.

## Review and retry

Read the acceptance guidance in [fidelity-workflows.md](references/fidelity-workflows.md) for fidelity-sensitive work.

- Compare each exported object with the original crop at native size and intended display size. Review contour, anchors, proportions, palette, material, highlights, edge alpha, transparent openings, stray pixels, and required lettering.
- Review every isolated asset — not a sample — on light, dark, and contrasting mattes, then assemble the actual exported layers to check alignment and consistency. A good aggregate screen metric does not override a visibly wrong individual asset. Look specifically for fragments of neighboring elements, background-colored halos, doubled rims, repair seams and stepped alpha.
- Self-review misses defects. Before calling a pack done, give the user a visual review page (every asset numbered, with its reference crop and dark/light previews) or have an independent reviewer pass it.
- Measure original-pixel preservation only in a declared, aligned, known-visible region outside edits and documented edge processing. Report that region and its pixel count. For regenerated or hidden areas, report what is observed and what lacks ground truth.
- Keep technical validation and fidelity review separate. `READY` requires applicable technical checks plus a recorded per-asset fidelity acceptance. File export, job completion, retry exhaustion, or selection of the best candidate must not automatically set `READY` or clear issues. An unresolved best candidate stays `REVIEW` with a specific next action.

Allow up to three retries per asset by default, stopping early when it passes. Diagnose the cause before retrying: contour/matte, local repair, geometry, material, or backend fidelity. Change the relevant crop, mask, method, or backend rather than repeatedly conditioning on a failed candidate. Every iteration is judged against the original. Preserve a better previous result when a later attempt regresses. Report a backend limitation only as narrowly as the evidence supports.

## Package the run

Keep a separate revision and preserve the comparison baseline. Put canonical runtime PNGs in `Unity/`; keep raw generations, masks, and history out of that import folder. Distinct states and independently animated layers are not duplicates. Select one export per intended use, document aliases, and report optional alternatives. If cleanup is requested, preserve recoverable history separately, update references, and verify unchanged rendering where no art change was intended.

Deliver `manifest.json`, `QA.md`, and `Gallery.html`. The gallery shows the full original and assembled result plus an original/previous-to-current comparison for each asset. Reuse source images for displayed crops where the chosen gallery builder supports it. Distinguish a style revision from a same-RGB mask comparison. Check links and required files. State whether verification used exported PNGs or the Unity Editor.

The [manifest and gallery guide](references/run-manifest.md) documents metadata, acceptance evidence, and the bundled gallery helper. Keep the QA report and handoff in the user's language. Describe unresolved fidelity honestly; do not convert a complete export inventory into a claim that the user's visual target has been achieved.

