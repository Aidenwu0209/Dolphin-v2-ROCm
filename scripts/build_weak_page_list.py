#!/usr/bin/env python3
"""Build a weak-page list from OmniDocBench GT attributes (offline helper).

Requires a local OmniDocBench.json (not committed). Expands beyond the starter
list in eval/configs/cuda5070ti_weak_pages.txt when dataset is available.

Example:
  python scripts/build_weak_page_list.py \\
    --gt /path/to/OmniDocBench.json \\
    --out eval/configs/cuda5070ti_weak_pages.txt \\
    --max-pages 48
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

# Buckets that looked weak on ROCm full-eval aggregates (edit_dist / TEDS / CDM).
# Exact attribute key names follow OmniDocBench v1.6 GT schema.
DEFAULT_WEAK_HINTS = (
    "newspaper",
    "color_textbook",
    "jiaocaineedrop",
    "eastmoney",
)


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--gt", type=Path, required=True, help="OmniDocBench.json path")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--max-pages", type=int, default=48)
    p.add_argument(
        "--seed-list",
        type=Path,
        default=Path("eval/configs/cuda5070ti_weak_pages.txt"),
        help="Always include these basenames first",
    )
    p.add_argument(
        "--hints",
        nargs="*",
        default=list(DEFAULT_WEAK_HINTS),
        help="Substring hints matched against image / page id",
    )
    args = p.parse_args()

    gt = json.loads(args.gt.read_text())
    # OmniDocBench.json is typically a list of page records with an image path field.
    if isinstance(gt, dict) and "data" in gt:
        records = gt["data"]
    elif isinstance(gt, list):
        records = gt
    else:
        raise SystemExit(f"Unrecognized GT shape: {type(gt)}")

    seed: list[str] = []
    if args.seed_list.is_file():
        seed = [ln.strip() for ln in args.seed_list.read_text().splitlines() if ln.strip()]

    candidates: list[str] = []
    for rec in records:
        # Tolerate common field names across OmniDocBench exports.
        name = rec.get("image_path") or rec.get("img_id") or rec.get("page_id") or rec.get("image") or ""
        base = Path(str(name)).name
        if not base:
            continue
        blob = json.dumps(rec, ensure_ascii=False)
        if any(h in base or h in blob for h in args.hints):
            candidates.append(base)

    seen: set[str] = set()
    out: list[str] = []
    for name in seed + candidates:
        if name in seen:
            continue
        seen.add(name)
        out.append(name)
        if len(out) >= args.max_pages:
            break

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text("\n".join(out) + "\n")
    print(f"wrote {len(out)} pages -> {args.out}")


if __name__ == "__main__":
    main()
