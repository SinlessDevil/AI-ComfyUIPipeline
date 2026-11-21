"""Edit route of the reference-to-sprite toolkit: graph, run loading, hi-res rule, example recipe and keying."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
EDIT = ROOT/'Pipelines/UnityUIAssets/edit'
sys.path.insert(0, str(EDIT))
import comfy_run
import qwen_edit_graph

HAS_IMAGE_LIBS = all(importlib.util.find_spec(name) for name in ['numpy', 'PIL', 'scipy', 'pymatting'])


class EditGraphTests(unittest.TestCase):
    def test_qwen_graph_wiring(self):
        g = qwen_edit_graph.build('sub/ref.png', [10, 20, 64, 48], 'isolate it', 1234, 'Run/a1', remove_bg=False)
        types = {node['class_type'] for node in g.values()}
        for required in ['UNETLoader', 'CLIPLoader', 'VAELoader', 'LoadImage', 'ImageCrop', 'TextEncodeQwenImageEditPlus',
                         'ModelSamplingAuraFlow', 'CFGNorm', 'KSampler', 'VAEDecode', 'SaveImage']:
            self.assertIn(required, types)
        self.assertNotIn('RemoveBackground', types)
        crop = next(n for n in g.values() if n['class_type'] == 'ImageCrop')['inputs']
        self.assertEqual((crop['x'], crop['y'], crop['width'], crop['height']), (10, 20, 64, 48))
        sampler = next(n for n in g.values() if n['class_type'] == 'KSampler')['inputs']
        self.assertEqual((sampler['seed'], sampler['steps'], sampler['cfg']), (1234, 30, 4.0))
        save = next(n for n in g.values() if n['class_type'] == 'SaveImage')['inputs']
        self.assertEqual(save['filename_prefix'], 'Run/a1/raw')
        for node in g.values():
            for value in node['inputs'].values():
                if isinstance(value, list) and len(value) == 2 and isinstance(value[1], int):
                    self.assertIn(value[0], g, 'dangling link')

    def test_models_are_in_a_pinned_profile(self):
        catalog = json.loads((ROOT/'Config/models.lock.json').read_text(encoding='utf-8'))
        files = {m['id']: Path(m['file']).name for m in catalog['models']}
        profile = {files[i] for i in catalog['profiles']['uiassets']}
        g = qwen_edit_graph.build('x.png', [0, 0, 8, 8], 'p', 1, 'p', remove_bg=True)
        used = {v for n in g.values() for k, v in n['inputs'].items() if k in ('unet_name', 'clip_name', 'vae_name', 'bg_removal_name')}
        self.assertTrue(used <= profile, used - profile)


class RunHelperTests(unittest.TestCase):
    def test_hires_rule(self):
        self.assertIsNone(comfy_run.hires_size([128, 40]))
        self.assertEqual(comfy_run.hires_size([55, 55]), (275, 275))
        self.assertEqual(comfy_run.hires_size([33, 28]), (264, 224))
        self.assertEqual(comfy_run.hires_size([100, 20]), (400, 80))

    def test_arguments_and_seeds(self):
        self.assertEqual(comfy_run.parse_args(['a', '--attempt', '3', 'b', '--batch', '--seed', '7']), (7, 3, True, ['a', 'b']))
        self.assertEqual(comfy_run.default_seed('a', 2), comfy_run.default_seed('a', 2))
        self.assertNotEqual(comfy_run.default_seed('a', 1), comfy_run.default_seed('a', 2))

    def test_relative_paths_resolve_against_the_run(self):
        with tempfile.TemporaryDirectory() as folder:
            run = Path(folder)/'runs'/'r1'
            run.mkdir(parents=True)
            (run/'run.json').write_text(json.dumps({'ref_dir': '../../refs', 'baseline_root': 'base'}), encoding='utf-8')
            (run/'tasks.json').write_text(json.dumps([{'id': 'a', 'ref': 'Screens/s.png', 'crop': [0, 0, 4, 4], 'target': [4, 4]},
                                                      {'id': 'b', 'ref_abs': 'Attempts/a/a1/raw.png', 'crop': [0, 0, 4, 4],
                                                       'target': [4, 4], 'fit': 'alpha_from', 'alpha_from': 'Unity/x.png'}]),
                                          encoding='utf-8')
            loaded_run, cfg, tasks = comfy_run.load_run(str(run/'tasks.json'))
            self.assertEqual(Path(loaded_run), run)
            self.assertEqual(Path(comfy_run.src_path(tasks['a'], cfg)), Path(folder)/'refs'/'Screens'/'s.png')
            self.assertEqual(Path(comfy_run.src_path(tasks['b'], cfg)), run/'Attempts'/'a'/'a1'/'raw.png')
            self.assertEqual(Path(comfy_run.alpha_path(tasks['b'], cfg)), run/'base'/'Unity'/'x.png')

    def test_no_machine_specific_paths_in_tools(self):
        for path in EDIT.glob('*.py'):
            text = path.read_text(encoding='utf-8')
            self.assertNotRegex(text, r"['\"][A-Za-z]:[\\/]", path.name)


class ExampleRecipeTests(unittest.TestCase):
    def test_puzzle_memories_tasks(self):
        folder = ROOT/'Examples/PuzzleMemories'
        tasks = json.loads((folder/'tasks.json').read_text(encoding='utf-8'))
        ids = [t['id'] for t in tasks]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(ids), 40)
        for t in tasks:
            self.assertEqual(len(t['crop']), 4, t['id'])
            self.assertEqual(len(t['target']), 2, t['id'])
            self.assertTrue(t.get('ref') or t.get('ref_abs'), t['id'])
            self.assertTrue(t.get('edit') or (t.get('subject') and t.get('geometry')), t['id'])
            self.assertIn(t.get('match', False), (False, True, 'flat'), t['id'])
            if t.get('fit'):
                self.assertEqual(t['fit'], 'alpha_from')
                self.assertTrue(t.get('alpha_from'), t['id'])
            if t.get('ref_abs'):
                self.assertFalse(os.path.isabs(t['ref_abs']), t['id'])


@unittest.skipUnless(HAS_IMAGE_LIBS, 'numpy, Pillow, scipy and pymatting are installed in the application environment')
class KeyingTests(unittest.TestCase):
    def test_gray_key_keeps_body_and_enclosed_hole(self):
        import numpy as np
        from PIL import Image
        with tempfile.TemporaryDirectory() as folder:
            yy, xx = np.mgrid[0:200, 0:200]
            r = np.hypot(xx - 100, yy - 100)
            img = np.full((200, 200, 3), 200, np.uint8)
            img[r < 70] = (40, 140, 60)
            img[r < 20] = (200, 200, 200)
            Image.fromarray(img).save(Path(folder)/'raw.png')
            out = Path(folder)/'final.png'
            subprocess.run([sys.executable, str(EDIT/'key_bg.py'), str(Path(folder)/'raw.png'), str(out), '64', '64'],
                           check=True, stdin=subprocess.DEVNULL, capture_output=True)
            rgba = np.asarray(Image.open(out).convert('RGBA'))
            self.assertEqual(rgba.shape, (64, 64, 4))
            self.assertEqual(rgba[0, 0, 3], 0)
            self.assertEqual(rgba[32, 32, 3], 0, 'enclosed key-coloured hole must stay transparent')
            ring = rgba[32, 12]
            self.assertGreater(ring[3], 240)
            self.assertGreater(int(ring[1]), int(ring[0]) + 50, 'body keeps its green colour')
