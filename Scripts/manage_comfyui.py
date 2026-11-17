import argparse
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import socket
import subprocess
import sys
import time

import psutil

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT / "ComfyUI"
PYTHON = REPO / ".venv" / "Scripts" / "python.exe"
STATE = ROOT / "Logs" / "comfyui-process.json"
URL = "http://127.0.0.1:8188"


def port_in_use():
    with socket.socket() as connection:
        connection.settimeout(1)
        return connection.connect_ex(("127.0.0.1", 8188)) == 0


def owned_process():
    if not STATE.exists():
        return None
    state = json.loads(STATE.read_text(encoding="utf-8"))
    try:
        process = psutil.Process(state["pid"])
        if abs(process.create_time() - state["create_time"]) > 0.01:
            return None
        command = process.cmdline()
        if Path(process.exe()).resolve() != PYTHON.resolve() or str(REPO / "main.py") not in command:
            raise RuntimeError("PID identity check failed; refusing to stop this process")
        return process
    except psutil.NoSuchProcess:
        return None


def start():
    if owned_process() or port_in_use():
        print(f"Server or another application already uses {URL}. Open OPEN_COMFYUI.bat.")
        return 0
    args = [str(PYTHON), "-u", str(REPO / "main.py"),
            "--listen", "127.0.0.1", "--port", "8188", "--enable-manager",
            "--models-directory", str(ROOT / "Models"),
            "--input-directory", str(ROOT / "Input"),
            "--output-directory", str(ROOT / "Output"),
            "--temp-directory", str(ROOT / "Temp" / "comfyui"),
            "--user-directory", str(ROOT / "User"),
            "--disable-auto-launch"]
    log = ROOT / "Logs" / f"comfyui-{datetime.now():%Y%m%d-%H%M%S}.log"
    environment = os.environ.copy()
    environment["PYTHONUNBUFFERED"] = "1"
    child = subprocess.Popen(args, cwd=REPO, env=environment, stdout=subprocess.PIPE,
                             stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    STATE.write_text(json.dumps({"pid": child.pid, "create_time": psutil.Process(child.pid).create_time(),
                                 "python": str(PYTHON), "log": str(log), "url": URL}, indent=2), encoding="utf-8")
    print(f"ComfyUI: {URL}\nLog: {log}\nCtrl+C stops the server.", flush=True)
    try:
        with log.open("w", encoding="utf-8", buffering=1) as output:
            for line in child.stdout:
                output.write(line)
                print(line, end="", flush=True)
        code = child.wait()
        # STOP removes the state after verifying process identity and terminating it.
        if code and (not STATE.exists() or json.loads(STATE.read_text(encoding="utf-8")).get("stop_requested")):
            return 0
        return code
    except KeyboardInterrupt:
        try:
            child.wait(timeout=10)
        except subprocess.TimeoutExpired:
            child.terminate()
            child.wait(timeout=10)
        return 0
    finally:
        if child.poll() is None:
            child.terminate()
            child.wait(timeout=10)
        if STATE.exists() and json.loads(STATE.read_text(encoding="utf-8"))["pid"] == child.pid:
            STATE.unlink()


def stop():
    process = owned_process()
    if process is None:
        print("No server started by this setup is running.")
        return 0
    print(f"Stopping ComfyUI PID {process.pid}. Any active generation will be interrupted.")
    state = json.loads(STATE.read_text(encoding="utf-8"))
    state["stop_requested"] = True
    STATE.write_text(json.dumps(state, indent=2), encoding="utf-8")
    process.terminate()
    process.wait(timeout=15)
    if STATE.exists():
        STATE.unlink()
    return 0


def update():
    if owned_process() or port_in_use():
        raise RuntimeError("Stop ComfyUI before updating (STOP_COMFYUI.bat)")
    def git(*args):
        return subprocess.check_output(["git", "-C", str(REPO), *args], text=True, encoding="utf-8").strip()
    if git("diff", "--name-only") or git("diff", "--cached", "--name-only"):
        raise RuntimeError("Tracked source files were changed; save your changes before updating")
    if git("remote", "get-url", "origin").removesuffix(".git") != "https://github.com/Comfy-Org/ComfyUI":
        raise RuntimeError("Origin is not the official ComfyUI repository")
    backup = ROOT / "Logs" / f"update-{datetime.now():%Y%m%d-%H%M%S}"
    backup.mkdir()
    previous = git("rev-parse", "HEAD")
    (backup / "previous-commit.txt").write_text(previous, encoding="utf-8")
    freeze = subprocess.check_output([str(PYTHON), "-m", "pip", "freeze"], text=True)
    (backup / "requirements-before.txt").write_text(freeze, encoding="utf-8")
    shutil.copytree(ROOT / "User", backup / "User", ignore=shutil.ignore_patterns("*.log", "__pycache__"))
    git("fetch", "origin", "--tags")
    versions = [tag for tag in git("tag", "--list", "v*").splitlines() if re.fullmatch(r"v\d+\.\d+\.\d+", tag)]
    newest = max(versions, key=lambda tag: tuple(map(int, tag[1:].split("."))))
    print(f"Updating to official stable release {newest}. Backup: {backup}", flush=True)
    git("switch", "--detach", newest)
    # Preserve the verified CUDA build. Upgrading PyTorch is a separate explicit operation.
    command = [str(REPO / ".venv" / "Scripts" / "uv.exe"), "pip", "install", "--python", str(PYTHON),
               "-r", str(REPO / "requirements.txt"), "-r", str(REPO / "manager_requirements.txt"),
               "-c", str(ROOT / "Scripts" / "torch-constraints.txt"),
               "--index-url", "https://pypi.org/simple",
               "--extra-index-url", "https://download.pytorch.org/whl/cu130"]
    with (backup / "install.log").open("w", encoding="utf-8") as log:
        completed = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT)
    if completed.returncode:
        raise RuntimeError(f"Dependency update failed; inspect {backup / 'install.log'}. Previous commit: {previous}")
    subprocess.run([str(PYTHON), "-m", "pip", "check"], check=True)
    subprocess.run([str(PYTHON), str(ROOT / "Scripts" / "check_gpu.py")], check=True)
    subprocess.run([str(PYTHON), str(ROOT / "Scripts" / "system_report.py")], check=True)
    print("Update complete. Launch START_COMFYUI.bat and verify your workflows.")
    return 0


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["start", "stop", "update"])
    options = parser.parse_args()
    try:
        sys.exit({"start": start, "stop": stop, "update": update}[options.action]())
    except (OSError, RuntimeError, subprocess.CalledProcessError, psutil.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
