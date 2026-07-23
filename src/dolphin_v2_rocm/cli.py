"""``dolphin-rocm`` command line interface.

Subcommands:
- ``doctor``: run environment diagnostics, emit JSON + Markdown reports.
- ``infer``:  parse a directory of page images with a chosen backend.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
from pathlib import Path

from .config import load_config
from .doctor import render_markdown, run_doctor
from .pipeline import run_pipeline


def _cmd_doctor(args: argparse.Namespace) -> int:
    report = run_doctor(model_dir=args.model_dir)
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    if args.markdown_out:
        Path(args.markdown_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.markdown_out).write_text(render_markdown(report), encoding="utf-8")
    print(render_markdown(report))
    return 0 if report["overall"] != "FAIL" else 1


def _cmd_infer(args: argparse.Namespace) -> int:
    overrides = {}
    if args.backend:
        overrides["backend"] = args.backend
    if args.model_path:
        overrides["model_path"] = args.model_path
    if args.limit_pages is not None:
        overrides["limit_pages"] = args.limit_pages
    config = load_config(args.config, overrides=overrides)
    summary = run_pipeline(
        input_dir=args.input,
        output_dir=args.output,
        config=config,
        resume=not args.no_resume,
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0 if summary["failed"] == 0 else 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="dolphin-rocm", description="Dolphin-v2 on AMD ROCm")
    parser.add_argument("-v", "--verbose", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    doctor = sub.add_parser("doctor", help="diagnose the ROCm inference environment")
    doctor.add_argument("--model-dir", default=None, help="expected model weight directory")
    doctor.add_argument("--json-out", default=None, help="write machine-readable report here")
    doctor.add_argument("--markdown-out", default=None, help="write human-readable report here")
    doctor.set_defaults(func=_cmd_doctor)

    infer = sub.add_parser("infer", help="parse a directory of page images")
    infer.add_argument("--input", required=True, help="directory containing page images")
    infer.add_argument("--output", required=True, help="output directory")
    infer.add_argument("--config", required=True, help="YAML run config")
    infer.add_argument("--backend", default=None, help="override backend (transformers/vllm/mock)")
    infer.add_argument("--model-path", default=None, help="override model path")
    infer.add_argument("--limit-pages", type=int, default=None, help="only process the first N pages")
    infer.add_argument("--no-resume", action="store_true", help="do not skip already-completed pages")
    infer.set_defaults(func=_cmd_infer)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
