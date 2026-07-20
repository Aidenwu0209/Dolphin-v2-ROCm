"""Backend interface contract.

All backends implement ``load() / parse_page() / close()`` and return
:class:`~dolphin_v2_rocm.contracts.PageResult` records. Backends must never
silently fall back to CPU: if the configured device is unavailable they raise
unless ``allow_cpu_fallback`` was explicitly enabled.
"""

from __future__ import annotations

import abc
from pathlib import Path

from ..config import RunConfig
from ..contracts import PageResult


class BackendNotAvailableError(RuntimeError):
    """Raised when a backend cannot run in the current environment."""


class Backend(abc.ABC):
    name: str = "base"

    def __init__(self, config: RunConfig):
        self.config = config
        self.loaded = False
        self.load_time_seconds: float | None = None

    @abc.abstractmethod
    def load(self) -> None:
        """Load model weights and processors. Must set ``self.loaded = True``."""

    @abc.abstractmethod
    def parse_page(self, image_path: str | Path, output_dir: str | Path) -> PageResult:
        """Parse a single page image and persist markdown + raw outputs."""

    @abc.abstractmethod
    def close(self) -> None:
        """Release model resources."""

    def __enter__(self):
        self.load()
        return self

    def __exit__(self, *exc_info):
        self.close()
