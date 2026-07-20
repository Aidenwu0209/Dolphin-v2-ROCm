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
SCORE_CONFIG="${SCORE_CONFIG:-${REPO_ROOT}/eval/configs/end2end_rocm.yaml}"
SCORE_WORKDIR="${OMNIDOCBENCH_SRC}"

# Rewrite prediction path in a temp config so OUT_DIR can vary.
TMP_CFG="$(mktemp)"
sed "s|data_path: .*/markdown|data_path: ${OUT_DIR}/markdown|" "${SCORE_CONFIG}" > "${TMP_CFG}"

if [[ ! -x "${EVAL_ENV}/bin/omnidocbench-eval" ]]; then
  echo "ERROR: ${EVAL_ENV}/bin/omnidocbench-eval not found; run scripts/setup_eval_env.sh" >&2
  exit 2
fi

(
  cd "${SCORE_WORKDIR}"
  "${EVAL_ENV}/bin/omnidocbench-eval" --config "${TMP_CFG}"
) 2>&1 | tee -a "${LOG_DIR}/full_score.log"

# OmniDocBench writes under result/; copy the metric file into OUT_DIR.
METRIC_SRC="$(ls -t "${SCORE_WORKDIR}"/result/*metric_result.json 2>/dev/null | head -1 || true)"
if [[ -n "${METRIC_SRC}" ]]; then
  cp -f "${METRIC_SRC}" "${OUT_DIR}/metric_result.json"
  echo "==> Metrics copied to ${OUT_DIR}/metric_result.json"
else
  echo "ERROR: could not find metric_result.json under ${SCORE_WORKDIR}/result" >&2
  exit 3
fi
rm -f "${TMP_CFG}"
