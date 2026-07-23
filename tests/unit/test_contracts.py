import pytest

from dolphin_v2_rocm.contracts import (
    EmptyOutputError,
    PageResult,
    RunStats,
    validate_success_output,
)


def _success(page_id="p1", **kwargs):
    defaults = dict(
        page_id=page_id,
        source_path=f"/in/{page_id}.png",
        status="success",
        backend="mock",
        markdown_path=f"/out/{page_id}.md",
    )
    defaults.update(kwargs)
    return PageResult(**defaults)


def test_success_requires_markdown_path():
    with pytest.raises(ValueError, match="requires a markdown_path"):
        PageResult(page_id="p", source_path="s", status="success", backend="mock")


def test_success_must_not_carry_error():
    with pytest.raises(ValueError, match="must not carry an error"):
        _success(error="boom")


def test_invalid_status_rejected():
    with pytest.raises(ValueError, match="Invalid status"):
        PageResult(page_id="p", source_path="s", status="ok", backend="mock")


def test_empty_markdown_rejected():
    with pytest.raises(EmptyOutputError):
        validate_success_output("p1", "   \n  ")
    validate_success_output("p1", "# content")


def test_run_stats_consistency_detects_mismatch():
    stats = RunStats(total=2, succeeded=2, failed=0, skipped=0, fallback=0)
    records = [
        _success("a").to_dict(),
        PageResult(page_id="b", source_path="s", status="failed", backend="mock", error="x").to_dict(),
    ]
    problems = stats.check_consistency(records)
    assert any("succeeded" in p for p in problems)
    assert any("failed" in p for p in problems)

    stats_ok = RunStats(total=2, succeeded=1, failed=1, skipped=0, fallback=0)
    assert stats_ok.check_consistency(records) == []


def test_run_stats_counts_timeout_as_failed():
    stats = RunStats(total=1, succeeded=0, failed=1, skipped=0, fallback=0)
    records = [
        PageResult(page_id="t", source_path="s", status="timeout", backend="mock", error="slow").to_dict()
    ]
    assert stats.check_consistency(records) == []
