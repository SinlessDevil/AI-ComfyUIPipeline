# Local MCP connection

Implementation: [official Comfy MCP](https://github.com/Comfy-Org/comfy-mcp), driven by [comfy-cli](https://github.com/Comfy-Org/comfy-cli). The separate environment is `Tools/ComfyMCP`; its CLI profile is `Tools/ComfyMCP_Profile`. Both are ignored runtime folders.

Installation generates absolute paths for the current checkout in `Logs/generated/mcp.json` and `Logs/generated/codex-mcp.toml`. Merge exactly one server entry into your client's existing configuration and reload the connection. Do not replace the whole client config or copy credentials from another machine. The installer prepares the snippets but does not automatically register the server in the client.

The registration runs `Scripts/comfy_mcp_launcher.py` through the MCP environment. It retains official tools and adds:

- `list_local_workflows`: list absolute paths from maintained templates and the UI library.
- `start_local_pipeline`: start the existing backend through the native no-browser launcher with explicit shared Models/Input/Output/Temp/User paths.

Use `server_info` first, then `start_local_pipeline` if the backend is stopped. The native launcher handles paths containing spaces. comfy-cli 1.25's generic launch settings do not encode our shared path arguments reliably, so use the wrapper or app shortcut for startup.

## Acceptance checks through the registered client

1. Call `server_info` and confirm the intended local workspace/backend. Start it if needed, then check again.
2. Call `list_local_workflows`. Select a local API graph for the installed model profile and call `validate_workflow`.
3. Make a test copy with a new seed and a unique output prefix. Submit with `run_workflow(wait=false)`.
4. Wait through `job` and require successful completion, not a cached previous result.
5. Use `fetch_outputs`, decode the actual image, and report the prompt ID and output path.
6. Verify failure handling with a test-only copy whose model or input selection is deliberately invalid. Preserve the backend's useful error details. Leave the real workflow unchanged.

If the client cannot see the tools after config generation, MCP is not registered yet. If the backend is stopped or the model profile is absent, finish those parts before claiming readiness. API-only checks must be labeled separately. Local test graphs must not invoke paid partner nodes.

The upstream [MCP documentation](https://docs.comfy.org/agent-tools/mcp) describes client-specific connection details. Keep API keys out of the committed examples.
