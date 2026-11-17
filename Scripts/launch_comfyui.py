"""Start the local server in the background and open its app window."""

import argparse
from contextlib import contextmanager
import ctypes
import json
import msvcrt
import os
from pathlib import Path
import subprocess
import time
import traceback
from urllib.error import URLError
from urllib.request import ProxyHandler, build_opener

import manage_comfyui as manager

ROOT = manager.ROOT
LOG = ROOT / "Logs" / "shortcut-launcher.log"
TIMEOUT = 180
HTTP = build_opener(ProxyHandler({}))


def server_ready():
    try:
        with HTTP.open(manager.URL + "/system_stats", timeout=2) as response:
            stats = json.load(response)
        if not stats.get("system", {}).get("comfyui_version"):
            return False
        with HTTP.open(manager.URL, timeout=2) as response:
            return response.status == 200
    except (URLError, OSError, ValueError):
        return False


def local_environment():
    # Windows environment names are case insensitive; duplicate PATH/Path keys
    # in the agent's inherited environment can prevent process creation.
    environment = {key.upper(): value for key, value in os.environ.items()}
    local_paths = {
        "AI_ROOT": ROOT,
        "TEMP": ROOT / "Temp",
        "TMP": ROOT / "Temp",
        "PIP_CACHE_DIR": ROOT / "Temp" / "pip-cache",
        "UV_CACHE_DIR": ROOT / "Temp" / "uv-cache",
        "UV_PYTHON_INSTALL_DIR": ROOT / "Tools" / "Python",
        "HF_HOME": ROOT / "Temp" / "huggingface",
        "TORCH_HOME": ROOT / "Temp" / "torch",
        "XDG_CACHE_HOME": ROOT / "Temp" / "cache",
        "MPLCONFIGDIR": ROOT / "Temp" / "matplotlib",
        "CUDA_CACHE_PATH": ROOT / "Temp" / "cuda-cache",
        "VIRTUAL_ENV": manager.REPO / ".venv",
    }
    environment.update({key: str(value) for key, value in local_paths.items()})
    environment.update({
        "PIP_INDEX_URL": "https://pypi.org/simple", "PIP_NO_INDEX": "0",
        "HF_HUB_DISABLE_TELEMETRY": "1", "DO_NOT_TRACK": "1",
        "PYTHONNOUSERSITE": "1", "PYTHONUTF8": "1",
        "PYTHONIOENCODING": "utf-8", "PYTHONUNBUFFERED": "1",
        "PYTHONPATH": "",
    })
    environment["PATH"] = str(manager.PYTHON.parent) + os.pathsep + environment.get("PATH", "")
    return environment


@contextmanager
def launch_lock():
    """Serialize simultaneous shortcut clicks across launcher processes."""
    deadline = time.monotonic() + TIMEOUT
    with (ROOT / "Logs" / "shortcut-launcher.lock").open("a+b") as handle:
        if handle.seek(0, os.SEEK_END) == 0:
            handle.write(b"0")
            handle.flush()
        while True:
            handle.seek(0)
            try:
                msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                break
            except OSError:
                if time.monotonic() >= deadline:
                    raise RuntimeError("Другой запуск ещё выполняется. Повторите через минуту.")
                time.sleep(0.5)
        try:
            yield
        finally:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)


def start_background():
    with LOG.open("a", encoding="utf-8") as output:
        return subprocess.Popen(
            [str(manager.PYTHON), "-u", str(ROOT / "Scripts" / "manage_comfyui.py"), "start"],
            cwd=ROOT, env=local_environment(), stdin=subprocess.DEVNULL,
            stdout=output, stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def ensure_ready():
    if server_ready():
        return
    process = None
    if not manager.owned_process():
        if manager.port_in_use():
            raise RuntimeError("Порт 8188 занят, но ComfyUI не отвечает. Проверьте запущенные приложения.")
        process = start_background()
    deadline = time.monotonic() + TIMEOUT
    while time.monotonic() < deadline:
        if server_ready():
            return
        if process is not None and process.poll() is not None:
            raise RuntimeError("ComfyUI не смог запуститься. Подробности в Logs/shortcut-launcher.log.")
        time.sleep(0.5)
    raise RuntimeError("ComfyUI пока не отвечает. Проверьте Logs/comfyui-*.log и повторите запуск.")


def open_app_window():
    program_dirs = (os.environ.get("ProgramW6432"), os.environ.get("ProgramFiles"),
                    os.environ.get("ProgramFiles(x86)"), os.environ.get("LOCALAPPDATA"))
    for relative in ("Google/Chrome/Application/chrome.exe", "Microsoft/Edge/Application/msedge.exe"):
        for directory in filter(None, program_dirs):
            executable = Path(directory) / relative
            if executable.is_file():
                subprocess.Popen([str(executable), f"--app={manager.URL}"])
                return
    raise RuntimeError("Для окна ComfyUI требуется Chrome или Edge. Сервер доступен на http://127.0.0.1:8188.")


def launch(open_browser=True):
    (ROOT / "Logs").mkdir(exist_ok=True)
    with launch_lock():
        ensure_ready()
    if open_browser:
        open_app_window()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-browser", action="store_true", help="Check startup without opening an app window")
    args = parser.parse_args()
    try:
        launch(open_browser=not args.no_browser)
        return 0
    except Exception as error:
        with LOG.open("a", encoding="utf-8") as output:
            traceback.print_exc(file=output)
        if args.no_browser:
            print(error)
        else:
            ctypes.windll.user32.MessageBoxW(None, str(error), "Запуск ComfyUI", 0x10)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
