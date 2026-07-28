from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "build_weak_page_list.py"


def page(
    image_path: str,
    *,
    data_source: str = "book",
    language: str = "simplified_chinese",
    layout: str = "single_column",
    special_issue: list[str] | None = None,
) -> dict[str, object]:
    return {
        "page_info": {
            "image_path": image_path,
            "page_attribute": {
                "data_source": data_source,
                "language": language,
                "layout": layout,
                "special_issue": special_issue or [],
                "subset": "layout_hard",
            },
        },
        "layout_dets": [],
        "extra": {"relation": []},
    }


def run_builder(
    gt: Path,
    out: Path,
    *,
    profile: str,
    expected_count: int,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gt",
            str(gt),
            "--out",
            str(out),
            "--profile",
            profile,
            "--expected-count",
            str(expected_count),
        ],
        check=False,
        capture_output=True,
        text=True,
    )


def test_severe_union_reads_nested_schema_sorts_and_deduplicates(tmp_path: Path) -> None:
    records = [
        page("z-historical.png", data_source="historical_document"),
        page("a-geometric.png", special_issue=["geometric_deformation"]),
        page("m-handwriting.png", special_issue=["handwriting"]),
        page("f-fuzzy.png", special_issue=["fuzzy_content", "geometric_deformation"]),
        page("a-geometric.png", special_issue=["geometric_deformation"]),
        page("traditional-only.png", language="traditional_chinese"),
    ]
    gt = tmp_path / "OmniDocBench.json"
    gt.write_text(json.dumps({"data": records}), encoding="utf-8")
    out = tmp_path / "severe.txt"

    result = run_builder(gt, out, profile="severe-union", expected_count=4)

    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8").splitlines() == [
        "a-geometric.png",
        "f-fuzzy.png",
        "m-handwriting.png",
        "z-historical.png",
    ]


def test_research_report_dual_profile_uses_exact_gt_attributes(tmp_path: Path) -> None:
    records = [
        page(
            "yanbaopptmerge_b.pdf_2.jpg",
            data_source="research_report",
            layout="1andmore_column",
        ),
        page(
            "eastmoney_a.pdf_0.jpg",
            data_source="research_report",
            layout="1andmore_column",
        ),
        page(
            "eastmoney_single.pdf_1.jpg",
            data_source="research_report",
            layout="single_column",
        ),
        page(
            "other-prefix.pdf_0.jpg",
            data_source="research_report",
            layout="1andmore_column",
        ),
        page(
            "eastmoney_wrong-source.pdf_0.jpg",
            data_source="PPT2PDF",
            layout="1andmore_column",
        ),
    ]
    gt = tmp_path / "OmniDocBench.json"
    gt.write_text(json.dumps(records), encoding="utf-8")
    out = tmp_path / "research.txt"

    result = run_builder(gt, out, profile="research-report-dual", expected_count=2)

    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8").splitlines() == [
        "eastmoney_a.pdf_0.jpg",
        "yanbaopptmerge_b.pdf_2.jpg",
    ]


def test_expected_count_mismatch_fails_before_writing(tmp_path: Path) -> None:
    gt = tmp_path / "OmniDocBench.json"
    gt.write_text(
        json.dumps([page("only-one.png", special_issue=["handwriting"])]),
        encoding="utf-8",
    )
    out = tmp_path / "must-not-exist.txt"

    result = run_builder(gt, out, profile="severe-union", expected_count=2)

    assert result.returncode != 0
    assert "expected 2 pages, got 1" in result.stderr
    assert not out.exists()


def test_default_hints_preserves_legacy_seed_first_record_order(
    tmp_path: Path,
) -> None:
    seed = tmp_path / "eval" / "configs" / "cuda5070ti_weak_pages.txt"
    seed.parent.mkdir(parents=True)
    seed.write_text("legacy-seed.png\n", encoding="utf-8")

    gt = tmp_path / "OmniDocBench.json"
    gt.write_text(
        json.dumps(
            [
                page("newspaper-z.png"),
                page("newspaper-a.png"),
            ]
        ),
        encoding="utf-8",
    )
    out = tmp_path / "weak.txt"

    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--gt",
            str(gt),
            "--out",
            str(out),
            "--max-pages",
            "3",
        ],
        cwd=tmp_path,
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0, result.stderr
    assert out.read_text(encoding="utf-8").splitlines() == [
        "legacy-seed.png",
        "newspaper-z.png",
        "newspaper-a.png",
    ]
