#!/usr/bin/env bash
# Run the OmniDocBench canary subset (fixed page list or config limit_pages).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
IMG_DIR="${IMG_DIR:-${WORKSPACE}/data/OmniDocBench/images}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm-canary}"
CONFIG="${CONFIG:-${REPO_ROOT}/eval/configs/canary.yaml}"
PAGE_LIST="${PAGE_LIST:-${REPO_ROOT}/eval/configs/canary_pages.txt}"
LOG_DIR="${LOG_DIR:-${WORKSPACE}/logs}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"
export PATH="${ENV_DIR}/bin:${PATH}"

EXTRA=()
if [[ -f "${PAGE_LIST}" ]]; then
  EXTRA+=(--page-list "${PAGE_LIST}")
  echo "==> Using page list ${PAGE_LIST}"
fi

echo "==> Canary inference"
"${ENV_DIR}/bin/python" "${REPO_ROOT}/eval/run_eval.py" \
  --img-dir "${IMG_DIR}" \
  --out-dir "${OUT_DIR}" \
  --config "${CONFIG}" \
  --platform linux-rocm \
  "${EXTRA[@]}" \
  2>&1 | tee "${LOG_DIR}/canary.log"

echo "==> Canary complete. Summary: ${OUT_DIR}/run_summary.json"
