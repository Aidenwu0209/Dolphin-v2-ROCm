"""Inference backends for Dolphin-v2 on ROCm."""

from __future__ import annotations

from .base import Backend


def create_backend(name: str, config) -> Backend:
    if name == "transformers":
        from .transformers_rocm import TransformersRocmBackend

        return TransformersRocmBackend(config)
    if name == "vllm":
        from .vllm_rocm import VllmRocmBackend

        return VllmRocmBackend(config)
    if name == "mock":
        from .mock import MockBackend

        return MockBackend(config)
    raise ValueError(f"Unknown backend: {name!r} (expected transformers, vllm, or mock)")
