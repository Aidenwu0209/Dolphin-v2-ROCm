#!/usr/bin/env bash
# Download the pinned Dolphin-v2 model revision.
#
# Usage: scripts/download_model.sh [DEST_DIR]
# Env:   HF_ENDPOINT can point at a mirror (e.g. https://hf-mirror.com) when
#        huggingface.co is unreachable from the host.
set -euo pipefail

DEST_DIR="${1:-/root/workspace/models/Dolphin-v2}"
MODEL_REPO="ByteDance/Dolphin-v2"
MODEL_REVISION="c37c62768c644bb594da4283149c627765aa80f3"
ENV_DIR="${ENV_DIR:-/root/workspace/envs/dolphin}"

echo "==> Downloading ${MODEL_REPO}@${MODEL_REVISION} to ${DEST_DIR}"
"${ENV_DIR}/bin/hf" download "${MODEL_REPO}" \
    --revision "${MODEL_REVISION}" \
    --local-dir "${DEST_DIR}" \
    --exclude "zk.log"

echo "==> Verifying weight files"
ls -l "${DEST_DIR}"/*.safetensors
"${ENV_DIR}/bin/python" - "$DEST_DIR" <<'PY'
import hashlib
import json
import sys
from pathlib import Path

dest = Path(sys.argv[1])
digests = {}
for name in ("config.json", "model.safetensors.index.json"):
    payload = (dest / name).read_bytes()
    digests[name] = "sha256:" + hashlib.sha256(payload).hexdigest()
print(json.dumps(digests, indent=2))
PY
