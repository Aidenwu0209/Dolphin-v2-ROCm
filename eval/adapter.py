"""OmniDocBench adapter: run Dolphin-v2 over benchmark images.

Public entrypoint: :func:`run_adapter`. It wraps the resumable pipeline and
returns a machine-readable summary dict that downstream scripts (and the
release contract) validate. Prediction markdown files are named exactly after
the source image stem (``<image>.md``), which is the layout the OmniDocBench
end2end scorer expects.
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dolphin_v2_rocm.config import RunConfig  # noqa: E402
from dolphin_v2_rocm.contracts import read_json  # noqa: E402
from dolphin_v2_rocm.pipeline import discover_pages, run_pipeline  # noqa: E402


def run_adapter(
    img_dir: str | Path,
    out_dir: str | Path,
    *,
    platform: str,
    config: RunConfig,
) -> dict[str, Any]:
    """Run the benchmark adapter over ``img_dir`` and return the summary contract.

    The returned dict includes: total, succeeded, failed, skipped, fallback,
    started_at, finished_at, duration_seconds, backend, platform,
    model_revision, dataset_revision, output_dir.
    """
    summary = run_pipeline(
        input_dir=img_dir,
        output_dir=out_dir,
        config=config,
        platform_name=platform,
    )
    required_keys = (
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
    )
    missing = [key for key in required_keys if key not in summary]
    if missing:
        raise RuntimeError(f"Adapter summary is missing contract keys: {missing}")
    return summary


def verify_output_completeness(img_dir: str | Path, out_dir: str | Path) -> dict[str, Any]:
    """Cross-check that every input page has either a markdown file or an explicit failure."""
    out_dir = Path(out_dir)
    pages = discover_pages(img_dir)
    markdown_dir = out_dir / "markdown"
    failures = {rec["page_id"] for rec in read_json(out_dir / "failures.json")}

    missing: list[str] = []
    empty: list[str] = []
    for page in pages:
        md = markdown_dir / f"{page.stem}.md"
        if md.exists():
            if not md.read_text(encoding="utf-8").strip():
                empty.append(page.stem)
        elif page.stem not in failures:
            missing.append(page.stem)
    return {
        "pages": len(pages),
        "markdown_files": len(list(markdown_dir.glob("*.md"))) if markdown_dir.exists() else 0,
        "explicit_failures": len(failures),
        "missing": missing,
        "empty": empty,
        "complete": not missing and not empty,
    }
