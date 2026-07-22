#!/usr/bin/env bash
# Periodically snapshot full-eval progress off the GPU host and push a
# resume-ready ledger to GitHub. Safe to run repeatedly; no-ops when unchanged.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "${REPO_ROOT}"

SSH_HOST="${SSH_HOST:-root@36.150.116.200}"
SSH_PORT="${SSH_PORT:-30147}"
REMOTE_OUT="${REMOTE_OUT:-/root/workspace/Dolphin-v2-ROCm/results/omnidocbench/v16/linux-rocm}"
LOCAL_OUT="${LOCAL_OUT:-${REPO_ROOT}/results/omnidocbench/v16/linux-rocm}"
EVIDENCE_DIR="${EVIDENCE_DIR:-${REPO_ROOT}/evidence/accuracy/full-eval}"
TARGET_PAGES="${TARGET_PAGES:-1651}"
BRANCH="${BRANCH:-feat/rocm-adaptation}"

SSH=(ssh -o ConnectTimeout=25 -o BatchMode=yes -p "${SSH_PORT}" "${SSH_HOST}")
RSYNC_SSH="ssh -o ConnectTimeout=25 -o BatchMode=yes -p ${SSH_PORT}"

mkdir -p "${LOCAL_OUT}/checkpoints" "${LOCAL_OUT}/raw" "${LOCAL_OUT}/markdown" "${EVIDENCE_DIR}"

stamp() { date -u +%Y-%m-%dT%H:%M:%SZ; }
echo "==> [$(stamp)] sync full-eval progress from ${SSH_HOST}:${REMOTE_OUT}"

if ! "${SSH[@]}" "test -f ${REMOTE_OUT}/checkpoints/pages.json"; then
  echo "WARN: remote checkpoint missing; instance may be down or wiped"
  # Still refresh progress.json from local copy if present.
else
  rsync -az -e "${RSYNC_SSH}" \
    "${SSH_HOST}:${REMOTE_OUT}/checkpoints/" "${LOCAL_OUT}/checkpoints/"
  rsync -az -e "${RSYNC_SSH}" \
    "${SSH_HOST}:${REMOTE_OUT}/raw/" "${LOCAL_OUT}/raw/"
  rsync -az -e "${RSYNC_SSH}" \
    "${SSH_HOST}:${REMOTE_OUT}/markdown/" "${LOCAL_OUT}/markdown/"
fi

CP_SRC="${LOCAL_OUT}/checkpoints/pages.json"
if [[ ! -f "${CP_SRC}" ]]; then
  echo "ERROR: no local checkpoint at ${CP_SRC}; nothing to push"
  exit 1
fi

# Tracked resume ledger (results/**/checkpoints/ is gitignored).
cp -f "${CP_SRC}" "${EVIDENCE_DIR}/pages.json"

export REPO_ROOT EVIDENCE_DIR TARGET_PAGES
python3 - <<'PY'
import json
import os
from datetime import datetime, timezone
from pathlib import Path

evidence = Path(os.environ["EVIDENCE_DIR"])
cp = evidence / "pages.json"
target = int(os.environ.get("TARGET_PAGES", "1651"))
recs = json.loads(cp.read_text())
ok = [r for r in recs if r.get("status") == "success"]
fail = [r for r in recs if r.get("status") != "success"]
lat = [r["latency_ms"] for r in ok if isinstance(r.get("latency_ms"), (int, float))]
avg_s = (sum(lat) / len(lat) / 1000.0) if lat else None
remaining = max(target - len(ok), 0)
eta_h = (remaining * avg_s / 3600.0) if avg_s is not None else None
last_ok = ok[-1]["page_id"] if ok else None
progress = {
    "updated_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    "target_pages": target,
    "checkpoint_records": len(recs),
    "success_pages": len(ok),
    "failed_pages": len(fail),
    "progress_pct": round(100.0 * len(ok) / target, 2) if target else None,
    "avg_latency_s": round(avg_s, 2) if avg_s is not None else None,
    "eta_hours_approx": round(eta_h, 2) if eta_h is not None else None,
    "last_success_page_id": last_ok,
    "failed_page_ids": [r.get("page_id") for r in fail],
    "local_out_dir": "results/omnidocbench/v16/linux-rocm",
    "evidence_checkpoint": "evidence/accuracy/full-eval/pages.json",
    "resume_hint": (
        "Restore evidence/accuracy/full-eval/pages.json to "
        "OUT_DIR/checkpoints/pages.json (and rsync markdown/raw if available), "
        "then: OUT_DIR=... IMG_DIR=... bash scripts/resume_eval.sh"
    ),
}
(evidence / "progress.json").write_text(json.dumps(progress, indent=2) + "\n")
print(
    f"ok={progress['success_pages']}/{target} "
    f"fail={progress['failed_pages']} "
    f"avg_s={progress['avg_latency_s']} "
    f"eta_h={progress['eta_hours_approx']}"
)
PY

git checkout "${BRANCH}" >/dev/null 2>&1 || true
git add "${EVIDENCE_DIR}/progress.json" "${EVIDENCE_DIR}/pages.json"

if git diff --cached --quiet; then
  echo "==> [$(stamp)] no progress change; skip commit/push"
  exit 0
fi

OK_COUNT=$(python3 -c "import json; print(json.load(open('${EVIDENCE_DIR}/progress.json'))['success_pages'])")
MSG="chore: snapshot full-eval progress (${OK_COUNT}/${TARGET_PAGES})"

git commit -m "$(cat <<EOF
${MSG}

Periodic resume ledger backup so a killed GPU instance can be continued
from evidence/accuracy/full-eval/pages.json.
EOF
)"

git push -u origin HEAD
echo "==> [$(stamp)] pushed ${MSG}"
