"""Latency and GPU memory telemetry helpers.

Works on ROCm builds of PyTorch (which expose the ``torch.cuda`` namespace);
degrades gracefully when torch or a GPU is unavailable so unit tests can run
anywhere.
"""

from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field


def _torch():
    try:
        import torch

        return torch
    except ImportError:
        return None


def gpu_available() -> bool:
    torch = _torch()
    return bool(torch and torch.cuda.is_available())


def reset_peak_vram() -> None:
    torch = _torch()
    if torch and torch.cuda.is_available():
        torch.cuda.reset_peak_memory_stats()


def peak_vram_mb() -> float | None:
    torch = _torch()
    if torch and torch.cuda.is_available():
        return round(torch.cuda.max_memory_allocated() / (1024**2), 1)
    return None


def synchronize() -> None:
    torch = _torch()
    if torch and torch.cuda.is_available():
        torch.cuda.synchronize()


@dataclass
class PageTimer:
    """Measures wall-clock latency and peak VRAM for a single page."""

    latency_ms: float | None = None
    peak_vram_mb: float | None = None
    _start: float = field(default=0.0, repr=False)

    def __enter__(self) -> PageTimer:
        reset_peak_vram()
        self._start = time.perf_counter()
        return self

    def __exit__(self, *exc_info) -> None:
        synchronize()
        self.latency_ms = round((time.perf_counter() - self._start) * 1000, 1)
        self.peak_vram_mb = peak_vram_mb()


@contextmanager
def timed(label: str, sink: dict):
    """Record elapsed seconds for a labelled phase into ``sink``."""
    start = time.perf_counter()
    try:
        yield
    finally:
        sink[label] = round(time.perf_counter() - start, 3)
