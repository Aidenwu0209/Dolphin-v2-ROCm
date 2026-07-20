"""Performance benchmark collection for Dolphin-v2 on ROCm.

Measures, with a fixed input set and fixed generation parameters:
- model load time
- first-page latency (cold)
- per-page latency (p50 / p95 / mean)
- pages per second
- peak VRAM per page and per run
- GPU/CPU utilization snapshots (rocm-smi / psutil)

The benchmark repeats the full page set ``--repeats`` times (default 3) and
reports the median across repeats, as required by the performance protocol.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
import threading
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "src"))

from dolphin_v2_rocm.backends import create_backend  # noqa: E402
from dolphin_v2_rocm.config import load_config  # noqa: E402
from dolphin_v2_rocm.contracts import write_json  # noqa: E402
from dolphin_v2_rocm.pipeline import discover_pages  # noqa: E402
from dolphin_v2_rocm.provenance import build_provenance, utc_now  # noqa: E402


class UtilizationSampler(threading.Thread):
    """Sample GPU busy % / VRAM % via rocm-smi and CPU % via psutil."""

    def __init__(self, interval_s: float = 2.0):
        super().__init__(daemon=True)
        self.interval_s = interval_s
        self.samples: list[dict] = []
        self._stop = threading.Event()

    def run(self) -> None:
        try:
            import psutil
        except ImportError:
            psutil = None
        while not self._stop.is_set():
            sample: dict = {"t": time.time()}
            try:
                out = subprocess.run(
                    ["rocm-smi", "--showuse", "--showmemuse", "--json"],
                    capture_output=True,
                    text=True,
                    timeout=10,
                ).stdout
                data = json.loads(out)
                card = next(iter(data.values()))
                sample["gpu_busy_pct"] = float(card.get("GPU use (%)", "nan"))
                sample["vram_used_pct"] = float(card.get("GPU Memory Allocated (VRAM%)", "nan"))
            except Exception:  # noqa: BLE001 - sampling is best-effort
                pass
            if psutil:
                sample["cpu_pct"] = psutil.cpu_percent(interval=None)
            self.samples.append(sample)
            self._stop.wait(self.interval_s)

    def stop(self) -> dict:
        self._stop.set()
        self.join(timeout=5)
        gpu = [s["gpu_busy_pct"] for s in self.samples if "gpu_busy_pct" in s]
        cpu = [s["cpu_pct"] for s in self.samples if "cpu_pct" in s]
        vram = [s["vram_used_pct"] for s in self.samples if "vram_used_pct" in s]
        summarize = lambda xs: (
            {"mean": round(statistics.mean(xs), 1), "max": round(max(xs), 1)} if xs else None
        )  # noqa: E731
        return {
            "gpu_busy_pct": summarize(gpu),
            "cpu_pct": summarize(cpu),
            "vram_used_pct": summarize(vram),
            "n_samples": len(self.samples),
        }


def percentile(values: list[float], pct: float) -> float:
    if not values:
        return float("nan")
    ordered = sorted(values)
    k = (len(ordered) - 1) * pct / 100
    f = int(k)
    c = min(f + 1, len(ordered) - 1)
    return ordered[f] + (ordered[c] - ordered[f]) * (k - f)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dolphin-v2 ROCm benchmark")
    parser.add_argument("--img-dir", required=True)
    parser.add_argument("--out", required=True, help="output JSON file")
    parser.add_argument("--config", required=True)
    parser.add_argument("--backend", default=None)
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--warmup-pages", type=int, default=1)
    parser.add_argument("--limit-pages", type=int, default=None)
    parser.add_argument("--label", default="baseline")
    args = parser.parse_args(argv)

    overrides = {}
    if args.backend:
        overrides["backend"] = args.backend
    if args.limit_pages is not None:
        overrides["limit_pages"] = args.limit_pages
    config = load_config(args.config, overrides=overrides)

    pages = discover_pages(args.img_dir, limit=config.get("limit_pages"))
    if not pages:
        raise FileNotFoundError(f"no pages in {args.img_dir}")

    backend = create_backend(args.backend or config.get("backend"), config)
    load_start = time.perf_counter()
    backend.load()
    load_seconds = round(time.perf_counter() - load_start, 2)

    scratch = Path(args.out).parent / f"_bench_scratch_{args.label}"
    repeats: list[dict] = []
    first_page_latency_ms: float | None = None
    try:
        # cold first page (after load, before warmup)
        first = backend.parse_page(pages[0], scratch / "first")
        first_page_latency_ms = first.latency_ms

        for warm_idx in range(args.warmup_pages):
            backend.parse_page(pages[warm_idx % len(pages)], scratch / "warmup")

        for rep in range(args.repeats):
            sampler = UtilizationSampler()
            sampler.start()
            latencies: list[float] = []
            peak_vram: list[float] = []
            failures = 0
            rep_start = time.perf_counter()
            for page in pages:
                try:
                    result = backend.parse_page(page, scratch / f"rep{rep}")
                    latencies.append(result.latency_ms)
                    if result.peak_vram_mb:
                        peak_vram.append(result.peak_vram_mb)
                except Exception:  # noqa: BLE001
                    failures += 1
            wall = time.perf_counter() - rep_start
            util = sampler.stop()
            repeats.append(
                {
                    "latencies_ms": latencies,
                    "p50_ms": round(percentile(latencies, 50), 1),
                    "p95_ms": round(percentile(latencies, 95), 1),
                    "mean_ms": round(statistics.mean(latencies), 1) if latencies else None,
                    "pages_per_second": round(len(latencies) / wall, 4),
                    "wall_seconds": round(wall, 1),
                    "peak_vram_mb": max(peak_vram) if peak_vram else None,
                    "failures": failures,
                    "utilization": util,
                }
            )
    finally:
        backend.close()

    median_of = lambda key: round(statistics.median(r[key] for r in repeats if r[key] is not None), 3)  # noqa: E731
    payload = {
        "label": args.label,
        "generated_at": utc_now(),
        "backend": backend.name,
        "config_digest": config.digest,
        "config": config.to_dict(),
        "input_pages": [p.name for p in pages],
        "warmup_pages": args.warmup_pages,
        "repeats": args.repeats,
        "model_load_seconds": load_seconds,
        "first_page_latency_ms": first_page_latency_ms,
        "median_across_repeats": {
            "p50_ms": median_of("p50_ms"),
            "p95_ms": median_of("p95_ms"),
            "mean_ms": median_of("mean_ms"),
            "pages_per_second": median_of("pages_per_second"),
            "wall_seconds": median_of("wall_seconds"),
        },
        "per_repeat": repeats,
        "provenance": build_provenance(
            model_path=config.get("model_path"),
            model_repo="ByteDance/Dolphin-v2",
            model_revision=config.get("model_revision"),
            config_digest=config.digest,
            repo_dir=REPO_ROOT,
        ),
    }
    write_json(args.out, payload)
    print(json.dumps({k: payload[k] for k in ("label", "model_load_seconds", "first_page_latency_ms", "median_across_repeats")}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
