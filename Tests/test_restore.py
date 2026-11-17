"""Restore invariants that matter for preserving user files and validating downloads."""
import functools
import hashlib
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import tempfile
import threading
import tomllib
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'Scripts'))
import install_runtime
import model_manager


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *args):
        pass


class RestoreTests(unittest.TestCase):
    def test_download_verifies_hash_and_preserves_a_different_existing_model(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            payload = b'test-model-payload'
            (root/'model').write_bytes(payload)
            handler = functools.partial(QuietHandler, directory=directory)
            server = ThreadingHTTPServer(('127.0.0.1',0),handler)
            thread = threading.Thread(target=server.serve_forever,daemon=True)
            thread.start()
            try:
                model = {'file':'test.safetensors','bytes':len(payload),'sha256':hashlib.sha256(payload).hexdigest(),
                         'url':f'http://127.0.0.1:{server.server_port}/model'}
                target = root/'weights/test.safetensors'
                # A partial file exercises fallback when this test server returns a full response.
                target.parent.mkdir()
                target.with_name(target.name+'.part').write_bytes(payload[:3])
                model_manager.download(model,target)
                self.assertEqual(target.read_bytes(),payload)
                target.write_bytes(b'existing-user-content')
                with self.assertRaises(RuntimeError):
                    model_manager.download(model,target)
                self.assertEqual(target.read_bytes(),b'existing-user-content')
            finally:
                server.shutdown()
                server.server_close()
                thread.join()

    def test_model_path_cannot_escape_shared_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                model_manager.destination(Path(directory),'../outside.safetensors')

    def test_sync_preserves_user_edits_and_config_handles_spaces(self):
        with tempfile.TemporaryDirectory(prefix='pipeline with spaces ') as directory:
            root=Path(directory)
            source=root/'WorkflowLibrary/GameArt/example.json'
            source.parent.mkdir(parents=True)
            source.write_text('{"source":true}')
            self.assertEqual(install_runtime.sync_library(root)['copied'],1)
            target=root/'User/default/workflows/GameArt/example.json'
            target.write_text('{"user_edit":true}')
            self.assertEqual(install_runtime.sync_library(root)['preserved'],1)
            self.assertEqual(json.loads(target.read_text()),{'user_edit':True})
            generated=install_runtime.create_mcp_config(root)
            toml=tomllib.loads((generated/'codex-mcp.toml').read_text())
            server=json.loads((generated/'mcp.json').read_text())['mcpServers']['comfy-mcp']
            self.assertEqual(toml['mcp_servers']['comfy-mcp']['args'],server['args'])
            self.assertEqual(server['env']['COMFY_PIPELINE_ROOT'],str(root))


if __name__=='__main__':
    unittest.main()
