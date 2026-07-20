"""Provenance capture: pin the exact model, data, code, and environment.

Every official result directory must contain a ``provenance.json`` produced
here, so that any number in a report can be traced back to a model revision,
dataset revision, repository commit, and runtime environment.
"""

from __future__ import annotations

import hashlib
import json
import platform
import subprocess
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def utc_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def file_sha256(path: str | Path, chunk_size: int = 1 << 20) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(chunk_size):
            digest.update(chunk)
    return "sha256:" + digest.hexdigest()


def git_commit(repo_dir: str | Path | None = None) -> str | None:
    try:
        out = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir,
            capture_output=True,
            text=True,
            timeout=10,
            check=True,
        )
        return out.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return None


def package_versions(names: list[str]) -> dict[str, str | None]:
    import importlib.metadata

    versions: dict[str, str | None] = {}
    for name in names:
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return versions


def torch_environment() -> dict[str, Any]:
    info: dict[str, Any] = {"torch": None, "hip": None, "gpu": None, "gpu_arch": None}
    try:
        import torch

        info["torch"] = torch.__version__
        info["hip"] = getattr(torch.version, "hip", None)
        if torch.cuda.is_available():
            info["gpu"] = torch.cuda.get_device_name(0)
            props = torch.cuda.get_device_properties(0)
            info["gpu_arch"] = getattr(props, "gcnArchName", None)
            info["vram_gb"] = round(props.total_memory / (1024**3), 1)
    except ImportError:
        pass
    return info


def model_weight_digests(model_dir: str | Path) -> dict[str, str]:
    """Digest the model config and weight index (fast, stable identity)."""
    model_dir = Path(model_dir)
    digests: dict[str, str] = {}
    for name in (
        "config.json",
        "model.safetensors.index.json",
        "preprocessor_config.json",
        "generation_config.json",
        "tokenizer_config.json",
    ):
        candidate = model_dir / name
        if candidate.exists():
            digests[name] = file_sha256(candidate)
    return digests


def build_provenance(
    *,
    model_path: str | None = None,
    model_repo: str | None = None,
    model_revision: str | None = None,
    dataset_name: str | None = None,
    dataset_revision: str | None = None,
    scorer_repo: str | None = None,
    scorer_commit: str | None = None,
    config: dict[str, Any] | None = None,
    config_digest: str | None = None,
    repo_dir: str | Path | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "generated_at": utc_now(),
        "code": {
            "repository": "https://github.com/Aidenwu0209/Dolphin-v2-ROCm",
            "commit": git_commit(repo_dir),
        },
        "model": {
            "repo": model_repo,
            "revision": model_revision,
            "local_path": model_path,
            "file_digests": model_weight_digests(model_path)
            if model_path and Path(model_path).exists()
            else {},
        },
        "dataset": {
            "name": dataset_name,
            "revision": dataset_revision,
        },
        "scorer": {
            "repo": scorer_repo,
            "commit": scorer_commit,
        },
        "config": config or {},
        "config_digest": config_digest,
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            **torch_environment(),
            "packages": package_versions(
                ["transformers", "accelerate", "qwen-vl-utils", "tokenizers", "numpy", "pillow", "vllm"]
            ),
        },
    }
    if extra:
        payload.update(extra)
    return payload


def save_provenance(path: str | Path, payload: dict[str, Any]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)
