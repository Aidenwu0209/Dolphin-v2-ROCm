"""Run configuration loading and digest computation.

A run config is a plain YAML mapping. The digest of the *resolved* config is
recorded in every page result and run summary so that results can always be
traced back to the exact configuration that produced them.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

DEFAULTS: dict[str, Any] = {
    "backend": "transformers",
    "model_path": None,
    "model_revision": None,
    "dtype": "bfloat16",
    "device": "cuda",
    "max_new_tokens": 4096,
    "max_batch_size": 4,
    "attn_implementation": "sdpa",
    "layout_prompt": "Parse the reading order of this document.",
    "prompts": {
        "tab": "Parse the table in the image.",
        "equ": "Read formula in the image.",
        "code": "Read code in the image.",
        "text": "Read text in the image.",
    },
    "resize_max_size": 1600,
    "post_process": False,
    "limit_pages": None,
    "page_timeout_seconds": 600,
    "max_retries_per_page": 1,
    "save_layout_visualization": False,
    "allow_cpu_fallback": False,
    "seed": 42,
}


@dataclass
class RunConfig:
    """Resolved run configuration with provenance digest."""

    values: dict[str, Any] = field(default_factory=dict)
    source_path: str | None = None

    def __getitem__(self, key: str) -> Any:
        return self.values[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.values.get(key, default)

    @property
    def digest(self) -> str:
        canonical = json.dumps(self.values, sort_keys=True, ensure_ascii=False, default=str)
        return "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()

    def to_dict(self) -> dict[str, Any]:
        return dict(self.values)


def _deep_merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    merged = dict(base)
    for key, value in override.items():
        if key in merged and isinstance(merged[key], dict) and isinstance(value, dict):
            merged[key] = _deep_merge(merged[key], value)
        else:
            merged[key] = value
    return merged


def load_config(path: str | Path | None = None, overrides: dict[str, Any] | None = None) -> RunConfig:
    """Load a YAML config file, apply defaults and explicit overrides."""
    values: dict[str, Any] = dict(DEFAULTS)
    source_path = None
    if path is not None:
        source_path = str(path)
        with open(path, encoding="utf-8") as f:
            loaded = yaml.safe_load(f) or {}
        if not isinstance(loaded, dict):
            raise ValueError(f"Config file {path} must contain a YAML mapping, got {type(loaded).__name__}")
        values = _deep_merge(values, loaded)
    if overrides:
        values = _deep_merge(values, {k: v for k, v in overrides.items() if v is not None})
    return RunConfig(values=values, source_path=source_path)
