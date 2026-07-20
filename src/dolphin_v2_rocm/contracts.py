"""Result contracts: page-level and run-level result records.

These contracts are the single source of truth for what a "successful page"
means. A page with empty markdown output is *never* a success; it must be
recorded as a failure with an explicit error.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

VALID_STATUSES = ("success", "failed", "skipped", "timeout")


@dataclass
class PageResult:
    """Standardized result of parsing a single page."""

    page_id: str
    source_path: str
    status: str
    backend: str
    markdown_path: str | None = None
    raw_output_path: str | None = None
    error: str | None = None
    latency_ms: float | None = None
    peak_vram_mb: float | None = None
    model_revision: str | None = None
    config_digest: str | None = None
    fallback: bool = False
    attempts: int = 1
    element_count: int | None = None
    extra: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"Invalid status {self.status!r}; expected one of {VALID_STATUSES}")
        if self.status == "success":
            if not self.markdown_path:
                raise ValueError(f"Page {self.page_id}: success requires a markdown_path")
            if self.error:
                raise ValueError(f"Page {self.page_id}: success must not carry an error")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def validate_success_output(page_id: str, markdown_text: str) -> None:
    """Reject empty or whitespace-only markdown as a successful output."""
    if not markdown_text or not markdown_text.strip():
        raise EmptyOutputError(f"Page {page_id}: model produced empty markdown output")


class EmptyOutputError(RuntimeError):
    """Raised when a page produced no usable output."""


@dataclass
class RunStats:
    """Aggregated statistics for an inference/evaluation run."""

    total: int = 0
    succeeded: int = 0
    failed: int = 0
    skipped: int = 0
    fallback: int = 0
    started_at: str | None = None
    finished_at: str | None = None
    duration_seconds: float | None = None
    backend: str | None = None
    platform: str | None = None
    model_revision: str | None = None
    dataset_revision: str | None = None
    output_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def check_consistency(self, page_results: list[dict[str, Any]]) -> list[str]:
        """Return a list of consistency violations (empty list = consistent)."""
        problems: list[str] = []
        by_status: dict[str, int] = {}
        for page in page_results:
            by_status[page["status"]] = by_status.get(page["status"], 0) + 1
        succeeded = by_status.get("success", 0)
        failed = by_status.get("failed", 0) + by_status.get("timeout", 0)
        skipped = by_status.get("skipped", 0)
        if len(page_results) != self.total:
            problems.append(f"total={self.total} but {len(page_results)} page records exist")
        if succeeded != self.succeeded:
            problems.append(f"succeeded={self.succeeded} but {succeeded} success records exist")
        if failed != self.failed:
            problems.append(f"failed={self.failed} but {failed} failed/timeout records exist")
        if skipped != self.skipped:
            problems.append(f"skipped={self.skipped} but {skipped} skipped records exist")
        fallback_count = sum(1 for p in page_results if p.get("fallback"))
        if fallback_count != self.fallback:
            problems.append(f"fallback={self.fallback} but {fallback_count} fallback records exist")
        return problems


def write_json(path: str | Path, payload: Any) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2, default=str)
    tmp.replace(path)


def read_json(path: str | Path) -> Any:
    with open(path, encoding="utf-8") as f:
        return json.load(f)
