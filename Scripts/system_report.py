import ctypes
from datetime import datetime, timezone
import importlib.metadata
import json
from pathlib import Path
import platform
import subprocess
import sys
import winreg

import psutil
import torch

ROOT = Path(__file__).resolve().parents[1]


def registry(path, names):
    with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
        return {name: winreg.QueryValueEx(key, name)[0] for name in names}


def command(*args):
    result = subprocess.run(args, capture_output=True, text=True, encoding="utf-8", errors="replace")
    return {"exit_code": result.returncode, "stdout": result.stdout.strip(), "stderr": result.stderr.strip()}


windows = registry(r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", ["ProductName", "DisplayVersion", "CurrentBuild", "UBR"])
windows["detected_name"] = "Windows 11" if int(windows["CurrentBuild"]) >= 22000 else windows["ProductName"]
report = {
    "recorded_utc": datetime.now(timezone.utc).isoformat(),
    "workspace": str(ROOT), "windows": windows,
    "cpu": registry(r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", ["ProcessorNameString"]),
    "logical_cpus": psutil.cpu_count(), "physical_cpus": psutil.cpu_count(logical=False),
    "ram_total_bytes": psutil.virtual_memory().total,
    "disk": psutil.disk_usage(str(ROOT))._asdict(),
    "python": sys.version, "python_executable": sys.executable, "python_base": sys.base_prefix,
    "git": command("git", "--version"),
    "nvidia": command("nvidia-smi", "--query-gpu=name,driver_version,memory.total,memory.free", "--format=csv"),
    "nvidia_smi": command("nvidia-smi"),
    "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
    "cuda_available": torch.cuda.is_available(),
    "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
    "comfyui_commit": command("git", "-C", str(ROOT / "ComfyUI"), "rev-parse", "HEAD"),
    "comfyui_release": command("git", "-C", str(ROOT / "ComfyUI"), "describe", "--tags", "--always"),
    "manager": importlib.metadata.version("comfyui-manager"),
    "frontend": importlib.metadata.version("comfyui-frontend-package"),
    "custom_nodes": sorted(p.name for p in (ROOT / "ComfyUI" / "custom_nodes").iterdir() if p.is_dir() and p.name != "__pycache__"),
    "system_probe_notes": [
        "CIM/WMI queries denied in this execution environment; Windows/CPU read from registry, RAM read with psutil/Win32 APIs.",
        "Registry ProductName remains Windows 10 Pro; build 26200 identifies Windows 11 25H2.",
        "CUDA UMD 13.4 reported by nvidia-smi is driver capability, not installed PyTorch runtime (13.0).",
        "Python managed locally by uv; optional user executable link and registry registration were denied; no global Python replacement occurred.",
    ],
}
(ROOT / "Logs" / "system-report.json").write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
(ROOT / "Logs" / "installed-packages.txt").write_text(command(sys.executable, "-m", "pip", "freeze")["stdout"] + "\n", encoding="utf-8")
print(json.dumps({key: report[key] for key in ("workspace", "gpu", "ram_total_bytes", "python", "torch", "cuda_runtime", "comfyui_release", "manager", "custom_nodes")}, indent=2))
