"""Re-run keying / colour matching (and the hi-res master) from an existing raw.png, without the GPU.
Usage: python reprocess.py <run>/tasks.json <id>:a<N> [key args, e.g. --t1 8 --t2 30]"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_run  # noqa: E402

if len(sys.argv) < 3:
    raise SystemExit(__doc__)
run, cfg, tasks = comfy_run.load_run(sys.argv[1])
aid, att = sys.argv[2].split(':')
task = dict(tasks[aid])
if len(sys.argv) > 3:
    task['key_args'] = sys.argv[3:]
d = os.path.join(run, 'Attempts', aid, att)
made = comfy_run.postprocess(task, cfg, d)
rec_p = os.path.join(d, 'record.json')
rec = json.load(open(rec_p, encoding='utf-8')) if os.path.exists(rec_p) else {'asset': aid}
rec.setdefault('reprocess', []).append({'key_args': task.get('key_args', []), 'match': task.get('match', False), 'files': made})
json.dump(rec, open(rec_p, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
print(aid, att, made)
