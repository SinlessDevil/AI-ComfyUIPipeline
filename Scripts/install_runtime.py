"""Install the pinned Windows/NVIDIA runtime into this repository checkout."""
import argparse
import configparser
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys


def run(*args, env=None):
    print('+', subprocess.list2cmdline([str(a) for a in args]), flush=True)
    subprocess.run([str(a) for a in args], check=True, env=env)


def sync_library(root):
    copied = preserved = 0
    for source in sorted((root / 'WorkflowLibrary').rglob('*.json')):
        target = root / 'User/default/workflows' / source.relative_to(root / 'WorkflowLibrary')
        target.parent.mkdir(parents=True, exist_ok=True)
        if target.exists():
            preserved += 1
        else:
            shutil.copyfile(source, target)
            copied += 1
    return {'copied': copied, 'preserved': preserved}


def install_custom_nodes(root, runtime):
    destination = root / 'ComfyUI/custom_nodes'
    destination.mkdir(parents=True, exist_ok=True)
    for pack in runtime['custom_node_packs']:
        name = pack['name']
        if Path(name).name != name or name in ('.', '..'):
            raise ValueError('Custom node name must be a single directory name')
        target = destination / name
        if pack['source'] == 'bundled':
            source = root / 'CustomNodes' / name
            paths = [p for p in source.rglob('*') if p.is_file() and '__pycache__' not in p.parts]
            if not paths:
                raise RuntimeError(f'Missing bundled custom node: {name}')
            for path in paths:
                existing = target / path.relative_to(source)
                if existing.exists() and existing.read_bytes() != path.read_bytes():
                    raise RuntimeError(f'Existing custom node differs; back it up and update deliberately: {existing}')
            for path in paths:
                existing = target / path.relative_to(source)
                existing.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(path, existing)
        else:
            if not target.exists():
                run('git', 'clone', '--no-checkout', pack['repository'], target)
                run('git', '-C', target, 'checkout', '--detach', pack['commit'])
            actual = subprocess.check_output(['git','-C',str(target),'rev-parse','HEAD'],text=True).strip()
            if actual != pack['commit'] or subprocess.check_output(['git','-C',str(target),'diff','HEAD','--name-only'],text=True).strip():
                raise RuntimeError(f'Existing custom node differs from its pin; preserving it: {name}')
    print('Custom nodes installed from pinned source; dependencies use the application lock.')


def create_mcp_config(root):
    profile = root / 'Tools/ComfyMCP_Profile'
    config_path = profile / 'AppData/Local/comfy-cli/config.ini'
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config = configparser.ConfigParser(interpolation=None)
    if config_path.exists():
        config.read(config_path, encoding='utf-8')
    config['DEFAULT']['default_workspace'] = str(root / 'ComfyUI')
    config['DEFAULT']['enable_tracking'] = 'false'
    # comfy-cli 1.25 splits this field on spaces; use our native launcher tool
    # for shared-directory flags, including installation paths containing spaces.
    config['DEFAULT'].pop('default_launch_extras', None)
    with config_path.open('w', encoding='utf-8') as output:
        config.write(output)
    env = {'COMFY_BIN': str(root / 'Tools/ComfyMCP/Scripts/comfy.exe'),
           'USERPROFILE': str(profile), 'COMFY_PIPELINE_ROOT': str(root),
           'PYTHONUTF8': '1', 'DO_NOT_TRACK': '1'}
    server = {'command': str(root / 'Tools/ComfyMCP/Scripts/python.exe'),
              'args': [str(root / 'Scripts/comfy_mcp_launcher.py')], 'env': env}
    generated = root / 'Logs/generated'
    generated.mkdir(parents=True, exist_ok=True)
    (generated / 'mcp.json').write_text(json.dumps({'mcpServers': {'comfy-mcp': server}}, indent=2), encoding='utf-8')
    # JSON strings are valid TOML basic strings and correctly escape Windows paths.
    toml = ['[mcp_servers.comfy-mcp]', 'command = ' + json.dumps(server['command']),
            'args = ' + json.dumps(server['args']), '', '[mcp_servers.comfy-mcp.env]']
    toml.extend(key + ' = ' + json.dumps(value) for key, value in env.items())
    (generated / 'codex-mcp.toml').write_text('\n'.join(toml) + '\n', encoding='utf-8')
    return generated


def shortcut(root, desktop=False):
    # Pass paths through environment variables rather than embedding them in PowerShell code.
    code = r"""$s = New-Object -ComObject WScript.Shell
$link = $s.CreateShortcut((Join-Path $env:PIPELINE_SHORTCUT_DIR 'ComfyUI.lnk'))
$link.TargetPath = Join-Path $env:COMFY_PIPELINE_ROOT 'ComfyUI\.venv\Scripts\pythonw.exe'
$link.Arguments = '"' + (Join-Path $env:COMFY_PIPELINE_ROOT 'Scripts\launch_comfyui.py') + '"'
$link.WorkingDirectory = $env:COMFY_PIPELINE_ROOT
$link.IconLocation = Join-Path $env:COMFY_PIPELINE_ROOT 'Assets\comfyui.ico'
$link.Save()
"""
    env = os.environ.copy()
    env['COMFY_PIPELINE_ROOT'] = str(root)
    env['PIPELINE_SHORTCUT_DIR'] = str(root)
    run('powershell.exe', '-NoProfile', '-Command', code, env=env)
    if desktop:
        desktop_code = code.replace("$s = New-Object", "$env:PIPELINE_SHORTCUT_DIR = [Environment]::GetFolderPath('Desktop')\n$s = New-Object")
        run('powershell.exe', '-NoProfile', '-Command', desktop_code, env=env)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--uv', type=Path, required=True)
    parser.add_argument('--profile', default='ui')
    parser.add_argument('--download-models', action='store_true')
    parser.add_argument('--desktop-shortcut', action='store_true')
    args = parser.parse_args()
    root = args.root.resolve()
    if sys.platform != 'win32' or sys.version_info[:2] != (3, 12):
        raise RuntimeError('Use Install.ps1 with its managed Python 3.12 on Windows')
    runtime = json.loads((root / 'Config/runtime.lock.json').read_text())
    for folder in ['Models','Input','Output','Temp','Logs','User','Assets','Tools']:
        (root / folder).mkdir(exist_ok=True)
    repository = root / 'ComfyUI'
    if not repository.exists():
        run('git', 'clone', '--depth', '1', '--branch', 'v' + runtime['comfyui_version'], runtime['comfyui_repository'], repository)
    if not (repository / '.git').exists():
        raise RuntimeError('Existing ComfyUI folder is not a Git checkout; preserving it')
    commit = subprocess.check_output(['git','-C',str(repository),'rev-parse','HEAD'],text=True).strip()
    if commit != runtime['comfyui_commit']:
        raise RuntimeError('Existing ComfyUI checkout differs from runtime.lock.json; preserving it')
    if subprocess.check_output(['git','-C',str(repository),'diff','--name-only'],text=True).strip():
        raise RuntimeError('Existing ComfyUI source has local changes; preserving it')
    app_env = repository / '.venv'
    mcp_env = root / 'Tools/ComfyMCP'
    for environment in [app_env, mcp_env]:
        if not (environment / 'Scripts/python.exe').exists():
            run(args.uv, 'venv', '--seed', '--python', sys.executable, environment)
    app_python = app_env / 'Scripts/python.exe'
    mcp_python = mcp_env / 'Scripts/python.exe'
    run(args.uv, 'pip', 'sync', '--python', app_python, '--index-url', 'https://pypi.org/simple',
        '--extra-index-url', runtime['torch_index'], '--index-strategy', 'unsafe-best-match',
        root / 'Config/application.windows-cu130.lock.txt')
    run(args.uv, 'pip', 'sync', '--python', mcp_python, '--index-url', 'https://pypi.org/simple',
        root / 'Config/mcp.windows.lock.txt')
    run(app_python, '-m', 'pip', 'check')
    run(args.uv, 'pip', 'check', '--python', mcp_python)
    install_custom_nodes(root, runtime)
    run(app_python, root / 'Scripts/create_demo_inputs.py')
    print('Workflow library:', sync_library(root))
    generated = create_mcp_config(root)
    if args.download_models:
        run(app_python, root / 'Scripts/model_manager.py', '--root', root, '--profile', args.profile, '--download')
    run(app_python, root / 'Scripts/check_gpu.py')
    run(app_python, '-B', '-m', 'unittest', 'discover', '-s', root / 'Tests')
    shortcut(root, desktop=args.desktop_shortcut)
    print(f'Installed. MCP configuration snippets: {generated}')
    print('Merge one snippet into your client configuration, then reload the client. Client registration is not automatic.')
    print('Launch ComfyUI.lnk. Run Scripts/verify_pipeline.py after startup for a real generation smoke test.')


if __name__ == '__main__':
    main()
