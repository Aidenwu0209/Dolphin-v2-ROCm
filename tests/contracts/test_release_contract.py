"""Tests for eval.release_contract."""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))

from eval.release_contract import validate_release_dir  # noqa: E402

_NOT_PROVIDED = object()


def _write(path: Path, payload) -> None:
    path.write_text(json.dumps(payload), encoding="utf-8")


def _write_minimal_release(tmp_path: Path, *, output_completeness=_NOT_PROVIDED) -> None:
    summary = {
        "total": 2,
        "succeeded": 2,
        "failed": 0,
        "skipped": 0,
        "fallback": 0,
        "started_at": "2026-07-20T00:00:00Z",
        "finished_at": "2026-07-20T00:01:00Z",
        "duration_seconds": 60,
        "backend": "transformers",
        "platform": "linux-rocm",
        "model_revision": "abc",
        "dataset_revision": "def",
        "output_dir": str(tmp_path),
        "config_digest": "sha256:" + ("a" * 64),
    }
    if output_completeness is not _NOT_PROVIDED:
        summary["output_completeness"] = output_completeness
    _write(tmp_path / "run_summary.json", summary)
    _write(
        tmp_path / "_run_stats.json",
        {"pages_missing_records": [], "total": 2, "succeeded": 2, "failed": 0},
    )
    _write(tmp_path / "failures.json", [])
    _write(
        tmp_path / "provenance.json",
        {
            "generated_at": "2026-07-20T00:01:00Z",
            "code": {
                "repository": "https://github.com/Aidenwu0209/Dolphin-v2-ROCm",
                "commit": "a" * 40,
            },
            "model": {"repo": "ByteDance/Dolphin-v2", "revision": "c" * 40},
            "dataset": {"name": "opendatalab/OmniDocBench", "revision": "def"},
            "config_digest": "sha256:" + ("a" * 64),
            "environment": {"python": "3.12.3", "platform": "Linux"},
        },
    )
    _write(tmp_path / "runtime_attestation.json", {"overall": "PASS"})
    _write(tmp_path / "model_card.json", {"repo": "ByteDance/Dolphin-v2"})
    _write(
        tmp_path / "performance.json",
        {
            "label": "baseline",
            "generated_at": "2026-07-20T00:01:00Z",
            "backend": "transformers",
            "config_digest": "sha256:" + ("a" * 64),
            "input_pages": ["doc_a.png", "doc_b.png"],
            "repeats": 3,
            "model_load_seconds": 4.0,
            "first_page_latency_ms": 1000.0,
            "median_across_repeats": {
                "p50_ms": 900.0,
                "p95_ms": 1200.0,
                "mean_ms": 950.0,
                "pages_per_second": 1.1,
                "wall_seconds": 2.0,
            },
            "per_repeat": [
                {"p50_ms": 900.0, "p95_ms": 1200.0, "pages_per_second": 1.1, "failures": 0},
                {"p50_ms": 910.0, "p95_ms": 1210.0, "pages_per_second": 1.0, "failures": 0},
                {"p50_ms": 890.0, "p95_ms": 1190.0, "pages_per_second": 1.2, "failures": 0},
            ],
        },
    )
    _write(tmp_path / "metric_result.json", {"text_edit": 0.9})


def test_release_contract_passes_legacy_summary_without_completeness(tmp_path: Path):
    _write_minimal_release(tmp_path)

    assert validate_release_dir(tmp_path) == []


def test_release_contract_passes_complete_markdown(tmp_path: Path):
    _write_minimal_release(
        tmp_path,
        output_completeness={"complete": True, "missing": [], "empty": []},
    )

    assert validate_release_dir(tmp_path) == []


def test_release_contract_rejects_missing_markdown(tmp_path: Path):
    _write_minimal_release(
        tmp_path,
        output_completeness={"complete": False, "missing": ["doc_b"], "empty": []},
    )

    problems = validate_release_dir(tmp_path)

    assert "output_completeness.complete=false (missing markdown: doc_b)" in problems


def test_release_contract_catches_fallback(tmp_path: Path):
    problems = validate_release_dir(tmp_path)
    assert any("missing required file" in p for p in problems)
