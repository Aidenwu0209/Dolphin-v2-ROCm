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
# Matching 1651 pages opens many files; default ulimit -n 1024 fails mid-run.
ulimit -n 65536 || ulimit -n 16384 || true
echo "    ulimit -n=$(ulimit -n)"

# Rewrite prediction path in a temp config so OUT_DIR can vary.
TMP_CFG="$(mktemp)"
sed "s|data_path: .*/markdown|data_path: ${OUT_DIR}/markdown|" "${SCORE_CONFIG}" > "${TMP_CFG}"
# Keep file descriptors under control on large runs (override via MATCH_WORKERS).
if [[ -n "${MATCH_WORKERS:-}" ]]; then
  python3 - "${TMP_CFG}" "${MATCH_WORKERS}" <<'PY'
import sys
from pathlib import Path
path = Path(sys.argv[1])
workers = int(sys.argv[2])
text = path.read_text(encoding="utf-8")
import re
text = re.sub(r"(match_workers:\s*)\d+", rf"\g<1>{workers}", text)
text = re.sub(r"(cdm_workers:\s*)\d+", rf"\g<1>{workers}", text)
text = re.sub(r"(teds_workers:\s*)\d+", rf"\g<1>{workers}", text)
path.write_text(text, encoding="utf-8")
PY
fi

if [[ ! -x "${EVAL_ENV}/bin/omnidocbench-eval" ]]; then
  echo "ERROR: ${EVAL_ENV}/bin/omnidocbench-eval not found; run scripts/setup_eval_env.sh" >&2
  exit 2
fi

# Isolate result dir so we never copy a stale canary metric after a failed run.
RESULT_DIR="${SCORE_WORKDIR}/result"
ARCHIVE_DIR="${SCORE_WORKDIR}/result_archive_$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -d "${RESULT_DIR}" ]] && ls "${RESULT_DIR}"/*metric_result.json >/dev/null 2>&1; then
  mkdir -p "${ARCHIVE_DIR}"
  mv "${RESULT_DIR}"/* "${ARCHIVE_DIR}/" 2>/dev/null || true
  echo "==> Archived previous scorer outputs to ${ARCHIVE_DIR}"
fi
mkdir -p "${RESULT_DIR}"
SCORE_STARTED_EPOCH="$(date +%s)"

set +e
(
  cd "${SCORE_WORKDIR}"
  "${EVAL_ENV}/bin/omnidocbench-eval" --config "${TMP_CFG}"
)
SCORE_RC=$?
set -e
echo "SCORER_EXIT=${SCORE_RC}" | tee -a "${LOG_DIR}/full_score.log"

if [[ "${SCORE_RC}" -ne 0 ]]; then
  echo "ERROR: official scorer failed with exit ${SCORE_RC}; refusing to copy stale metrics" >&2
  rm -f "${TMP_CFG}"
  exit "${SCORE_RC}"
fi

# Only accept metric files newer than this scoring attempt.
METRIC_SRC=""
while IFS= read -r candidate; do
  if [[ "$(stat -c %Y "${candidate}" 2>/dev/null || stat -f %m "${candidate}")" -ge "${SCORE_STARTED_EPOCH}" ]]; then
    METRIC_SRC="${candidate}"
    break
  fi
done < <(ls -t "${RESULT_DIR}"/*metric_result.json 2>/dev/null || true)

if [[ -z "${METRIC_SRC}" ]]; then
  echo "ERROR: no fresh metric_result.json under ${RESULT_DIR} after successful scorer exit" >&2
  rm -f "${TMP_CFG}"
  exit 3
fi

cp -f "${METRIC_SRC}" "${OUT_DIR}/metric_result.json"
SUMMARY_SRC="${RESULT_DIR}/markdown_quick_match_run_summary.json"
if [[ -f "${SUMMARY_SRC}" ]]; then
  cp -f "${SUMMARY_SRC}" "${OUT_DIR}/scorer_run_summary.json"
fi
echo "==> Metrics copied to ${OUT_DIR}/metric_result.json (from ${METRIC_SRC})"
rm -f "${TMP_CFG}"
