#!/usr/bin/env bash
# Run the environment doctor and refresh the committed environment evidence.
#
# Usage: scripts/doctor.sh [MODEL_DIR]
set -euo pipefail

MODEL_DIR="${1:-/root/workspace/models/Dolphin-v2}"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EVIDENCE_DIR="${REPO_ROOT}/evidence/environments"
mkdir -p "${EVIDENCE_DIR}"

"${ENV_DIR}/bin/dolphin-rocm" doctor \
    --model-dir "${MODEL_DIR}" \
    --json-out "${EVIDENCE_DIR}/runtime_attestation.json" \
    --markdown-out "${EVIDENCE_DIR}/doctor-report.md"

echo "==> Capturing raw ROCm tool output"
rocminfo > "${EVIDENCE_DIR}/rocminfo.txt" 2>&1 || true
rocm-smi > "${EVIDENCE_DIR}/rocm-smi.txt" 2>&1 || true
rocm-smi --showproductname --showmeminfo vram --showdriverversion >> "${EVIDENCE_DIR}/rocm-smi.txt" 2>&1 || true
echo "==> Evidence written to ${EVIDENCE_DIR}"
