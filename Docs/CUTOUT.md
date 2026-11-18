# Cutout integration

The four maintained 2D workflows include `GameArtCutoutFinish` immediately before RGBA export. Generation models, prompts, seeds, output prefixes, shadow/highlight controls and background switches are preserved.

- **UI Asset Extract, Text Final, Style Final:** default `alpha_only`. Enable `alpha_and_rgb` when the fringe contains background color, or select the appropriate material mode for an isolated gold/ivory glyph on green.
- **Retouch Final:** default `off`, preserving source alpha and the existing masked edit/composite. `rgb_only` offers optional color cleanup without changing that alpha. Changing its mode to alpha refinement explicitly allows contour changes.
- Archived v1 and 3D graphs are unchanged.

Read the [node guide](../CustomNodes/GameArt_CutoutLab/README.md) for mask polarity, controls and limitations. Final checks need a light, dark and contrasting backdrop at native sprite size; additional soft edge pixels alone do not prove quality.

## Restore and upgrade

The installer copies our bundled node and checks out [ComfyUI-Image-Filters](https://github.com/spacepxl/ComfyUI-Image-Filters) at commit `3d9184c45bcdd079d96718dc936150b68f5e41ba`. The latter supplies the earlier standalone ImageMatting experiments; Finish calls the same PyMatting algorithms directly. Both use the single application dependency lock, including `pymatting`, `numba`, `llvmlite` and `opencv-contrib-python-headless`. Do not install four overlapping OpenCV distributions from the upstream requirements. No extra neural weights are required for matting; the existing BiRefNet remains the initial object segmenter.

Fresh installs receive the updated library. Existing user workflows are preserved by installation: compare and patch their output tails deliberately, or back up the selected workflow and import its updated repository copy. The installer refuses conflicting custom-node files or a modified/different upstream node checkout. Back up and reconcile these explicitly; do not reset user changes. Restart only when ComfyUI's queue is empty, then reload the workflow in the frontend.

Generated test images, user reference crops and machine paths stay local. The repository contains source and the validation summary, not the user's image pack. See [validation](VALIDATION.md) for the recorded checks and limits.
