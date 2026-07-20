"""Contract tests for eval.adapter.run_adapter."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(REPO_ROOT / "src"))

from eval.adapter import run_adapter, verify_output_completeness  # noqa: E402

from dolphin_v2_rocm.config import load_config  # noqa: E402


@pytest.fixture()
def img_dir(tmp_path: Path) -> Path:
    d = tmp_path / "imgs"
    d.mkdir()
    for name in ("doc_a", "doc_b"):
        Image.new("RGB", (48, 48), "white").save(d / f"{name}.png")
    return d


def test_run_adapter_summary_keys(img_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    summary = run_adapter(
        img_dir,
        out,
        platform="linux-rocm",
        config=load_config(overrides={"backend": "mock", "model_revision": "testrev"}),
    )
    for key in (
        "total",
        "succeeded",
        "failed",
        "skipped",
        "fallback",
        "started_at",
        "finished_at",
        "duration_seconds",
        "backend",
        "platform",
        "model_revision",
        "dataset_revision",
        "output_dir",
    ):
        assert key in summary
    assert summary["total"] == 2
    assert summary["succeeded"] == 2
    assert summary["platform"] == "linux-rocm"
    assert summary["backend"] == "mock"


def test_output_naming_matches_image_stem(img_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_adapter(img_dir, out, platform="linux-rocm", config=load_config(overrides={"backend": "mock"}))
    assert (out / "markdown" / "doc_a.md").exists()
    assert (out / "markdown" / "doc_b.md").exists()


def test_completeness_detects_missing(img_dir: Path, tmp_path: Path):
    out = tmp_path / "out"
    run_adapter(img_dir, out, platform="linux-rocm", config=load_config(overrides={"backend": "mock"}))
    (out / "markdown" / "doc_a.md").unlink()
    report = verify_output_completeness(img_dir, out)
    assert report["complete"] is False
    assert "doc_a" in report["missing"]
