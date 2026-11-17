"""Run the official Comfy MCP server with local workflow discovery."""

from pathlib import Path
import os
import subprocess

from comfy_mcp.server import main, mcp

ROOT = Path(os.environ.get('COMFY_PIPELINE_ROOT', str(Path(__file__).resolve().parents[1])))


@mcp.tool()
def list_local_workflows() -> dict:
    """List saved ComfyUI workflows with absolute paths for validate_workflow and run_workflow."""
    root = ROOT
    collections = {
        'project': root / 'Workflows',
        'ui_library': root / 'User' / 'default' / 'workflows',
    }


@mcp.tool()
def start_local_pipeline() -> dict:
    """Start this pipeline with its shared model/input/output/user folders and no app window."""
    result = subprocess.run(
        [str(ROOT / 'ComfyUI/.venv/Scripts/python.exe'), str(ROOT / 'Scripts/launch_comfyui.py'), '--no-browser'],
        cwd=ROOT, capture_output=True, text=True, timeout=200,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0,
    )
    if result.returncode:
        raise RuntimeError((result.stderr + result.stdout).strip() or 'Read Logs/shortcut-launcher.log')
    return {'running': True, 'url': 'http://127.0.0.1:8188', 'root': str(ROOT)}
    return {
        name: [str(path) for path in sorted(folder.rglob('*.json')) if path.is_file()]
        for name, folder in collections.items()
    }


if __name__ == '__main__':
    main()
