r"""Run: .\ComfyUI\.venv\Scripts\python.exe -m unittest discover -s Tests"""

from contextlib import nullcontext
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "Scripts"))
import launch_comfyui as launcher


class LauncherTests(unittest.TestCase):
    def test_running_server_is_reused(self):
        with patch.object(launcher, "server_ready", return_value=True), \
                patch.object(launcher, "start_background") as start:
            launcher.ensure_ready()
            start.assert_not_called()

    def test_cold_start_waits_for_ready(self):
        process = Mock()
        process.poll.return_value = None
        with patch.object(launcher, "server_ready", side_effect=[False, False, True]), \
                patch.object(launcher.manager, "owned_process", return_value=None), \
                patch.object(launcher.manager, "port_in_use", return_value=False), \
                patch.object(launcher, "start_background", return_value=process) as start, \
                patch.object(launcher.time, "sleep"):
            launcher.ensure_ready()
            start.assert_called_once()

    def test_existing_startup_does_not_spawn_another_server(self):
        with patch.object(launcher, "server_ready", side_effect=[False, True]), \
                patch.object(launcher.manager, "owned_process", return_value=Mock()), \
                patch.object(launcher, "start_background") as start:
            launcher.ensure_ready()
            start.assert_not_called()

    def test_unrelated_port_is_not_opened(self):
        with patch.object(launcher, "server_ready", return_value=False), \
                patch.object(launcher.manager, "owned_process", return_value=None), \
                patch.object(launcher.manager, "port_in_use", return_value=True), \
                patch.object(launcher, "start_background") as start:
            with self.assertRaises(RuntimeError):
                launcher.ensure_ready()
            start.assert_not_called()

    def test_failed_start_does_not_open_app_window(self):
        with patch.object(launcher, "launch_lock", return_value=nullcontext()), \
                patch.object(launcher, "ensure_ready", side_effect=RuntimeError("Failed")), \
                patch.object(launcher, "open_app_window") as browser:
            with self.assertRaises(RuntimeError):
                launcher.launch()
            browser.assert_not_called()

    def test_app_window_opens_after_readiness(self):
        events = []
        with patch.object(launcher, "launch_lock", return_value=nullcontext()), \
                patch.object(launcher, "ensure_ready", side_effect=lambda: events.append("ready")), \
                patch.object(launcher, "open_app_window", side_effect=lambda *a, **k: events.append("app")):
            launcher.launch()
        self.assertEqual(events, ["ready", "app"])

    def test_environment_is_local_and_case_insensitive(self):
        with patch.dict(launcher.os.environ, {"Path": "first", "PATH": "second"}, clear=True):
            environment = launcher.local_environment()
        self.assertNotIn("Path", environment)
        self.assertEqual(environment["HF_HOME"], str(launcher.ROOT / "Temp" / "huggingface"))
        self.assertEqual(environment["PYTHONPATH"], "")


if __name__ == "__main__":
    unittest.main()
