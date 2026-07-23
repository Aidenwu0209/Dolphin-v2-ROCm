#!/usr/bin/env bash
# Run the multi-page smoke inference (examples/inputs or WORKSPACE samples).
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
INPUT_DIR="${INPUT_DIR:-${WORKSPACE}/samples}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/results/smoke}"
CONFIG="${CONFIG:-${REPO_ROOT}/eval/configs/smoke.yaml}"
LOG_DIR="${LOG_DIR:-${WORKSPACE}/logs}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"
export PATH="${ENV_DIR}/bin:${PATH}"

echo "==> Smoke inference"
echo "    input : ${INPUT_DIR}"
echo "    output: ${OUT_DIR}"
echo "    config: ${CONFIG}"

"${ENV_DIR}/bin/dolphin-rocm" infer \
  --input "${INPUT_DIR}" \
  --output "${OUT_DIR}" \
  --backend transformers \
  --config "${CONFIG}" \
  2>&1 | tee "${LOG_DIR}/smoke.log"

echo "==> Smoke complete. Summary: ${OUT_DIR}/_run_stats.json"
