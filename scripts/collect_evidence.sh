#!/usr/bin/env bash
# Collect environment, accuracy, and performance evidence into evidence/.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
WORKSPACE="${WORKSPACE:-/root/workspace}"
EVIDENCE="${REPO_ROOT}/evidence"
RESULTS="${RESULTS:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm}"

mkdir -p \
  "${EVIDENCE}/environments" \
  "${EVIDENCE}/compatibility" \
  "${EVIDENCE}/accuracy" \
  "${EVIDENCE}/performance" \
  "${EVIDENCE}/upstream-issues"

export PATH="${ENV_DIR}/bin:${PATH}"

echo "==> Doctor attestation"
"${ENV_DIR}/bin/dolphin-rocm" doctor \
  --model-dir "${WORKSPACE}/models/Dolphin-v2" \
  --json-out "${EVIDENCE}/environments/runtime_attestation.json" \
  --markdown-out "${EVIDENCE}/environments/doctor-report.md" \
  >/dev/null

rocminfo > "${EVIDENCE}/environments/rocminfo.txt" 2>&1 || true
rocm-smi > "${EVIDENCE}/environments/rocm-smi.txt" 2>&1 || true

if [[ -f "${RESULTS}/metric_result.json" ]]; then
  cp -f "${RESULTS}/metric_result.json" "${EVIDENCE}/accuracy/metric_result.json"
fi
if [[ -f "${RESULTS}/run_summary.json" ]]; then
  cp -f "${RESULTS}/run_summary.json" "${EVIDENCE}/accuracy/run_summary.json"
fi
if [[ -f "${RESULTS}/performance.json" ]]; then
  cp -f "${RESULTS}/performance.json" "${EVIDENCE}/performance/run_performance.json"
fi

echo "==> Evidence collected under ${EVIDENCE}"
find "${EVIDENCE}" -type f | sort
