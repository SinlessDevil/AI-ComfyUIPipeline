"""Write a review_sheet.ps1 list: reference crop, then final.png of each attempt.
Usage: python make_review.py <run>/tasks.json <out_list.txt> id[:a1,a2] ...  (default: all attempts)"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import comfy_run  # noqa: E402

if len(sys.argv) < 4:
    raise SystemExit(__doc__)
run, cfg, tasks = comfy_run.load_run(sys.argv[1])
lines = []
for arg in sys.argv[3:]:
    i, _, att = arg.partition(':')
    t = tasks[i]
    d = os.path.join(run, 'Attempts', i)
    atts = att.split(',') if att else (sorted(os.listdir(d)) if os.path.isdir(d) else [])
    files = []
    for a in atts:
        for name in ('final.png', 'raw.png'):
            p = os.path.join(d, a, name)
            if os.path.exists(p):
                files.append(p.replace('\\', '/'))
                break
    ref = comfy_run.src_path(t, cfg)
    x, y, w, h = t['crop']
    lines.append('|'.join([i + '  ' + ' '.join(atts), ref.replace('\\', '/'), str(x), str(y), str(w), str(h)] + files))
open(sys.argv[2], 'w', encoding='utf-8').write('\n'.join(lines))
print(len(lines))
