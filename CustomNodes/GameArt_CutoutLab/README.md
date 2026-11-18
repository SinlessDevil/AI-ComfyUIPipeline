# GameArt cutout nodes

Local PyMatting-based output cleanup. No network calls, model downloads, or changes to core ComfyUI. Copy this directory into `ComfyUI/custom_nodes/` and install the versions in the application lock. Restart an idle backend to load node changes.

## GameArt Cutout Finish

Place immediately before `JoinImageWithAlpha`. Its `alpha` input and output follow Comfy's transparency convention: **0 is opaque, 1 is transparent**. A white-foreground mask from BiRefNet needs `InvertMask` first. Connect both output ports to the matching inputs of `JoinImageWithAlpha`.

| Mode | Behavior |
|---|---|
| `off` | Return the exact input tensors; default in Retouch |
| `alpha_only` | Refine transparency, preserve RGB; default in Extract/Text/Style |
| `alpha_and_rgb` | Refine transparency and estimate foreground colors |
| `rgb_only` | Estimate foreground colors while retaining the exact input alpha |
| `gold_on_green` | Build gold material seeds inside the supplied coarse region, then refine alpha/RGB |
| `ivory_on_green` | Same for a pale glyph such as a white plus |

Defaults: no preblur, blackpoint 0.01, whitepoint 0.99, 1000 iterations. Lowering whitepoint to 0.95 can help uncertain foreground seeds; review the edge against its source. Completely full/empty masks have no boundary and pass through. Incomplete trimaps produce actionable errors.

Material modes apply to a **single glyph with an appropriate coarse region**, excluding the parent plate's golden rim. They are not automatic detectors for a whole screenshot, portrait, leaves, or multicolored logo. `min_component_fraction=0` preserves disconnected details; 0.04 removed a stray parent-rim component in our Collection test. Keep it zero unless that filtering is intended.

## GameArt Glyph Trimap

Exposes the material-guided trimap separately for the upstream ImageMatting node. Its `region_mask` and output use **white foreground**, unlike the Finish node's transparency port.

PyMatting refines a boundary; it cannot recover hidden goggles or reliably correct a badly selected object. Preserve a cleaner reconstruction when it already passes. RGB recovery can alter edge colors, so it remains optional.
