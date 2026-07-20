#!/usr/bin/env bash
# Attach model_card, runtime attestation, and performance stubs to a result dir.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT_DIR="${1:?usage: finalize_result_dir.sh <result_dir>}"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
MODEL_DIR="${MODEL_DIR:-/root/workspace/models/Dolphin-v2}"

mkdir -p "${OUT_DIR}"

if [[ -f "${REPO_ROOT}/evidence/environments/runtime_attestation.json" ]]; then
  cp -f "${REPO_ROOT}/evidence/environments/runtime_attestation.json" \
    "${OUT_DIR}/runtime_attestation.json"
fi

"${ENV_DIR}/bin/python" - <<PY
import json
from pathlib import Path
out = Path("${OUT_DIR}")
card = {
    "repo": "ByteDance/Dolphin-v2",
    "revision": "c37c62768c644bb594da4283149c627765aa80f3",
    "local_path": "${MODEL_DIR}",
    "license_pointer": "MODEL_LICENSE",
    "architecture": "Qwen2.5-VL based Dolphin-v2",
    "dtype": "bfloat16",
    "backend_baseline": "transformers",
}
(out / "model_card.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
print("wrote", out / "model_card.json")
PY

if [[ ! -f "${OUT_DIR}/performance.json" && -f "${OUT_DIR}/_run_stats.json" ]]; then
  "${ENV_DIR}/bin/python" - <<PY
import json, statistics
from pathlib import Path
out = Path("${OUT_DIR}")
stats = json.loads((out / "_run_stats.json").read_text())
pages = []
cp = out / "checkpoints" / "pages.json"
if cp.exists():
    pages = [p for p in json.loads(cp.read_text()) if p.get("status") == "success"]
lat = sorted(p["latency_ms"] for p in pages if p.get("latency_ms") is not None)
def pct(xs, q):
    if not xs:
        return None
    idx = min(len(xs)-1, max(0, int(round(q * (len(xs)-1)))))
    return xs[idx]
perf = {
    "label": "run_attached",
    "generated_at": stats.get("finished_at"),
    "backend": stats.get("backend"),
    "config_digest": stats.get("config_digest"),
    "input_pages": [p["page_id"] for p in pages],
    "repeats": 1,
    "model_load_seconds": stats.get("model_load_seconds"),
    "first_page_latency_ms": lat[0] if lat else None,
    "median_across_repeats": {
        "p50_ms": pct(lat, 0.50),
        "p95_ms": pct(lat, 0.95),
        "mean_ms": (sum(lat)/len(lat)) if lat else None,
        "pages_per_second": (len(lat) / stats["duration_seconds"]) if lat and stats.get("duration_seconds") else None,
        "wall_seconds": stats.get("duration_seconds"),
    },
    "per_repeat": [
        {
            "p50_ms": pct(lat, 0.50),
            "p95_ms": pct(lat, 0.95),
            "pages_per_second": (len(lat) / stats["duration_seconds"]) if lat and stats.get("duration_seconds") else None,
            "failures": stats.get("failed", 0),
        }
    ],
    "note": "Single-run attachment; use eval/run_benchmark.py for formal 3-repeat benchmarks.",
}
(out / "performance.json").write_text(json.dumps(perf, indent=2), encoding="utf-8")
print("wrote", out / "performance.json")
PY
fi

echo "==> Finalized ${OUT_DIR}"
