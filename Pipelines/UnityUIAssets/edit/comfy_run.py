"""Generate sprites from mockup crops on the local ComfyUI and post-process them.

Usage: python comfy_run.py <run>/tasks.json <id> [<id> ...] [--attempt N] [--seed S] [--batch]

Per asset and attempt writes <run>/Attempts/<id>/a<N>/: graph_api.json, record.json, raw.png, final.png
and, for small assets, final_hires.png (see HIRES_*).
--batch submits every job to the ComfyUI queue first and collects afterwards (the GPU never idles).
Paths come from <run>/run.json: {"ref_dir": ..., "baseline_manifest": ..., "baseline_root": ...}.
Relative paths in run.json are resolved against the run folder.

Environment overrides: COMFY_HOST (default http://127.0.0.1:8188), COMFY_PIPELINE_ROOT (installation root,
default four levels above this file), UNITY_UI_ASSETS_PYTHON (interpreter with numpy, Pillow, scipy, pymatting;
default the installation's ComfyUI/.venv, else the current interpreter).
"""
import copy
import json
import os
import subprocess
import sys
import time
import urllib.parse
import urllib.request
import uuid

HOST = os.environ.get('COMFY_HOST', 'http://127.0.0.1:8188').rstrip('/')
TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.environ.get('COMFY_PIPELINE_ROOT') or os.path.abspath(os.path.join(TOOLS, '..', '..', '..'))


def _image_python():
    if os.environ.get('UNITY_UI_ASSETS_PYTHON'):
        return os.environ['UNITY_UI_ASSETS_PYTHON']
    for rel in (('ComfyUI', '.venv', 'Scripts', 'python.exe'), ('ComfyUI', '.venv', 'bin', 'python')):
        candidate = os.path.join(ROOT, *rel)
        if os.path.exists(candidate):
            return candidate
    return sys.executable


VENV_PY = _image_python()
FLUX_GRAPH = os.path.join(ROOT, 'Workflows', 'GameArt', 'GameArt_UI_Asset_Extract_API.json')
UPLOAD_SUB = 'UnityUIAssetsEdit'
# Small-asset rule: when the target's long side is below HIRES_BELOW px, also export a high-resolution
# master whose long side is at least HIRES_MIN (and at least 4x the target). Unity can downscale it; the
# exact-size PNG stays the runtime default.
HIRES_BELOW = 128
HIRES_MIN = 256
GRAY = ('Place it centered on a plain flat uniform light gray background (#c8c8c8) with empty margin on every side. '
        'No text, no shadow on the background.')
STYLE = ('Warm illustrated casual mobile puzzle game UI, painted rounded forms, soft controlled shading, upper-left light. '
         'Match the colors of the reference crop exactly: same hue, saturation and brightness. Do not add outlines, '
         'rims or bevels that the reference does not have.')
NEGATIVE = ('No lettering, no numbers, no text, no extra ornaments, no glow, no large white specular blobs, '
            'no mirror-like gloss, no external cast shadow, no neighbouring UI elements.')


def http(method, path, data=None, headers=None):
    req = urllib.request.Request(HOST + path, data=data, method=method, headers=headers or {})
    with urllib.request.urlopen(req, timeout=120) as r:
        return r.read()


def upload(local_path, name):
    boundary = uuid.uuid4().hex
    body = []
    for k, v in (('subfolder', UPLOAD_SUB), ('overwrite', 'true'), ('type', 'input')):
        body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode())
    body.append(f'--{boundary}\r\nContent-Disposition: form-data; name="image"; filename="{name}"\r\n'
                f'Content-Type: image/png\r\n\r\n'.encode())
    body.append(open(local_path, 'rb').read())
    body.append(f'\r\n--{boundary}--\r\n'.encode())
    res = json.loads(http('POST', '/upload/image', b''.join(body),
                          {'Content-Type': 'multipart/form-data; boundary=' + boundary}))
    return (res.get('subfolder') + '/' if res.get('subfolder') else '') + res['name']


def src_path(task, cfg):
    """Reference image of a task: `ref` under run.json ref_dir, or `ref_abs` (absolute, or relative to the run)."""
    if task.get('ref_abs'):
        return os.path.join(cfg.get('_run', ''), task['ref_abs'])
    return os.path.join(cfg['ref_dir'], task['ref'])


def alpha_path(task, cfg):
    """`alpha_from` sprite for fit=alpha_from tasks: absolute, or relative to run.json baseline_root."""
    return os.path.join(cfg.get('baseline_root') or cfg.get('_run', ''), task['alpha_from'])


def read_json(path):
    with open(path, encoding='utf-8') as f:
        return json.load(f)


def load_run(tasks_json):
    """Read <run>/tasks.json and <run>/run.json; relative run.json paths resolve against the run folder."""
    tasks_path = os.path.abspath(tasks_json)
    run = os.path.dirname(tasks_path)
    cfg = read_json(os.path.join(run, 'run.json'))
    for key in ('ref_dir', 'baseline_manifest', 'baseline_root'):
        if cfg.get(key) and not os.path.isabs(cfg[key]):
            cfg[key] = os.path.normpath(os.path.join(run, cfg[key]))
    cfg['_run'] = run
    tasks = {t['id']: t for t in read_json(tasks_path)}
    return run, cfg, tasks


def parse_args(args):
    seed, attempt, batch, ids = None, 1, False, []
    i = 0
    while i < len(args):
        if args[i] == '--seed':
            seed = int(args[i + 1]); i += 2
        elif args[i] == '--attempt':
            attempt = int(args[i + 1]); i += 2
        elif args[i] == '--batch':
            batch = True; i += 1
        else:
            ids.append(args[i]); i += 1
    return seed, attempt, batch, ids


def default_seed(asset_id, attempt):
    return 1000 + attempt * 7919 + sum(map(ord, asset_id))


def hires_size(target):
    """Exact-size target -> high-resolution master size, or None when the asset is large enough."""
    tw, th = target
    if max(tw, th) >= HIRES_BELOW:
        return None
    k = max(4, -(-HIRES_MIN // max(tw, th)))
    return tw * k, th * k


def build_qwen(task, cfg, seed, prefix):
    sys.path.insert(0, TOOLS)
    import qwen_edit_graph
    name = upload(src_path(task, cfg), task['id'] + '_src.png')
    prompt = task.get('edit') or (
        'Isolate ' + task['subject'] + ' from this game screenshot crop. ' + task['geometry'] + ' '
        'Remove every other element: neighbouring buttons, icons, text, numbers, background. '
        'Complete any part of it that is hidden or cut off. Keep its exact colors, shading, proportions and art style. '
        + GRAY)
    return qwen_edit_graph.build(name, task['crop'], prompt, seed, prefix, steps=task.get('steps', 30),
                                 cfg=task.get('cfg', 4.0), megapixels=task.get('mp', 1.0),
                                 finish_mode=task.get('finish_mode', 'alpha_only'), remove_bg=False)


def build_flux(task, cfg, seed, prefix):
    g = copy.deepcopy(json.load(open(FLUX_GRAPH, encoding='utf-8')))
    g['16']['inputs']['image'] = upload(src_path(task, cfg), task['id'] + '_src.png')
    x, y, w, h = task['crop']
    g['40']['inputs'].update({'x': x, 'y': y, 'width': w, 'height': h})
    g['5']['inputs']['value'], g['6']['inputs']['value'] = task.get('size', [768, 768])
    g['9']['inputs']['noise_seed'] = seed
    g['20']['inputs']['value'] = ('Use the attached reference crop as the visual authority. Reproduce only ' + task['subject'] + '. '
                                  + task['geometry'] + ' ' + cfg.get('style', STYLE) + ' ' + NEGATIVE)
    g['21']['inputs']['value'] = 'Produce one isolated component centered on a uniform flat neutral gray background.'
    g['22']['inputs']['value'] = False
    g['15']['inputs']['filename_prefix'] = prefix + '/raw'
    g['42']['inputs']['filename_prefix'] = prefix + '/raw_dup'
    return g


def postprocess(task, cfg, out_dir):
    raw = os.path.join(out_dir, 'raw.png')
    final = os.path.join(out_dir, 'final.png')
    made = []
    if task.get('fit') == 'alpha_from':
        subprocess.run([VENV_PY, os.path.join(TOOLS, 'fit_alpha.py'), raw, final, alpha_path(task, cfg)],
                       check=True, stdin=subprocess.DEVNULL)
        return ['final.png']
    tw, th = task['target']
    sizes = [('final.png', tw, th)]
    if hires_size(task['target']):
        sizes.append(('final_hires.png', *hires_size(task['target'])))
    for name, w, h in sizes:
        out = os.path.join(out_dir, name)
        subprocess.run([VENV_PY, os.path.join(TOOLS, 'key_bg.py'), raw, out, str(w), str(h)]
                       + [str(v) for v in task.get('key_args', [])], check=True, stdin=subprocess.DEVNULL)
        if task.get('match'):
            args = [VENV_PY, os.path.join(TOOLS, 'color_match.py'), out, src_path(task, cfg)] + [str(v) for v in task['crop']]
            if task.get('match') == 'flat':
                args.append('--flat')
            if task.get('colors_from'):
                args += ['--colors-from', task['colors_from']]
            subprocess.run(args, check=True, stdin=subprocess.DEVNULL)
        made.append(name)
    return made


def submit(task, cfg, run, attempt, seed):
    out_dir = os.path.join(run, 'Attempts', task['id'], f'a{attempt}')
    os.makedirs(out_dir, exist_ok=True)
    prefix = f'{UPLOAD_SUB}/{os.path.basename(run)}/{task["id"]}/a{attempt}'
    g = build_qwen(task, cfg, seed, prefix) if task.get('engine', 'qwen') == 'qwen' else build_flux(task, cfg, seed, prefix)
    json.dump(g, open(os.path.join(out_dir, 'graph_api.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    res = json.loads(http('POST', '/prompt', json.dumps({'prompt': g, 'client_id': 'unity-ui-assets-edit'}).encode(),
                          {'Content-Type': 'application/json'}))
    return out_dir, res['prompt_id']


def collect(task, cfg, out_dir, pid, attempt, seed):
    for _ in range(1800):
        hist = json.loads(http('GET', '/history/' + pid))
        if pid in hist and hist[pid].get('status', {}).get('completed') is not None:
            break
        time.sleep(1)
    else:
        raise RuntimeError('timeout ' + pid)
    h = hist[pid]
    files = []
    for node, out in h.get('outputs', {}).items():
        for im in out.get('images', []):
            if im.get('type') != 'output' or 'raw_dup' in im.get('subfolder', '') + im.get('filename', ''):
                continue
            q = urllib.parse.urlencode({'filename': im['filename'], 'subfolder': im['subfolder'], 'type': 'output'})
            open(os.path.join(out_dir, 'raw.png'), 'wb').write(http('GET', '/view?' + q))
            files.append('raw.png')
    if 'raw.png' in files:
        files += postprocess(task, cfg, out_dir)
    rec = {'asset': task['id'], 'attempt': attempt, 'seed': seed, 'prompt_id': pid,
           'status': h.get('status', {}).get('status_str'), 'files': files, 'task': task,
           'engine': task.get('engine', 'qwen'), 'time': time.strftime('%Y-%m-%dT%H:%M:%S')}
    json.dump(rec, open(os.path.join(out_dir, 'record.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return rec


def main():
    args = sys.argv[1:]
    if not args or args[0] in ('-h', '--help'):
        raise SystemExit(__doc__)
    run, cfg, tasks = load_run(args[0])
    seed, attempt, batch, ids = parse_args(args[1:])
    unknown = [a for a in ids if a not in tasks]
    if unknown:
        raise SystemExit('Unknown asset id(s): ' + ', '.join(unknown))
    seeds = {a: seed if seed is not None else default_seed(a, attempt) for a in ids}
    if batch:
        pending = [(a, *submit(tasks[a], cfg, run, attempt, seeds[a])) for a in ids]
        print('submitted', len(pending), flush=True)
        for a, out_dir, pid in pending:
            try:
                rec = collect(tasks[a], cfg, out_dir, pid, attempt, seeds[a])
                print(a, 'a%d' % attempt, rec['status'], pid, rec['files'], flush=True)
            except Exception as e:  # keep collecting the rest of the batch
                print('FAIL', a, e, flush=True)
    else:
        for a in ids:
            out_dir, pid = submit(tasks[a], cfg, run, attempt, seeds[a])
            rec = collect(tasks[a], cfg, out_dir, pid, attempt, seeds[a])
            print(a, 'a%d' % attempt, rec['status'], pid, rec['files'], flush=True)


if __name__ == '__main__':
    main()
