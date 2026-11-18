# Validation record and limits

Initial source export prepared on 2026-11-18 from the existing Windows/NVIDIA installation.

## Recorded checks

- All 16 local model files were read and their SHA256 and size matched the pinned Hugging Face source metadata. Their weights are not uploaded.
- The source machine's package environments were captured into separate application and MCP lock files.
- All 10 tests passed against the exported source, including the seven existing launcher tests and three restore/download tests. They check readiness behavior, non-overwrite of user workflows and differing model files, path containment, actual local HTTP download/verification, and JSON/TOML configuration with spaces in paths.
- Source validation checks Python/JSON syntax, local Markdown links, portable pinned model records, package entries, possible credential patterns, personal absolute paths, large files, and binary content in the explicit publish set.
- PowerShell bootstrap syntax and the no-install plan are checked. These checks do not install another application environment or download model weights.
- The bundled skill is checked with the skill validator and its gallery helper is exercised with synthetic PNG fixtures.
- The exported MCP wrapper passed a real stdio initialization and local workflow discovery call using the existing MCP environment. This checks the wrapper without registering a second server in the current client or running generation.

The source installation previously passed real startup, seven launcher tests, dependency checks, MCP server connection, and validation of the four main 2D graphs. Those are reference-machine results, not proof of a fresh-device restore.

## Cutout update · 2026-11-19

The four maintained 2D graphs now include a selectable `GameArtCutoutFinish` output stage; see [cutout controls and installation](CUTOUT.md). The application lock includes the four tested matting/OpenCV dependencies, and the installer restores the bundled node plus the pinned Image-Filters checkout. No new model weights were downloaded.

- All 22 tests passed in the installed application environment, including numerical mask/polarity checks, exact bypass/RGB-only alpha preservation, hard and soft boundaries, mask batch broadcasting, useful input errors, UI link consistency, and actual temporary Git/bundled-node restore with preservation of modified files. Minimal source CI skips the eight numerical tests when the application libraries are absent.
- The 12 updated UI/API workflow files passed registered-MCP validation with zero errors or warnings; UI exports were converted and their node counts checked. The portable cutout comparison UI graph also passed validation.
- All four complete production workflows ran through registered MCP, then were repeated with the final node revision and returned PNGs. Repeated seeded RGBA outputs matched exactly. Existing prompts, models and generation settings were retained; test output prefixes were isolated. Retouch's output alpha matched the source PNG byte for byte.
- Ten original-reference menu/HUD cases ran again through the final node. The four gold glyphs and ivory plus matched the previously selected successful RGBA results exactly. Visible green pixels in Collection dropped from 2261 to zero and in the white plus from 201 to zero using G-R > 15 and G-B > 15 at alpha >= 128. These are diagnostics for those glyphs, not a general quality percentage or a metric for green artwork.
- General matting still needs a sound initial region. The portrait retains a small clothing-edge spill and partially occluded goggles remain unresolved. Keep its reviewed targeted mask. A cleaner reconstructed avatar ring is preserved; the ordinary core PNG roundtrip can differ by one alpha level, whereas Retouch retains its existing rounding compensation.
- Prior Puzzle2/Puzzle3 files and unrelated/3D workflows were hash-checked as unchanged. Local proof records contain prompt IDs, saved live histories, embedded-workflow checks, PNG hashes and the before/after gallery. User images and machine paths are excluded from this repository.

## Remaining validation limits

A complete clean-machine installation has not been run on another device. The new bootstrap's full network/package installation path still needs its first clean-machine acceptance run. A different OS, GPU architecture, or driver needs its own runtime/model compatibility review.

Static graph validation does not prove every optional workflow or the archived 3D pipeline generates correctly. The Qwen/Z-Image/3D profiles are optional and may need hardware-specific changes. UI extraction requires the user's reference image, which is not bundled.

The installer generates MCP snippets but does not edit a user's client configuration or reconnect it. Complete [MCP acceptance checks](MCP.md) on the receiving device before reporting agent control ready. The provided smoke script uses HTTP and labels that transport explicitly.

The Puzzle Chronicles recipes preserve reference-specific masks and coordinates. New screens need a new asset inventory and appropriate masks/prompts through the skill. PNG delivery does not constitute Unity Editor import/testing.
