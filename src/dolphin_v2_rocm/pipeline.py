"""Resumable page-processing pipeline.

Responsibilities:
- deterministic page ordering and output naming
- checkpointing after every page (crash-safe resume)
- skipping already-completed pages on resume
- per-page retry with explicit failure records
- run statistics that always reconcile with per-page records

The pipeline never deletes previous outputs: re-running against the same
output directory resumes rather than overwrites, unless the caller passes a
fresh directory.
"""

from __future__ import annotations

import logging
import time
import traceback
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .backends import create_backend
from .config import RunConfig
from .contracts import PageResult, RunStats, read_json, write_json

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def _utc() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def discover_pages(input_dir: str | Path, limit: int | None = None) -> list[Path]:
    """Deterministically ordered list of page images."""
    input_dir = Path(input_dir)
    pages = sorted(
        (p for p in input_dir.iterdir() if p.suffix.lower() in IMAGE_EXTENSIONS),
        key=lambda p: p.name,
    )
    if limit is not None:
        pages = pages[:limit]
    return pages


class CheckpointStore:
    """Page-level checkpoint ledger stored as one JSON file."""

    def __init__(self, output_dir: str | Path):
        self.path = Path(output_dir) / "checkpoints" / "pages.json"
        self._records: dict[str, dict[str, Any]] = {}
        if self.path.exists():
            self._records = {rec["page_id"]: rec for rec in read_json(self.path)}

    @property
    def records(self) -> list[dict[str, Any]]:
        return list(self._records.values())

    def completed_page_ids(self) -> set[str]:
        return {pid for pid, rec in self._records.items() if rec["status"] == "success"}

    def record(self, result: PageResult) -> None:
        self._records[result.page_id] = result.to_dict()
        write_json(self.path, self.records)

    def get(self, page_id: str) -> dict[str, Any] | None:
        return self._records.get(page_id)


def run_pipeline(
    *,
    input_dir: str | Path,
    output_dir: str | Path,
    config: RunConfig,
    backend_name: str | None = None,
    resume: bool = True,
    platform_name: str = "linux-rocm",
) -> dict[str, Any]:
    """Process every page image in ``input_dir``; return the run summary dict."""
    input_dir = Path(input_dir)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    backend_name = backend_name or config.get("backend", "transformers")

    pages = discover_pages(input_dir, limit=config.get("limit_pages"))
    if not pages:
        raise FileNotFoundError(f"No page images found in {input_dir}")

    checkpoints = CheckpointStore(output_dir)
    completed = checkpoints.completed_page_ids() if resume else set()
    max_retries = int(config.get("max_retries_per_page", 1))

    stats = RunStats(
        total=len(pages),
        backend=backend_name,
        platform=platform_name,
        model_revision=config.get("model_revision"),
        dataset_revision=config.get("dataset_revision"),
        output_dir=str(output_dir),
        started_at=_utc(),
    )
    run_start = time.perf_counter()

    backend = create_backend(backend_name, config)
    backend.load()
    try:
        for index, page_path in enumerate(pages, start=1):
            page_id = page_path.stem
            if page_id in completed:
                logger.info("[%d/%d] skip completed page %s", index, len(pages), page_id)
                continue

            result = _parse_with_retries(backend, page_path, output_dir, max_retries)
            checkpoints.record(result)
            logger.info(
                "[%d/%d] %s status=%s latency=%sms",
                index,
                len(pages),
                page_id,
                result.status,
                result.latency_ms,
            )
    finally:
        backend.close()

    # Reconcile stats from the checkpoint ledger (single source of truth).
    page_records = [rec for rec in checkpoints.records if rec["page_id"] in {p.stem for p in pages}]
    stats.succeeded = sum(1 for r in page_records if r["status"] == "success")
    stats.failed = sum(1 for r in page_records if r["status"] in ("failed", "timeout"))
    stats.skipped = sum(1 for r in page_records if r["status"] == "skipped")
    stats.fallback = sum(1 for r in page_records if r.get("fallback"))
    stats.finished_at = _utc()
    stats.duration_seconds = round(time.perf_counter() - run_start, 1)

    failures = [r for r in page_records if r["status"] != "success"]
    write_json(output_dir / "failures.json", failures)
    summary: dict[str, Any] = {
        **stats.to_dict(),
        "config_digest": config.digest,
        "model_load_seconds": backend.load_time_seconds,
        "pages_missing_records": sorted({p.stem for p in pages} - {r["page_id"] for r in page_records}),
    }
    write_json(output_dir / "_run_stats.json", summary)

    problems = stats.check_consistency(page_records)
    if problems:
        raise RuntimeError(f"Run statistics inconsistent with page records: {problems}")
    if summary["pages_missing_records"]:
        raise RuntimeError(f"Pages without any record: {summary['pages_missing_records']}")
    return summary


def _parse_with_retries(backend, page_path: Path, output_dir: Path, max_retries: int) -> PageResult:
    attempts = 0
    last_error = None
    while attempts <= max_retries:
        attempts += 1
        try:
            result = backend.parse_page(page_path, output_dir)
            result.attempts = attempts
            return result
        except KeyboardInterrupt:
            raise
        except Exception as exc:  # noqa: BLE001 - failure is captured in the ledger
            last_error = f"{type(exc).__name__}: {exc}"
            logger.warning("Page %s attempt %d failed: %s", page_path.stem, attempts, last_error)
            logger.debug("%s", traceback.format_exc())
    return PageResult(
        page_id=page_path.stem,
        source_path=str(page_path),
        status="failed",
        backend=backend.name,
        error=last_error,
        attempts=attempts,
        model_revision=backend.config.get("model_revision"),
        config_digest=backend.config.digest,
    )
