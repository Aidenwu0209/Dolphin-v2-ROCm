#!/usr/bin/env bash
# Optional probe: AMD rocm/vllm gfx110X container (does NOT touch the Dolphin venv).
#
# Usage:
#   IMAGE=rocm/vllm:rocm7.12.0_gfx110X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
#     bash scripts/probe_vllm_rocm_container.sh
#
# Archives stdout under reproductions/vllm/rocm-container/ if WRITE_EVIDENCE=1.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE="${IMAGE:-rocm/vllm:rocm7.12.0_gfx110X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0}"
WRITE_EVIDENCE="${WRITE_EVIDENCE:-0}"
OUT_DIR="${OUT_DIR:-${REPO_ROOT}/reproductions/vllm/rocm-container}"

if ! command -v docker >/dev/null 2>&1; then
  echo "ERROR: docker not found on PATH" >&2
  exit 2
fi

echo "==> Probing image: ${IMAGE}"
docker pull "${IMAGE}"

RUN=(docker run --rm
  --device=/dev/kfd --device=/dev/dri
  --group-add=video --ipc=host
  --security-opt seccomp=unconfined
  "${IMAGE}")

echo "==> torch / device"
"${RUN[@]}" python - <<'PY'
import torch
print("torch", torch.__version__)
print("hip", getattr(torch.version, "hip", None))
print("cuda_available", torch.cuda.is_available())
print("device_count", torch.cuda.device_count())
if torch.cuda.is_available():
    print("device0", torch.cuda.get_device_name(0))
PY

echo "==> import vllm"
"${RUN[@]}" python - <<'PY'
import vllm
print("vllm", getattr(vllm, "__version__", "unknown"))
PY

echo "==> Probe finished (engine/Dolphin not exercised by this script)"
if [[ "${WRITE_EVIDENCE}" == "1" ]]; then
  mkdir -p "${OUT_DIR}"
  echo "Set WRITE_EVIDENCE=1 and tee this script's output yourself into ${OUT_DIR}/probe.log"
fi
