#!/usr/bin/env python3
"""Build a stratified canary page list from OmniDocBench.json."""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--gt", required=True, help="OmniDocBench.json path")
    parser.add_argument("--out", required=True, help="output page list text file")
    parser.add_argument("--n", type=int, default=20)
    args = parser.parse_args()

    data = json.loads(Path(args.gt).read_text(encoding="utf-8"))
    buckets: dict[str, list[str]] = defaultdict(list)
    for item in data:
        # OmniDocBench entries typically carry page info / attributes.
        page = item.get("page_info", {}) if isinstance(item, dict) else {}
        image = page.get("image_path") or item.get("image_path") or item.get("page_name")
        if not image:
            # fallback: try common keys
            for key in ("img_id", "page_id", "file_name"):
                if key in item:
                    image = item[key]
                    break
        if not image:
            continue
        image = Path(str(image)).name
        attrs = item.get("page_info", {}).get("page_attribute", item.get("attribute", {}))
        if isinstance(attrs, dict):
            key = (
                str(attrs.get("data_source", attrs.get("language", "unknown")))
                + "|"
                + str(attrs.get("layout", attrs.get("page_type", "unknown")))
            )
        else:
            key = "unknown"
        buckets[key].append(image)

    selected: list[str] = []
    # round-robin across buckets for diversity
    while len(selected) < args.n and any(buckets.values()):
        for key in sorted(buckets.keys()):
            if buckets[key] and len(selected) < args.n:
                selected.append(buckets[key].pop(0))
    # de-dupe preserve order
    seen = set()
    ordered = []
    for name in selected:
        if name not in seen:
            seen.add(name)
            ordered.append(name)

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(ordered) + ("\n" if ordered else ""), encoding="utf-8")
    print(f"wrote {len(ordered)} pages to {out} from {len(data)} gt entries / {len(buckets)} buckets")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
