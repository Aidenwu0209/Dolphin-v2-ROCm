"""Environment doctor: verify the ROCm inference environment end to end.

Produces a machine-readable report (``runtime_attestation.json``) plus a
human-readable Markdown summary. Each check yields PASS/WARN/FAIL and the
overall status is the worst individual status.

Design notes:
- PyTorch ROCm builds expose the ``torch.cuda`` namespace; ``cuda.is_available()``
  returning True on this platform means HIP, not NVIDIA CUDA. The report
  records ``torch.version.hip`` to make this explicit.
- ``HSA_OVERRIDE_GFX_VERSION`` is reported and flagged: it must not be used as
  a default compatibility mechanism on natively supported architectures.
"""

from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .provenance import package_versions, utc_now

PASS, WARN, FAIL = "PASS", "WARN", "FAIL"
_ORDER = {PASS: 0, WARN: 1, FAIL: 2}

KNOWN_GOOD_ARCHES = {"gfx1100", "gfx1101", "gfx1102", "gfx90a", "gfx942", "gfx950"}
RISKY_ENV_VARS = (
    "HSA_OVERRIDE_GFX_VERSION",
    "HIP_VISIBLE_DEVICES",
    "ROCR_VISIBLE_DEVICES",
    "CUDA_VISIBLE_DEVICES",
    "PYTORCH_TUNABLEOP_ENABLED",
    "HSA_ENABLE_SDMA",
    "TORCH_BLAS_PREFER_HIPBLASLT",
)


@dataclass
class Check:
    name: str
    status: str
    detail: str
    data: dict[str, Any] = field(default_factory=dict)


def _run(cmd: list[str], timeout: int = 30) -> tuple[int, str]:
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return proc.returncode, (proc.stdout + proc.stderr).strip()
    except FileNotFoundError:
        return 127, f"{cmd[0]}: not found"
    except subprocess.TimeoutExpired:
        return 124, f"{cmd[0]}: timed out"


def check_os() -> Check:
    info = {
        "system": platform.system(),
        "kernel": platform.release(),
        "machine": platform.machine(),
    }
    os_release = Path("/etc/os-release")
    if os_release.exists():
        for line in os_release.read_text().splitlines():
            if line.startswith("PRETTY_NAME="):
                info["distribution"] = line.split("=", 1)[1].strip('"')
    status = PASS if info["system"] == "Linux" else WARN
    return Check("os", status, info.get("distribution", info["system"]), info)


def check_cpu_memory() -> Check:
    info: dict[str, Any] = {"cpu_count": os.cpu_count()}
    meminfo = Path("/proc/meminfo")
    if meminfo.exists():
        for line in meminfo.read_text().splitlines():
            if line.startswith("MemTotal:"):
                info["mem_total_gb"] = round(int(line.split()[1]) / (1024**2), 1)
            elif line.startswith("MemAvailable:"):
                info["mem_available_gb"] = round(int(line.split()[1]) / (1024**2), 1)
    model_name = None
    cpuinfo = Path("/proc/cpuinfo")
    if cpuinfo.exists():
        for line in cpuinfo.read_text().splitlines():
            if line.startswith("model name"):
                model_name = line.split(":", 1)[1].strip()
                break
    if model_name:
        info["cpu_model"] = model_name
    return Check("cpu_memory", PASS, f"{info.get('cpu_model', 'unknown CPU')} x{info['cpu_count']}", info)


def check_disk(path: str = ".") -> Check:
    usage = shutil.disk_usage(path)
    free_gb = round(usage.free / (1024**3), 1)
    info = {
        "path": str(Path(path).resolve()),
        "free_gb": free_gb,
        "total_gb": round(usage.total / (1024**3), 1),
    }
    if free_gb < 20:
        return Check("disk", FAIL, f"only {free_gb} GB free", info)
    if free_gb < 100:
        return Check("disk", WARN, f"{free_gb} GB free (model + dataset need ~30 GB)", info)
    return Check("disk", PASS, f"{free_gb} GB free", info)


def check_rocm() -> Check:
    info: dict[str, Any] = {}
    version_file = Path("/opt/rocm/.info/version")
    if version_file.exists():
        info["rocm_version"] = version_file.read_text().strip()
    code, out = _run(["rocminfo"])
    if code != 0:
        return Check("rocm", FAIL, f"rocminfo failed: {out[:200]}", info)
    gpus = []
    marketing = []
    for line in out.splitlines():
        stripped = line.strip()
        if stripped.startswith("Name:") and "gfx" in stripped:
            gpus.append(stripped.split(":", 1)[1].strip())
        elif stripped.startswith("Marketing Name:"):
            marketing.append(stripped.split(":", 1)[1].strip())
    arches = sorted({g for g in gpus if g.startswith("gfx") and "generic" not in g})
    info["gpu_arches"] = arches
    info["marketing_names"] = [m for m in marketing if "Radeon" in m or "Instinct" in m]
    if not arches:
        return Check("rocm", FAIL, "no AMD GPU agents found in rocminfo", info)
    unknown = [a for a in arches if a not in KNOWN_GOOD_ARCHES]
    status = WARN if unknown else PASS
    detail = (
        f"ROCm {info.get('rocm_version', '?')}, GPU {info['marketing_names'] or arches} ({', '.join(arches)})"
    )
    return Check("rocm", status, detail, info)


def check_gpu_driver() -> Check:
    code, out = _run(["rocm-smi", "--showdriverversion"])
    info: dict[str, Any] = {}
    if code == 0:
        for line in out.splitlines():
            if "Driver version" in line:
                info["driver_version"] = line.split(":", 1)[1].strip()
    if not info.get("driver_version"):
        return Check("gpu_driver", WARN, "could not read driver version via rocm-smi", info)
    return Check("gpu_driver", PASS, f"amdgpu driver {info['driver_version']}", info)


def check_torch() -> Check:
    try:
        import torch
    except ImportError:
        return Check("torch", FAIL, "PyTorch is not installed in this environment", {})
    info: dict[str, Any] = {
        "torch_version": torch.__version__,
        "hip_version": getattr(torch.version, "hip", None),
        "cuda_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
    }
    if not info["hip_version"]:
        return Check("torch", FAIL, f"torch {torch.__version__} is not a ROCm/HIP build", info)
    if not info["cuda_available"]:
        return Check("torch", FAIL, "torch.cuda.is_available() is False (GPU not visible)", info)
    props = torch.cuda.get_device_properties(0)
    info["gpu_name"] = torch.cuda.get_device_name(0)
    info["gpu_arch"] = getattr(props, "gcnArchName", None)
    info["vram_gb"] = round(props.total_memory / (1024**3), 1)
    return Check(
        "torch",
        PASS,
        f"torch {torch.__version__} (HIP {info['hip_version']}) sees {info['gpu_name']} [{info['gpu_arch']}]",
        info,
    )


def check_bf16_matmul() -> Check:
    try:
        import torch
    except ImportError:
        return Check("bf16_gpu_compute", FAIL, "PyTorch is not installed", {})
    if not torch.cuda.is_available():
        return Check("bf16_gpu_compute", FAIL, "no GPU visible to torch", {})
    try:
        x = torch.randn((2048, 2048), device="cuda", dtype=torch.bfloat16)
        y = x @ x
        torch.cuda.synchronize()
        mean = float(y.float().mean())
        info = {"shape": list(y.shape), "dtype": str(y.dtype), "mean": mean}
        if mean != mean:  # NaN guard
            return Check("bf16_gpu_compute", FAIL, "BF16 matmul produced NaN", info)
        return Check("bf16_gpu_compute", PASS, f"BF16 2048x2048 matmul OK (mean={mean:.4f})", info)
    except Exception as exc:  # pragma: no cover - depends on GPU runtime
        return Check("bf16_gpu_compute", FAIL, f"BF16 matmul raised: {exc}", {})


def check_packages() -> Check:
    versions = package_versions(["transformers", "accelerate", "qwen-vl-utils", "vllm", "numpy", "pillow"])
    missing = [name for name in ("transformers", "accelerate") if versions.get(name) is None]
    status = FAIL if missing else PASS
    detail = ", ".join(f"{k}={v}" for k, v in versions.items() if v) or "no inference packages found"
    if missing:
        detail = f"missing required packages: {missing}"
    return Check("packages", status, detail, {"versions": versions})


def check_model_cache(model_dir: str | None) -> Check:
    if not model_dir:
        return Check("model_cache", WARN, "no model directory configured", {})
    path = Path(model_dir)
    if not path.exists():
        return Check(
            "model_cache", WARN, f"model directory {model_dir} does not exist yet", {"path": model_dir}
        )
    weights = list(path.glob("*.safetensors"))
    size_gb = round(sum(w.stat().st_size for w in weights) / (1024**3), 2)
    info = {"path": model_dir, "weight_files": len(weights), "weights_size_gb": size_gb}
    if not weights:
        return Check("model_cache", WARN, f"{model_dir} exists but contains no safetensors weights", info)
    return Check("model_cache", PASS, f"{len(weights)} weight files, {size_gb} GB", info)


def check_env_vars() -> Check:
    present = {name: os.environ[name] for name in RISKY_ENV_VARS if name in os.environ}
    info = {"relevant_env": present}
    if "HSA_OVERRIDE_GFX_VERSION" in present:
        return Check(
            "env_vars",
            WARN,
            f"HSA_OVERRIDE_GFX_VERSION={present['HSA_OVERRIDE_GFX_VERSION']} is set; "
            "this project requires native gfx support, not override-based compatibility",
            info,
        )
    return Check("env_vars", PASS, "no risky ROCm environment overrides set", info)


def run_doctor(model_dir: str | None = None) -> dict[str, Any]:
    checks = [
        check_os(),
        check_cpu_memory(),
        check_disk(),
        check_rocm(),
        check_gpu_driver(),
        check_torch(),
        check_bf16_matmul(),
        check_packages(),
        check_model_cache(model_dir),
        check_env_vars(),
    ]
    overall = max((c.status for c in checks), key=lambda s: _ORDER[s])
    known_risks = [
        "PyTorch on ROCm reports devices through the torch.cuda namespace; this is HIP, not NVIDIA CUDA.",
        "gfx1100 (RDNA3) has no official flash-attention kernel coverage in some libraries; SDPA math paths are used instead.",
    ]
    return {
        "generated_at": utc_now(),
        "overall": overall,
        "checks": [asdict(c) for c in checks],
        "known_risks": known_risks,
    }


def render_markdown(report: dict[str, Any]) -> str:
    icon = {PASS: "PASS", WARN: "WARN", FAIL: "FAIL"}
    lines = [
        "# Environment Doctor Report",
        "",
        f"- Generated: {report['generated_at']}",
        f"- Overall: **{report['overall']}**",
        "",
        "| Check | Status | Detail |",
        "| --- | --- | --- |",
    ]
    for check in report["checks"]:
        detail = check["detail"].replace("|", "\\|")
        lines.append(f"| {check['name']} | {icon[check['status']]} | {detail} |")
    lines += ["", "## Known risks", ""]
    lines += [f"- {risk}" for risk in report["known_risks"]]
    lines.append("")
    return "\n".join(lines)
