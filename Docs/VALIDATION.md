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

## Not claimed by this export

A complete clean-machine installation has not been run on another device. The new bootstrap's full network/package installation path still needs its first clean-machine acceptance run. A different OS, GPU architecture, or driver needs its own runtime/model compatibility review.

Static graph validation does not prove every optional workflow or the archived 3D pipeline generates correctly. The Qwen/Z-Image/3D profiles are optional and may need hardware-specific changes. UI extraction requires the user's reference image, which is not bundled.

The installer generates MCP snippets but does not edit a user's client configuration or reconnect it. Complete [MCP acceptance checks](MCP.md) on the receiving device before reporting agent control ready. The provided smoke script uses HTTP and labels that transport explicitly.

The Puzzle Chronicles recipes preserve reference-specific masks and coordinates. New screens need a new asset inventory and appropriate masks/prompts through the skill. PNG delivery does not constitute Unity Editor import/testing.
