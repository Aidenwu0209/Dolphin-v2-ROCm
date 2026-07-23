"""Run OmniDocBench inference (smoke / canary / full) with checkpoint support.

This script only produces *predictions* plus run metadata. Scoring is done by
the pinned official OmniDocBench evaluator in a separate environment (see
scripts/run_full_eval.sh).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))
sys.path.insert(0, str(REPO_ROOT))

from eval.adapter import run_adapter, verify_output_completeness  # noqa: E402

from dolphin_v2_rocm.config import load_config  # noqa: E402
from dolphin_v2_rocm.contracts import write_json  # noqa: E402
from dolphin_v2_rocm.provenance import build_provenance, save_provenance  # noqa: E402


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="OmniDocBench inference runner")
    parser.add_argument("--img-dir", required=True, help="benchmark image directory")
    parser.add_argument("--out-dir", required=True, help="prediction output directory")
    parser.add_argument("--config", required=True, help="YAML run config")
    parser.add_argument("--platform", default="linux-rocm")
    parser.add_argument("--backend", default=None)
    parser.add_argument("--limit-pages", type=int, default=None)
    parser.add_argument(
        "--page-list", default=None, help="file with one image filename per line (subset run)"
    )
    args = parser.parse_args(argv)

    overrides = {}
    if args.backend:
        overrides["backend"] = args.backend
    if args.limit_pages is not None:
        overrides["limit_pages"] = args.limit_pages
    config = load_config(args.config, overrides=overrides)

    img_dir = Path(args.img_dir)
    if args.page_list:
        # materialize a symlink subset directory for deterministic subset runs
        subset_dir = Path(args.out_dir) / "_subset_inputs"
        subset_dir.mkdir(parents=True, exist_ok=True)
        names = [line.strip() for line in Path(args.page_list).read_text().splitlines() if line.strip()]
        for name in names:
            src = img_dir / name
            if not src.exists():
                raise FileNotFoundError(f"page-list entry not found: {src}")
            dst = subset_dir / name
            if not dst.exists():
                dst.symlink_to(src.resolve())
        img_dir = subset_dir

    summary = run_adapter(img_dir, args.out_dir, platform=args.platform, config=config)
    completeness = verify_output_completeness(img_dir, args.out_dir)
    summary["output_completeness"] = completeness
    write_json(Path(args.out_dir) / "run_summary.json", summary)

    provenance = build_provenance(
        model_path=config.get("model_path"),
        model_repo="ByteDance/Dolphin-v2",
        model_revision=config.get("model_revision"),
        dataset_name=config.get("dataset_name", "opendatalab/OmniDocBench"),
        dataset_revision=config.get("dataset_revision"),
        config=config.to_dict(),
        config_digest=config.digest,
        repo_dir=REPO_ROOT,
    )
    save_provenance(Path(args.out_dir) / "provenance.json", provenance)

    print(json.dumps(summary, indent=2, ensure_ascii=False))
    if not completeness["complete"]:
        print("ERROR: output completeness check failed", file=sys.stderr)
        return 3
    return 0 if summary["failed"] == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
