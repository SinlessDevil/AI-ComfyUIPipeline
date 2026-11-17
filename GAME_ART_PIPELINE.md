# Game-art workflow entry points

The main UI graphs are `Workflows/GameArt/GameArt_Text_Final.json`, `GameArt_Style_Final.json`, `GameArt_Retouch_Final.json`, and `GameArt_UI_Asset_Extract.json`. Each has a separate `*_API.json` for backend submission.

The default `ui` model profile provides the Klein and BiRefNet components used by these four graphs. Style, retouch, and extraction also need an appropriate input image; select your reference after opening the graph. Installed synthetic fixtures are clearly described in the installation guide and do not reproduce the original game art.

`WorkflowLibrary/GameArt/` preserves interface-visible copies, which can contain user layout/widget edits. Keep those edits separate from source templates when updating. Earlier `*_v1` model-comparison graphs remain available and may require another model profile.

The UI Asset Extract graph generates one candidate at a time from a reference crop and text conditions. The bundled skill coordinates inventory, per-element prompts, extraction/reconstruction, bounded retries, edge review, packaging, and the gallery. It is not a single node that automatically cuts every part of any screenshot.

Use [the skill](skills/unity-ui-assets/SKILL.md), [model guide](Docs/MODELS.md), [MCP guide](Docs/MCP.md), and [reference-specific example](Examples/PuzzleChronicles/README.md).
