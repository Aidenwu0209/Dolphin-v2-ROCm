"""Contract tests for the resumable pipeline, using the mock backend only."""

import json
from pathlib import Path

import pytest
from PIL import Image

from dolphin_v2_rocm.config import load_config
from dolphin_v2_rocm.contracts import read_json
from dolphin_v2_rocm.pipeline import discover_pages, run_pipeline


@pytest.fixture()
def input_dir(tmp_path: Path) -> Path:
    d = tmp_path / "inputs"
    d.mkdir()
    for name in ("page_b", "page_a", "page_c"):
        Image.new("RGB", (32, 32), "white").save(d / f"{name}.png")
    return d


def _cfg(**overrides):
    overrides.setdefault("backend", "mock")
    return load_config(overrides=overrides)


def test_deterministic_page_order(input_dir: Path):
    pages = discover_pages(input_dir)
    assert [p.stem for p in pages] == ["page_a", "page_b", "page_c"]


def test_run_produces_complete_artifacts(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    summary = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    assert summary["total"] == 3
    assert summary["succeeded"] == 3
    assert summary["failed"] == 0
    assert summary["fallback"] == 0
    assert summary["pages_missing_records"] == []
    assert (out / "_run_stats.json").exists()
    assert (out / "failures.json").exists()
    assert read_json(out / "failures.json") == []
    for name in ("page_a", "page_b", "page_c"):
        md = out / "markdown" / f"{name}.md"
        assert md.exists()
        assert md.read_text().strip()
        assert (out / "raw" / f"{name}.json").exists()


def test_failures_are_explicitly_recorded(input_dir: Path, tmp_path: Path):
    Image.new("RGB", (32, 32)).save(input_dir / "page_FAIL.png")
    out = tmp_path / "out"
    summary = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg(max_retries_per_page=1))
    assert summary["total"] == 4
    assert summary["succeeded"] == 3
    assert summary["failed"] == 1
    failures = read_json(out / "failures.json")
    assert len(failures) == 1
    assert failures[0]["page_id"] == "page_FAIL"
    assert failures[0]["error"]
    assert failures[0]["attempts"] == 2  # first try + one retry


def test_empty_output_is_a_failure_not_success(input_dir: Path, tmp_path: Path):
    Image.new("RGB", (32, 32)).save(input_dir / "page_EMPTY.png")
    out = tmp_path / "out"
    summary = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    assert summary["failed"] == 1
    failures = read_json(out / "failures.json")
    assert "empty markdown" in failures[0]["error"]


def test_resume_skips_completed_pages(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    marker = out / "markdown" / "page_a.md"
    original_mtime = marker.stat().st_mtime_ns

    summary = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    assert summary["succeeded"] == 3
    # completed page must not be re-processed (file untouched)
    assert marker.stat().st_mtime_ns == original_mtime


def test_resume_retries_only_failed_pages(input_dir: Path, tmp_path: Path):
    fail_page = input_dir / "page_FAIL.png"
    Image.new("RGB", (32, 32)).save(fail_page)
    out = tmp_path / "out"
    summary1 = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    assert summary1["failed"] == 1

    # "fix" the failing page by renaming it away and adding a good one with the same id is
    # not possible; instead verify the failed page is retried on resume (mock fails again)
    summary2 = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    assert summary2["failed"] == 1
    assert summary2["succeeded"] == 3


def test_repeated_runs_are_idempotent(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    s1 = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    s2 = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    for key in ("total", "succeeded", "failed", "skipped", "fallback"):
        assert s1[key] == s2[key]


def test_limit_pages(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    summary = run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg(limit_pages=2))
    assert summary["total"] == 2
    assert summary["succeeded"] == 2


def test_summary_contains_provenance_fields(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    summary = run_pipeline(
        input_dir=input_dir,
        output_dir=out,
        config=_cfg(model_revision="test-rev", dataset_revision="data-rev"),
    )
    assert summary["model_revision"] == "test-rev"
    assert summary["dataset_revision"] == "data-rev"
    assert summary["backend"] == "mock"
    assert summary["config_digest"].startswith("sha256:")
    assert summary["started_at"] and summary["finished_at"]


def test_checkpoint_ledger_is_valid_json(input_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_pipeline(input_dir=input_dir, output_dir=out, config=_cfg())
    ledger = json.loads((out / "checkpoints" / "pages.json").read_text())
    assert {rec["page_id"] for rec in ledger} == {"page_a", "page_b", "page_c"}
    for rec in ledger:
        assert rec["config_digest"].startswith("sha256:")
