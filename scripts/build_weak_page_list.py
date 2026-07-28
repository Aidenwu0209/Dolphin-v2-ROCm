#!/usr/bin/env python3
"""Build deterministic page lists from OmniDocBench GT attributes.

Requires a local OmniDocBench.json (not committed).

Examples:
  python scripts/build_weak_page_list.py \\
    --gt /path/to/OmniDocBench.json \\
    --profile severe-union \\
    --expected-count 19 \\
    --out eval/configs/cuda5070ti_severe_union_pages.txt

  python scripts/build_weak_page_list.py \\
    --gt /path/to/OmniDocBench.json \\
    --profile research-report-dual \\
    --expected-count 10 \\
    --out eval/configs/cuda5070ti_research_report_dual_pages.txt
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Buckets retained for the legacy substring-hint mode.
DEFAULT_WEAK_HINTS = (
    "newspaper",
    "color_textbook",
    "jiaocaineedrop",
    "eastmoney",
)

PROFILE_HINTS = "hints"
PROFILE_SEVERE_UNION = "severe-union"
PROFILE_RESEARCH_REPORT_DUAL = "research-report-dual"
PROFILES = (
    PROFILE_HINTS,
    PROFILE_SEVERE_UNION,
    PROFILE_RESEARCH_REPORT_DUAL,
)
LEGACY_SEED_LIST = Path("eval/configs/cuda5070ti_weak_pages.txt")

# `traditional_chinese` is an annotation on part of this cluster, not a selector:
# including every traditional-Chinese page expands the pinned v1.6 set from 19 to 28.
SEVERE_SPECIAL_ISSUES = frozenset(
    {
        "handwriting",
        "geometric_deformation",
        "fuzzy_content",
    }
)


def load_records(gt_path: Path) -> list[dict[str, object]]:
    gt = json.loads(gt_path.read_text(encoding="utf-8"))
    if isinstance(gt, dict) and "data" in gt:
        records = gt["data"]
    elif isinstance(gt, list):
        records = gt
    else:
        raise SystemExit(f"Unrecognized GT shape: {type(gt)}")

    if not isinstance(records, list) or not all(isinstance(rec, dict) for rec in records):
        raise SystemExit("GT records must be a list of objects")
    return records


def page_info(rec: dict[str, object]) -> dict[str, object]:
    value = rec.get("page_info")
    return value if isinstance(value, dict) else {}


def image_name(rec: dict[str, object]) -> str:
    page = page_info(rec)
    name = (
        page.get("image_path")
        or rec.get("image_path")
        or rec.get("img_id")
        or rec.get("page_id")
        or rec.get("image")
        or ""
    )
    return Path(str(name)).name if name else ""


def page_attributes(rec: dict[str, object]) -> dict[str, object]:
    attrs = page_info(rec).get("page_attribute")
    if not isinstance(attrs, dict):
        attrs = rec.get("attribute")
    return attrs if isinstance(attrs, dict) else {}


def special_issues(attrs: dict[str, object]) -> set[str]:
    value = attrs.get("special_issue", [])
    if isinstance(value, str):
        return {value}
    if isinstance(value, list):
        return {str(issue) for issue in value}
    return set()


def matches_profile(
    rec: dict[str, object],
    *,
    profile: str,
    hints: list[str],
) -> bool:
    name = image_name(rec)
    if not name:
        return False

    attrs = page_attributes(rec)
    if profile == PROFILE_SEVERE_UNION:
        return attrs.get("data_source") == "historical_document" or bool(
            SEVERE_SPECIAL_ISSUES & special_issues(attrs)
        )

    if profile == PROFILE_RESEARCH_REPORT_DUAL:
        # The visually dual-pane brokerage pages use this GT label, not `double_column`.
        return (
            attrs.get("data_source") == "research_report"
            and attrs.get("layout") == "1andmore_column"
            and name.casefold().startswith(("eastmoney", "yanbao"))
        )

    blob = json.dumps(rec, ensure_ascii=False)
    return any(hint in name or hint in blob for hint in hints)


def build_page_list(
    records: list[dict[str, object]],
    *,
    profile: str,
    hints: list[str],
    seed: list[str],
    max_pages: int,
) -> list[str]:
    matched = [image_name(rec) for rec in records if matches_profile(rec, profile=profile, hints=hints)]
    seed_names = [Path(name).name for name in seed if name]

    if profile == PROFILE_HINTS:
        # Preserve the original helper's seed-first, GT-record-order semantics.
        candidates = seed_names + matched
    else:
        # Exact profiles are reproducible regardless of GT record order.
        candidates = sorted(set(seed_names + matched))

    seen: set[str] = set()
    selected: list[str] = []
    for name in candidates:
        if not name or name in seen:
            continue
        seen.add(name)
        selected.append(name)
        if len(selected) >= max_pages:
            break
    return selected


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gt", type=Path, required=True, help="OmniDocBench.json path")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-pages", type=int, default=48)
    p.add_argument(
        "--profile",
        choices=PROFILES,
        default=PROFILE_HINTS,
        help="Exact GT selection profile; hints preserves the legacy substring mode",
    )
    p.add_argument(
        "--expected-count",
        type=int,
        default=None,
        help="Fail before writing unless the final page count matches",
    )
    p.add_argument(
        "--seed-list",
        type=Path,
        default=None,
        help=(f"Optional page list to union with profile matches; hints mode defaults to {LEGACY_SEED_LIST}"),
    )
    p.add_argument(
        "--hints",
        nargs="*",
        default=list(DEFAULT_WEAK_HINTS),
        help="Substring hints used only by the hints profile",
    )
    args = p.parse_args()

    if args.max_pages < 1:
        p.error("--max-pages must be at least 1")
    if args.expected_count is not None and args.expected_count < 0:
        p.error("--expected-count must be non-negative")

    records = load_records(args.gt)
    seed: list[str] = []
    seed_list = args.seed_list
    if seed_list is None and args.profile == PROFILE_HINTS:
        seed_list = LEGACY_SEED_LIST
    if seed_list is not None and seed_list.is_file():
        seed = [line.strip() for line in seed_list.read_text(encoding="utf-8").splitlines() if line.strip()]

    out = build_page_list(
        records,
        profile=args.profile,
        hints=args.hints,
        seed=seed,
        max_pages=args.max_pages,
    )
    if args.expected_count is not None and len(out) != args.expected_count:
        raise SystemExit(f"profile {args.profile!r}: expected {args.expected_count} pages, got {len(out)}")

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + ("\n" if out else ""), encoding="utf-8")
    print(f"wrote {len(out)} pages for profile {args.profile!r} -> {args.out}")


if __name__ == "__main__":
    main()
