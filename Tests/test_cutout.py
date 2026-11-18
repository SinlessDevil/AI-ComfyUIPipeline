"""Output graph wiring, exact bypass, mask conventions and portable custom-node restore."""
import importlib.util
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'Scripts'))
import install_runtime

HAS_RUNTIME = all(importlib.util.find_spec(name) for name in ['torch','numpy','scipy','pymatting'])
if HAS_RUNTIME:
    import numpy as np
    import torch
    spec = importlib.util.spec_from_file_location('cutout', ROOT/'CustomNodes/GameArt_CutoutLab/__init__.py')
    cutout = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cutout)


class CutoutGraphTests(unittest.TestCase):
    def test_pinned_git_restore_and_modified_source_preservation(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)/'install'
            source=Path(folder)/'upstream'
            source.mkdir()
            def git(*args):
                return subprocess.check_output(['git','-C',str(source),*args],text=True,stderr=subprocess.STDOUT).strip()
            git('init')
            (source/'nodes.py').write_text('version = 1\n')
            git('add','nodes.py')
            git('-c','user.name=Restore test','-c','user.email=restore@example.invalid','commit','-m','Fixture')
            commit=git('rev-parse','HEAD')
            runtime={'custom_node_packs':[{'name':'PinnedExample','source':'git','repository':str(source),'commit':commit}]}
            install_runtime.install_custom_nodes(root,runtime)
            installed=root/'ComfyUI/custom_nodes/PinnedExample/nodes.py'
            self.assertEqual(installed.read_text(),'version = 1\n')
            installed.write_text('user_edit = True\n')
            with self.assertRaises(RuntimeError):
                install_runtime.install_custom_nodes(root,runtime)
            self.assertEqual(installed.read_text(),'user_edit = True\n')

    def test_all_four_output_tails_and_defaults(self):
        for name in ['UI_Asset_Extract','Text_Final','Style_Final','Retouch_Final']:
            graph=json.loads((ROOT/f'Workflows/GameArt/GameArt_{name}_API.json').read_text())
            finish=[(k,n) for k,n in graph.items() if n['class_type']=='GameArtCutoutFinish']
            self.assertEqual(len(finish),1)
            key,node=finish[0]
            join=graph['29' if name=='Retouch_Final' else '37']['inputs']
            self.assertEqual(join['image'],[key,0])
            self.assertEqual(join['alpha'],[key,1])
            self.assertEqual(node['inputs']['mode'],'off' if name=='Retouch_Final' else 'alpha_only')
            self.assertNotEqual(node['inputs']['image'][0],key)

    def test_ui_links_are_bidirectional_and_match_slots(self):
        for folder in ['WorkflowLibrary/GameArt','Workflows/GameArt']:
            for name in ['UI_Asset_Extract','Text_Final','Style_Final','Retouch_Final']:
                graph=json.loads((ROOT/f'{folder}/GameArt_{name}.json').read_text())
                nodes={n['id']:n for n in graph['nodes']}
                for lid,source,output,target,port,kind in graph['links']:
                    self.assertEqual(nodes[target]['inputs'][port]['link'],lid)
                    self.assertIn(lid,nodes[source]['outputs'][output]['links'])

    def test_bundled_restore_preserves_modified_node(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            source=root/'CustomNodes/Example/__init__.py'
            source.parent.mkdir(parents=True)
            source.write_text('version = 1\n')
            runtime={'custom_node_packs':[{'name':'Example','source':'bundled'}]}
            install_runtime.install_custom_nodes(root,runtime)
            target=root/'ComfyUI/custom_nodes/Example/__init__.py'
            target.write_text('user_edit = True\n')
            with self.assertRaises(RuntimeError):
                install_runtime.install_custom_nodes(root,runtime)
            self.assertEqual(target.read_text(),'user_edit = True\n')


@unittest.skipUnless(HAS_RUNTIME,'Run numerical cutout checks inside the installed application environment')
class CutoutRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.node=cutout.GameArtCutoutFinish()
        self.image=torch.full((1,32,32,3),.2)
        self.image[:,8:24,8:24]=torch.tensor([.95,.8,.35])
        self.alpha=torch.ones((1,32,32))
        self.alpha[:,8:24,8:24]=0

    def test_off_returns_original_tensors_exactly(self):
        rgb,alpha=self.node.finish(self.image,self.alpha,'off')
        self.assertIs(rgb,self.image)
        self.assertIs(alpha,self.alpha)

    def test_alpha_only_preserves_rgb_and_mask_polarity(self):
        rgb,alpha=self.node.finish(self.image,self.alpha,'alpha_only')
        self.assertIs(rgb,self.image)
        self.assertLess(float(alpha[0,16,16]),.01)
        self.assertGreater(float(alpha[0,0,0]),.99)

    def test_rgb_only_preserves_alpha_exactly(self):
        _,alpha=self.node.finish(self.image,self.alpha,'rgb_only')
        self.assertIs(alpha,self.alpha)

    def test_shared_mask_broadcasts_and_bad_canvas_errors(self):
        _,alpha=self.node.finish(self.image.repeat(2,1,1,1),self.alpha,'alpha_only')
        self.assertEqual(tuple(alpha.shape),(2,32,32))
        with self.assertRaisesRegex(ValueError,'matching canvases'):
            self.node.finish(self.image,self.alpha[:,:10,:10],'alpha_only')

    def test_full_and_empty_masks_are_preserved(self):
        for value in [0.,1.]:
            mask=torch.full_like(self.alpha,value)
            _,after=self.node.finish(self.image,mask,'alpha_only')
            self.assertTrue(torch.equal(mask,after))

    def test_gold_mode_removes_green_hole_within_coarse_region(self):
        self.image[:,12:20,12:20]=torch.tensor([.1,.65,.1])
        rgb,alpha=self.node.finish(self.image,self.alpha,'gold_on_green')
        self.assertGreater(float(alpha[0,16,16]),.99)
        self.assertLess(float(alpha[0,10,10]),.01)
        self.assertTrue(torch.isfinite(rgb).all())

    def test_unknown_boundary_is_solved_and_keeps_finite_alpha(self):
        self.alpha[:,7:25,7:25]=.5
        self.alpha[:,9:23,9:23]=0
        _,alpha=self.node.finish(self.image,self.alpha,'alpha_only')
        self.assertTrue(torch.isfinite(alpha).all())
        self.assertLess(float(alpha[0,16,16]),.01)
        self.assertGreater(float(alpha[0,0,0]),.99)

    def test_uncertain_mask_reports_missing_seeds(self):
        with self.assertRaisesRegex(ValueError,'known foreground and background'):
            self.node.finish(self.image,torch.full_like(self.alpha,.5),'alpha_only')


if __name__=='__main__':
    unittest.main()
