#!/usr/bin/env bash
# Resume a previously interrupted OmniDocBench inference run.
# Completed pages in OUT_DIR/checkpoints/pages.json are skipped.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
IMG_DIR="${IMG_DIR:-${WORKSPACE}/data/OmniDocBench/images}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm}"
CONFIG="${CONFIG:-${REPO_ROOT}/eval/configs/omnidocbench_v16.yaml}"
LOG_DIR="${LOG_DIR:-${WORKSPACE}/logs}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"
export PATH="${ENV_DIR}/bin:${PATH}"

if [[ ! -f "${OUT_DIR}/checkpoints/pages.json" ]]; then
  echo "WARN: no checkpoint found at ${OUT_DIR}/checkpoints/pages.json; starting fresh"
else
  DONE=$("${ENV_DIR}/bin/python" - <<PY
import json
from pathlib import Path
recs = json.loads(Path("${OUT_DIR}/checkpoints/pages.json").read_text())
print(sum(1 for r in recs if r.get("status") == "success"))
PY
)
  echo "==> Resuming; ${DONE} pages already succeeded"
fi

"${ENV_DIR}/bin/python" "${REPO_ROOT}/eval/run_eval.py" \
  --img-dir "${IMG_DIR}" \
  --out-dir "${OUT_DIR}" \
  --config "${CONFIG}" \
  --platform linux-rocm \
  2>&1 | tee -a "${LOG_DIR}/full_eval.log"

echo "==> Resume finished. Summary: ${OUT_DIR}/run_summary.json"
