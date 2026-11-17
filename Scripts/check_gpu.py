import json
from pathlib import Path
import torch

assert torch.cuda.is_available(), "CUDA unavailable: CPU fallback is not accepted"
x = torch.randn((1024, 1024), device="cuda", dtype=torch.float16)
y = x @ x
torch.cuda.synchronize()
assert bool(y.isfinite().all()), "GPU calculation produced non-finite values"
free, total = torch.cuda.mem_get_info()
result = {
    "torch": torch.__version__, "cuda_runtime": torch.version.cuda,
    "gpu": torch.cuda.get_device_name(0),
    "vram_bytes": torch.cuda.get_device_properties(0).total_memory,
    "free_vram_bytes": free, "cuda_memory_total_bytes": total,
    "compute_capability": torch.cuda.get_device_capability(0),
    "compiled_architectures": torch.cuda.get_arch_list(),
    "tensor_device": str(y.device), "gpu_matmul_passed": True,
}
print(json.dumps(result, indent=2))
(Path(__file__).resolve().parents[1] / "Logs" / "gpu-test.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
