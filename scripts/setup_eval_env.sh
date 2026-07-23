#!/usr/bin/env bash
# Set up the isolated OmniDocBench evaluation / scoring environment.
#
# Usage: scripts/setup_eval_env.sh [ENV_DIR]
# Default ENV_DIR: /root/workspace/envs/odb-eval
#
# Prefers Python 3.11 when available; falls back to 3.12 with a recorded note
# (see evidence/environments/ and docs/installation.md).
set -euo pipefail

ENV_DIR="${1:-/root/workspace/envs/odb-eval}"
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OMNIDOCBENCH_SRC="${OMNIDOCBENCH_SRC:-/root/workspace/OmniDocBench}"

if command -v python3.11 >/dev/null 2>&1; then
  PYTHON_BIN=python3.11
elif command -v python3.12 >/dev/null 2>&1; then
  PYTHON_BIN=python3.12
  echo "WARN: python3.11 not found; using python3.12 for the eval environment"
else
  echo "ERROR: need python3.11 or python3.12" >&2
  exit 1
fi

echo "==> Creating eval venv at ${ENV_DIR} with ${PYTHON_BIN}"
"${PYTHON_BIN}" -m venv "${ENV_DIR}"
"${ENV_DIR}/bin/pip" install --upgrade pip

echo "==> Installing OmniDocBench scorer from ${OMNIDOCBENCH_SRC}"
if [[ ! -d "${OMNIDOCBENCH_SRC}" ]]; then
  echo "ERROR: OmniDocBench source not found at ${OMNIDOCBENCH_SRC}" >&2
  echo "Clone https://github.com/opendatalab/OmniDocBench and set OMNIDOCBENCH_SRC" >&2
  exit 1
fi

"${ENV_DIR}/bin/pip" install -e "${OMNIDOCBENCH_SRC}"
"${ENV_DIR}/bin/pip" install pyyaml pillow numpy jsonschema

echo "==> Scorer import check"
"${ENV_DIR}/bin/python" - <<'PY'
import importlib
for name in ("omnidocbench", "omnidocbench_eval"):
    try:
        importlib.import_module(name)
        print("OK: imported", name)
        break
    except ImportError:
        continue
else:
    # Package layout varies by OmniDocBench revision; surface what is available.
    import pkgutil
    print("WARN: could not import omnidocbench*; listing top-level packages:")
    print([m.name for m in pkgutil.iter_modules()][:40])
PY

echo "==> Done. Activate with: source ${ENV_DIR}/bin/activate"
