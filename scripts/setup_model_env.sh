#!/usr/bin/env bash
# Set up the isolated model-inference environment (Python 3.12 + ROCm PyTorch).
#
# Usage: scripts/setup_model_env.sh [ENV_DIR]
# Default ENV_DIR: /root/workspace/envs/dolphin
#
# The ROCm wheel pins below were validated on ROCm 7.2.0 / gfx1100 and are the
# same builds recorded in runtime-manifest.json. Do not silently upgrade them.
set -euo pipefail

ENV_DIR="${1:-/root/workspace/envs/dolphin}"
PYTHON_BIN="${PYTHON_BIN:-python3.12}"
ROCM_WHEEL_INDEX="https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "==> Creating venv at ${ENV_DIR} with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${ENV_DIR}"
"${ENV_DIR}/bin/pip" install --upgrade pip

echo "==> Installing ROCm PyTorch stack (pinned)"
"${ENV_DIR}/bin/pip" install --no-cache-dir -f "${ROCM_WHEEL_INDEX}" \
    "torch==2.7.1+rocm7.2.0.lw.git262e50d5" \
    "torchvision==0.22.1+rocm7.2.0.git59a3e1f9" \
    "triton==3.3.1+rocm7.2.0.git28a7371e"

echo "==> Installing inference dependencies (pinned)"
"${ENV_DIR}/bin/pip" install \
    "transformers==4.51.0" \
    "accelerate==1.4.0" \
    "qwen-vl-utils==0.0.14" \
    pillow numpy pymupdf pyyaml psutil huggingface_hub

echo "==> Installing dolphin-v2-rocm package"
"${ENV_DIR}/bin/pip" install -e "${REPO_ROOT}"

echo "==> Verifying GPU visibility"
"${ENV_DIR}/bin/python" - <<'PY'
import torch
assert torch.version.hip, "not a ROCm build of PyTorch"
assert torch.cuda.is_available(), "GPU not visible to torch"
print("OK:", torch.__version__, "HIP", torch.version.hip, "|", torch.cuda.get_device_name(0))
PY
echo "==> Done. Activate with: source ${ENV_DIR}/bin/activate"
