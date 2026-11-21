"""Check the publishable source tree for binary/runtime files, broken links, and invalid source."""
import ast
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]
DIRECTORIES = {'CustomNodes','Config','Docs','Examples','Pipelines','Scripts','Tests','Workflows','WorkflowLibrary','skills','.github'}
ROOT_FILES = {'.gitignore','.gitattributes','.env.example','README.md','AGENTS.md','GAME_ART_PIPELINE.md',
              'Install.ps1','INSTALL.bat','START_COMFYUI.bat','OPEN_COMFYUI.bat','STOP_COMFYUI.bat','UPDATE_COMFYUI.bat'}
EXTENSIONS = {'.py','.json','.md','.yaml','.yml','.ps1','.bat','.txt','.cjs','.cs'}
RUNTIME_PARTS = {'runs','History','__pycache__'}


def files():
    result = []
    for name in ROOT_FILES:
        path = ROOT / name
        if path.is_file():
            result.append(path)
    for name in DIRECTORIES:
        folder = ROOT / name
        if folder.exists():
            for path in folder.rglob('*'):
                if path.is_file() and not RUNTIME_PARTS.intersection(path.relative_to(ROOT).parts):
                    result.append(path)
    return sorted(set(result))


def main():
    candidates = files()
    total = links = 0
    for path in candidates:
        relative = path.relative_to(ROOT).as_posix()
        if path.name not in ROOT_FILES and path.suffix not in EXTENSIONS:
            raise ValueError(f'Non-source file in publish set: {relative}')
        if path.is_symlink() or path.stat().st_size > 2 * 1024 * 1024:
            raise ValueError(f'Unexpected link or large source: {relative}')
        raw = path.read_bytes()
        if b'\0' in raw:
            raise ValueError(f'Binary content: {relative}')
        text = raw.decode('utf-8-sig')
        total += len(raw)
        if re.search(r'(?:sk-[A-Za-z0-9]{25,}|gh[pousr]_[A-Za-z0-9]{25,}|github_pat_[A-Za-z0-9_]{30,})', text):
            raise ValueError(f'Possible credential in {relative}')
        if re.search(r'[A-Z]:[\\/]Users[\\/]', text, re.I):
            raise ValueError(f'Personal absolute path in {relative}')
        if path.suffix == '.py':
            ast.parse(text, filename=relative)
        elif path.suffix == '.json':
            json.loads(text)
        elif path.suffix == '.md':
            for target in re.findall(r'\[[^\]]*\]\(([^)]+)\)', text):
                if target.startswith(('http://','https://','#')):
                    continue
                target = target.split('#')[0]
                if target and not (path.parent / target).exists():
                    raise ValueError(f'Broken link in {relative}: {target}')
                links += 1
    catalog = json.loads((ROOT/'Config/models.lock.json').read_text())
    ids = [item['id'] for item in catalog['models']]
    assert len(ids) == len(set(ids))
    for model in catalog['models']:
        assert re.fullmatch(r'[a-f0-9]{64}',model['sha256'])
        assert re.fullmatch(r'[a-f0-9]{40}',model['revision'])
        assert model['url'].startswith('https://huggingface.co/') and model['revision'] in model['url']
    for lock in ['application.windows-cu130.lock.txt','mcp.windows.lock.txt']:
        for line in (ROOT/'Config'/lock).read_text(encoding='utf-8-sig').splitlines():
            if line and not line.startswith('#'):
                assert re.fullmatch(r'[A-Za-z0-9_.-]+==[^\s]+',line), f'Nonportable dependency: {line}'
    print(json.dumps({'source_files':len(candidates),'bytes':total,'local_links':links,'model_entries':len(ids)},indent=2))


if __name__ == '__main__':
    main()
