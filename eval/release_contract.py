"""Validate a published OmniDocBench result directory against the release contract.

Checks:
- required JSON artifacts exist and parse
- provenance fields are present
- page counts reconcile (total == succeeded + failed + skipped)
- fallback == 0 for official runs
- failures.json length matches failed count
- no placeholder / TODO values in metric_result.json
- schemas validate when available
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REQUIRED_FILES = (
    "metric_result.json",
    "run_summary.json",
    "_run_stats.json",
    "failures.json",
    "provenance.json",
    "runtime_attestation.json",
    "model_card.json",
    "performance.json",
)

PLACEHOLDER_MARKERS = ("TODO", "TBD", "PLACEHOLDER", "FIXME", "xxx")


def _load(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_placeholder(obj: Any) -> list[str]:
    hits: list[str] = []

    def walk(node: Any, prefix: str = "") -> None:
        if isinstance(node, dict):
            for key, value in node.items():
                walk(value, f"{prefix}.{key}" if prefix else key)
        elif isinstance(node, list):
            for index, value in enumerate(node):
                walk(value, f"{prefix}[{index}]")
        elif isinstance(node, str):
            upper = node.upper()
            for marker in PLACEHOLDER_MARKERS:
                if marker in upper:
                    hits.append(f"{prefix}={node!r}")

    walk(obj)
    return hits


def validate_release_dir(result_dir: str | Path, *, require_metrics: bool = True) -> list[str]:
    """Return a list of human-readable problems (empty == pass)."""
    result_dir = Path(result_dir)
    problems: list[str] = []

    required = list(REQUIRED_FILES)
    if not require_metrics:
        required = [name for name in required if name != "metric_result.json"]

    for name in required:
        if not (result_dir / name).exists():
            problems.append(f"missing required file: {name}")

    if problems:
        return problems

    summary = _load(result_dir / "run_summary.json")
    stats = _load(result_dir / "_run_stats.json")
    failures = _load(result_dir / "failures.json")
    provenance = _load(result_dir / "provenance.json")

    for key in (
        "total",
        "succeeded",
        "failed",
        "skipped",
        "fallback",
        "backend",
        "platform",
        "model_revision",
        "dataset_revision",
        "output_dir",
    ):
        if key not in summary:
            problems.append(f"run_summary missing key: {key}")

    total = int(summary.get("total", -1))
    succeeded = int(summary.get("succeeded", -1))
    failed = int(summary.get("failed", -1))
    skipped = int(summary.get("skipped", -1))
    fallback = int(summary.get("fallback", -1))

    if total != succeeded + failed + skipped:
        problems.append(
            f"page count mismatch: total={total} != succeeded+failed+skipped={succeeded + failed + skipped}"
        )
    if fallback != 0:
        problems.append(f"official run requires fallback=0, got {fallback}")

    output_completeness = summary.get("output_completeness")
    if isinstance(output_completeness, dict) and output_completeness.get("complete") is False:
        details: list[str] = []
        for key, label in (
            ("missing", "missing markdown"),
            ("empty", "empty markdown"),
        ):
            page_ids = output_completeness.get(key)
            if isinstance(page_ids, list) and page_ids:
                preview = ", ".join(str(page_id) for page_id in page_ids[:5])
                if len(page_ids) > 5:
                    preview += f", ... (+{len(page_ids) - 5} more)"
                details.append(f"{label}: {preview}")
        suffix = f" ({'; '.join(details)})" if details else ""
        problems.append(f"output_completeness.complete=false{suffix}")

    if not isinstance(failures, list):
        problems.append("failures.json must be a list")
    elif len(failures) != failed:
        problems.append(f"failures.json length {len(failures)} != failed count {failed}")

    if "generated_at" not in provenance:
        problems.append("provenance missing field: generated_at")
    if not provenance.get("model", {}).get("revision") and not provenance.get("model_revision"):
        problems.append("provenance missing model revision")
    if not provenance.get("dataset", {}).get("revision") and not provenance.get("dataset_revision"):
        problems.append("provenance missing dataset revision")
    if not provenance.get("code", {}).get("commit") and not provenance.get("repo_commit"):
        problems.append("provenance missing code commit")

    if stats.get("pages_missing_records"):
        problems.append(f"pages_missing_records non-empty: {stats['pages_missing_records']}")

    if require_metrics:
        metrics = _load(result_dir / "metric_result.json")
        hits = _contains_placeholder(metrics)
        if hits:
            problems.append(f"metric_result contains placeholders: {hits[:5]}")
        if not metrics:
            problems.append("metric_result.json is empty")

    schema_dir = Path(__file__).resolve().parent / "schemas"
    try:
        import jsonschema
    except ImportError:
        return problems

    mapping = {
        "run_summary.json": "run_summary.schema.json",
        "provenance.json": "provenance.schema.json",
        "performance.json": "performance.schema.json",
    }
    for artifact, schema_name in mapping.items():
        schema_path = schema_dir / schema_name
        if not schema_path.exists() or not (result_dir / artifact).exists():
            continue
        try:
            jsonschema.validate(_load(result_dir / artifact), _load(schema_path))
        except Exception as exc:  # noqa: BLE001
            problems.append(f"schema validation failed for {artifact}: {exc}")

    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate OmniDocBench release artifacts")
    parser.add_argument("result_dir", help="directory under results/omnidocbench/...")
    parser.add_argument(
        "--allow-missing-metrics",
        action="store_true",
        help="skip metric_result.json requirement (inference-only directories)",
    )
    args = parser.parse_args(argv)
    problems = validate_release_dir(args.result_dir, require_metrics=not args.allow_missing_metrics)
    if problems:
        print("RELEASE CONTRACT FAIL", file=sys.stderr)
        for problem in problems:
            print(f" - {problem}", file=sys.stderr)
        return 1
    print("RELEASE CONTRACT PASS")
    return 0


if __name__ == "__main__":
    sys.exit(main())
