#!/usr/bin/env bash
# Official OmniDocBench scoring only (inference already finished).
#
# Usage:
#   MATCH_WORKERS=4 bash scripts/run_full_score.sh
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVAL_ENV="${EVAL_ENV:-/root/workspace/envs/odb-eval}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm}"
LOG_DIR="${LOG_DIR:-${WORKSPACE}/logs}"
GT_JSON="${GT_JSON:-${WORKSPACE}/data/OmniDocBench/OmniDocBench.json}"
OMNIDOCBENCH_SRC="${OMNIDOCBENCH_SRC:-${WORKSPACE}/OmniDocBench}"
SCORE_CONFIG="${SCORE_CONFIG:-${REPO_ROOT}/eval/configs/end2end_rocm.yaml}"
MATCH_WORKERS="${MATCH_WORKERS:-4}"
MIN_PAGE_COUNT="${MIN_PAGE_COUNT:-1600}"

mkdir -p "${OUT_DIR}" "${LOG_DIR}"

if [[ ! -d "${OUT_DIR}/markdown" ]]; then
  echo "ERROR: prediction markdown dir missing: ${OUT_DIR}/markdown" >&2
  exit 1
fi
if [[ ! -x "${EVAL_ENV}/bin/omnidocbench-eval" ]]; then
  echo "ERROR: ${EVAL_ENV}/bin/omnidocbench-eval not found; run scripts/setup_eval_env.sh" >&2
  exit 2
fi

# Matching 1651 pages opens many files; default ulimit -n 1024 fails mid-run.
ulimit -n 65536 || ulimit -n 16384 || true
echo "==> Full OmniDocBench scoring"
echo "    predictions : ${OUT_DIR}/markdown"
echo "    gt          : ${GT_JSON}"
echo "    workers     : ${MATCH_WORKERS}"
echo "    ulimit -n   : $(ulimit -n)"

TMP_CFG="$(mktemp)"
sed "s|data_path: .*/markdown|data_path: ${OUT_DIR}/markdown|" "${SCORE_CONFIG}" > "${TMP_CFG}"
python3 - "${TMP_CFG}" "${MATCH_WORKERS}" <<'PY'
import re
import sys
from pathlib import Path

path = Path(sys.argv[1])
workers = int(sys.argv[2])
text = path.read_text(encoding="utf-8")
text = re.sub(r"(match_workers:\s*)\d+", rf"\g<1>{workers}", text)
text = re.sub(r"(cdm_workers:\s*)\d+", rf"\g<1>{workers}", text)
text = re.sub(r"(teds_workers:\s*)\d+", rf"\g<1>{workers}", text)
path.write_text(text, encoding="utf-8")
PY

RESULT_DIR="${OMNIDOCBENCH_SRC}/result"
ARCHIVE_DIR="${OMNIDOCBENCH_SRC}/result_archive_$(date -u +%Y%m%dT%H%M%SZ)"
if [[ -d "${RESULT_DIR}" ]] && ls "${RESULT_DIR}"/*metric_result.json >/dev/null 2>&1; then
  mkdir -p "${ARCHIVE_DIR}"
  mv "${RESULT_DIR}"/* "${ARCHIVE_DIR}/" 2>/dev/null || true
  echo "==> Archived previous scorer outputs to ${ARCHIVE_DIR}"
fi
mkdir -p "${RESULT_DIR}"
SCORE_STARTED_EPOCH="$(date +%s)"

set +e
(
  cd "${OMNIDOCBENCH_SRC}"
  "${EVAL_ENV}/bin/omnidocbench-eval" --config "${TMP_CFG}"
) 2>&1 | tee -a "${LOG_DIR}/full_score.log"
SCORE_RC=${PIPESTATUS[0]}
set -e
echo "SCORER_EXIT=${SCORE_RC}" | tee -a "${LOG_DIR}/full_score.log"
rm -f "${TMP_CFG}"

if [[ "${SCORE_RC}" -ne 0 ]]; then
  echo "ERROR: official scorer failed with exit ${SCORE_RC}; refusing to copy stale metrics" >&2
  exit "${SCORE_RC}"
fi

METRIC_SRC=""
while IFS= read -r candidate; do
  mtime="$(stat -c %Y "${candidate}" 2>/dev/null || stat -f %m "${candidate}")"
  if [[ "${mtime}" -ge "${SCORE_STARTED_EPOCH}" ]]; then
    METRIC_SRC="${candidate}"
    break
  fi
done < <(ls -t "${RESULT_DIR}"/*metric_result.json 2>/dev/null || true)

if [[ -z "${METRIC_SRC}" ]]; then
  echo "ERROR: no fresh metric_result.json under ${RESULT_DIR}" >&2
  exit 3
fi

cp -f "${METRIC_SRC}" "${OUT_DIR}/metric_result.json"
if [[ -f "${RESULT_DIR}/markdown_quick_match_run_summary.json" ]]; then
  cp -f "${RESULT_DIR}/markdown_quick_match_run_summary.json" "${OUT_DIR}/scorer_run_summary.json"
fi

python3 - "${OUT_DIR}/scorer_run_summary.json" "${MIN_PAGE_COUNT}" <<'PY'
import json
import sys
from pathlib import Path

summary_path = Path(sys.argv[1])
min_pages = int(sys.argv[2])
if not summary_path.exists():
    raise SystemExit(f"missing scorer summary: {summary_path}")
data = json.loads(summary_path.read_text(encoding="utf-8"))
page_count = data.get("stage_execution", {}).get("page_match", {}).get("page_count")
print(f"scorer page_count={page_count}")
if not page_count or page_count < min_pages:
    raise SystemExit(
        f"refusing metric copy: page_count={page_count} < min_pages={min_pages} "
        "(likely a canary/stale run)"
    )
print("FULL_METRIC_OK")
PY

echo "==> Metrics copied to ${OUT_DIR}/metric_result.json"
bash "${REPO_ROOT}/scripts/finalize_result_dir.sh" "${OUT_DIR}"
