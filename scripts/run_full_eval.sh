#!/usr/bin/env bash
# Full OmniDocBench v1.6 inference + optional official scoring.
#
# Stages:
#   1) Transformers ROCm inference over the pinned dataset images (resumable)
#   2) Official OmniDocBench scorer in the eval environment (if SCORE=1)
#
# Usage:
#   scripts/run_full_eval.sh
#   SCORE=1 scripts/run_full_eval.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
EVAL_ENV="${EVAL_ENV:-/root/workspace/envs/odb-eval}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
IMG_DIR="${IMG_DIR:-${WORKSPACE}/data/OmniDocBench/images}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm}"
CONFIG="${CONFIG:-${REPO_ROOT}/eval/configs/omnidocbench_v16.yaml}"
LOG_DIR="${LOG_DIR:-${WORKSPACE}/logs}"
SCORE="${SCORE:-0}"
GT_JSON="${GT_JSON:-${WORKSPACE}/data/OmniDocBench/OmniDocBench.json}"
OMNIDOCBENCH_SRC="${OMNIDOCBENCH_SRC:-${WORKSPACE}/OmniDocBench}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"
export PATH="${ENV_DIR}/bin:${PATH}"

if [[ ! -d "${IMG_DIR}" ]]; then
  echo "ERROR: image directory not found: ${IMG_DIR}" >&2
  exit 1
fi

PAGE_COUNT=$(find "${IMG_DIR}" -maxdepth 1 \( -iname '*.jpg' -o -iname '*.jpeg' -o -iname '*.png' \) | wc -l | tr -d ' ')
echo "==> Full OmniDocBench inference"
echo "    images : ${IMG_DIR} (${PAGE_COUNT} files)"
echo "    output : ${OUT_DIR}"
echo "    config : ${CONFIG}"

"${ENV_DIR}/bin/python" "${REPO_ROOT}/eval/run_eval.py" \
  --img-dir "${IMG_DIR}" \
  --out-dir "${OUT_DIR}" \
  --config "${CONFIG}" \
  --platform linux-rocm \
  2>&1 | tee -a "${LOG_DIR}/full_eval.log"

echo "==> Inference finished. Summary: ${OUT_DIR}/run_summary.json"

if [[ "${SCORE}" != "1" ]]; then
  echo "==> Skipping official scorer (set SCORE=1 to enable)"
  exit 0
fi

echo "==> Running official OmniDocBench scorer"
PRED_DIR="${OUT_DIR}/markdown"
SCORE_OUT="${OUT_DIR}/metric_result.json"

# OmniDocBench CLI entrypoints differ slightly across revisions; try common forms.
if [[ -x "${EVAL_ENV}/bin/omnidocbench" ]]; then
  "${EVAL_ENV}/bin/omnidocbench" \
    --pred "${PRED_DIR}" \
    --gt "${GT_JSON}" \
    --out "${SCORE_OUT}" \
    2>&1 | tee -a "${LOG_DIR}/full_score.log"
elif [[ -f "${OMNIDOCBENCH_SRC}/pdf_validation.py" ]]; then
  "${EVAL_ENV}/bin/python" "${OMNIDOCBENCH_SRC}/pdf_validation.py" \
    --pred_path "${PRED_DIR}" \
    --gt_path "${GT_JSON}" \
    --output "${SCORE_OUT}" \
    2>&1 | tee -a "${LOG_DIR}/full_score.log" || true
  # Fallback: use metrics runner if present
  if [[ ! -f "${SCORE_OUT}" ]]; then
    "${EVAL_ENV}/bin/python" - <<PY
import json, sys
from pathlib import Path
print("Scorer entrypoint needs manual wiring for this OmniDocBench revision.", file=sys.stderr)
print("Predictions are ready at: ${PRED_DIR}", file=sys.stderr)
sys.exit(2)
PY
  fi
else
  echo "ERROR: could not locate OmniDocBench scorer entrypoint" >&2
  exit 2
fi

echo "==> Metrics written to ${SCORE_OUT}"
