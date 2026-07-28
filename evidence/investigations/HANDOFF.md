# Handoff — Dolphin-v2 ROCm / OmniDocBench / 5070 Ti parity

Date: 2026-07-28. Purpose: hand off to another agent. Read this before acting.

Repo: `/Users/wu/Dolphin-v2-ROCm`
Remote: `Aidenwu0209/Dolphin-v2-ROCm`
Policy: `AGENTS.md` — no secrets/weights/dataset in git; no upstream Issues without user approval; feature work on feat branches; do not auto-merge to `main`.

---

## 1. Mission (original)

Adapt ByteDance Dolphin-v2 for AMD ROCm (W7900D / gfx1100 / ROCm 7.2), produce reproducible OmniDocBench v1.6 evidence, then peel root causes and use NVIDIA 5070 Ti CUDA parity to separate AMD adaptation bugs vs model/scorer limits.

---

## 2. What is already DONE

### Phase A — ROCm adaptation (merged)

- **PR #1 merged** to `main` (`afc80bd`).
- Full infer: **1651 pages, 1649 success / 2 soft-timeout / fallback=0** (~57h).
- Soft-timeout pages:
  - `jiaocaineedrop_jiaocai_needrop_en_3063` (40 elems, ~2503s vs 1800s budget)
  - `newspaper_b615618f3cdb0f2c13ffb5865dea799c_1` (121 elems, ~1977s)
- **Critical bug fixed earlier:** first “full” `metric_result.json` was actually canary (`page_count=20`) after scorer died on `ulimit -n=1024`; watcher copied stale canary by mtime. Real full metrics rescored with raised ulimit / `MATCH_WORKERS=4`. Stale copy under `evidence/accuracy/full-eval/_stale_canary_copy/`.
- Headline full metrics (approx):
  - text Edit_dist **0.079**
  - formula Edit_dist **0.158**, CDM **0.914**
  - table TEDS **0.719**
  - reading_order **0.149**
- Perf: batch 4→8 **+12% pages/s** (formal 3-repeat). Full accuracy under batch=8 **not** re-scored.
- vLLM prebuilt wheels: **known-incompatible** (documented; **do not file as defect Issue**). Next probe: AMD `rocm/vllm` gfx110X container.
- Delivery report: `docs/delivery-report.md`.
- Scripts hardened: `run_full_score.sh`, `run_full_eval.sh` (archive-before-score), `finalize_result_dir.sh`.

### Phase B — Offline root-cause P0 (implemented on branch)

- Branch: **`feat/rootcause-offline-p0`** (tracks `origin/feat/rootcause-offline-p0`).
- **PR #2 open:** https://github.com/Aidenwu0209/Dolphin-v2-ROCm/pull/2
  Title: Offline root-cause scaffolds and 5070 Ti page lists.
  Includes earlier vLLM status rewrite, offline scaffolds, and the fresh AMD
  validation commit. **Not merged yet** — check live CI and wait for user OK.
- Tip pushed to remote: `1491184` (`Validate AMD runtime and isolate TEDS join failures`).
- **Included in `1491184`:**
  - `evidence/investigations/three-findings/NOTES.md` (important analysis)
  - `evidence/investigations/INDEX.md` (updated)
  - `.gitignore` adds `.local-cache/`
  - release-contract completeness fix + tests
  - deterministic severe-union / research-report page builders + lists
  - TEDS isolation driver + tests
  - fresh AMD runtime/smoke and fallback47/strict55 evidence packages

### Phase C — Three-finding offline probe (done and pushed)

Full write-up: `evidence/investigations/three-findings/NOTES.md`
Used pinned GT: `.local-cache/OmniDocBench.json` (rev `aa1ee96…` from `runtime-manifest.json`; **gitignored**, re-download if missing).

**Finding 1 — TEDS two layers (revised):**
- Layer A: 60/665 tables fail with `AssertionError: can only join a started process` (55 unique images). Scorer multiprocessing bug. Canary reproduced (workers=13). Full run used `teds_workers=4`.
- **Do not claim free lunch on ALL TEDS:** fixing join likely moves headline TEDS only ~**+0.00–0.03**.
- `layout_hard` TEDS **0.21 is misleading**: only 10 tables; **8 on join-error pages** (excluded from mean); 2 scored survivors ≈0.21.
- Real-volume weak buckets: **newspaper** (69 tables, TEDS 0.52), **table_hard** (136, 0.70), **note** (37, 0.54).

**Finding 2 — “cross-modal weak” is a tiny overlapping cluster:**
- historical n=5, handwriting n=2, fuzzy_content n=4, geometric n=13, traditional_chinese n=13.
- Labels overlap heavily; union ~**20 unique hard pages**. Likely model/input difficulty, not AMD. CUDA parity on this union is the falsifier.

**Finding 3 — research_report text good / RO bad:**
- text Edit_dist **0.025** (best DS), reading_order **0.325** (near-worst).
- Dual-pane brokerage layouts (eastmoney/yanbao). Case study: OCR matches; order differs (headers early; related-reports split into 5 `reference`s; column traversal ≠ GT).
- Mechanism: text metric is match-then-compare per block; RO compares serialized order stream.

### Phase D — Fresh AMD SSH revalidation and TEDS isolation (done)

- Fresh host doctor: **PASS** on ROCm 7.2.1 / gfx1100 / 48 GB VRAM.
- Model snapshot verified before loading: 14 top-level files,
  7,520,906,987 bytes, two weight shards, and 824 indexed weights.
- Smoke9: **9/9 success**, zero failures/skips/missing records, and zero
  checkpoint/distorted/raw fallbacks; 2,605 s total.
- The smoke summary honestly retains `dataset_revision=null`; exact input
  revision and image hashes are independently pinned by Hugging Face sidecars.
- Recovered the eight TEDS predictions absent from the retained archive:
  **8/8 success**, zero failures/missing records, and zero fallback in all
  representations.
- Scorer-only fallback47: 47 pages / 86 tables, workers=1, three repeats, all
  join errors gone; sample/page TEDS exactly stable at
  0.7001473590 / 0.8230421462.
- Hybrid strict55 (47 historical + 8 fresh): 55 pages / 94 tables, workers=1,
  three repeats, zero TEDS error/timeout/exception/join errors; sample/page
  scores exactly stable at 0.7205098758 / 0.8399679331.
- Page matching still emitted independent `latex_to_text` `os.fork/filelock`
  warnings (strict55 counts: 47 / 33 / 51). Therefore the conclusion is limited
  to the TEDS process-lifecycle layer; do not claim that the whole scorer is
  concurrency-clean or infer a 1,651-page headline gain.
- Evidence:
  - `evidence/investigations/amd-runtime-smoke/amd-ssh-20260728-rocm72-gfx1100-r1/`
  - `evidence/investigations/teds-join/amd-ssh-20260728-w1-fallback47/`
  - `evidence/investigations/teds-join/amd-ssh-20260728-w1-strict55-hybrid/`
- The evidence and local hardening were committed and pushed in `1491184`.
  No merge or upstream Issue was performed.

### Phase E — 5070 Ti Windows host (partially set up, smoke NOT done)

Host: Windows 10 desktop, RTX 5070 Ti 16GB, driver 596.36 / CUDA 13.2 reported by nvidia-smi.
**WSL not installed.** Native Windows CUDA path only.

**SSH credentials:** Connection details and credentials are session-only
secrets. Never record or commit them; obtain them directly from the user when
access is authorized.
- Tailscale node name: `5070ti`. Last successful ping with closed port 22: host online but **OpenSSH Server often not running after reboot**.

**Remote workspace (create/use only under this tree):**
```text
%USERPROFILE%\Dolphin-v2-ROCm-cuda5070ti\
  workspace\Dolphin-v2-ROCm\     # feat/rootcause-offline-p0 via git bundle (GitHub clone failed)
  conda-env\                     # python 3.12, torch 2.11.0+cu128, transformers 4.51.0, dolphin-v2-rocm editable
  models\Dolphin-v2\             # ByteDance/Dolphin-v2 @ c37c627… (~7.5GB)
  data\OmniDocBench\             # junction → D:\OCR\datasets\omnidocbench (~1355 images — NOT full 1651)
  evidence\                      # host-local logs
  workspace\tools\               # Sysinternals PsTools / PsExec64.exe
```

**Critical Windows/CUDA lesson:**
- SSH runs in **Session 0**. First smoke loaded shards then hung; zombie `python` hard to kill; `nvidia-smi` can hang.
- Workaround: **PsExec `-i 1`** into console session (`workspace\fix_ssh_smoke.ps1`, `run_smoke2.ps1`).
- Reboot via SSH eventually worked once; after reboot Tailscale came back but **sshd stayed down** repeatedly (2026-07-25 / 07-26 / 07-28 probes: ping OK, port 22 timeout).

**Smoke status:** NOT successfully completed. No formal CUDA metrics yet.

Docs on host caveats: `evidence/investigations/cuda5070ti-matrix/HOST_WORKSPACE.md`

---

## 3. Key paths (local Mac repo)

| Path | Why |
| --- | --- |
| `AGENTS.md` | Safety / scope |
| `runtime-manifest.json` | Model + dataset pins |
| `docs/plans/2026-07-23-rootcause-and-5070ti-matrix.md` | Master plan |
| `docs/upstream-drafts/` | Unpublished Issue drafts (CDM, TEDS) |
| `docs/upstream-contributions.md` | No publish without approval |
| `evidence/investigations/INDEX.md` | Investigation index |
| `evidence/investigations/three-findings/NOTES.md` | Best analysis so far |
| `evidence/investigations/teds-join/` | TEDS inventory |
| `evidence/investigations/amd-runtime-smoke/` | Fresh ROCm 7.2 doctor + smoke9 evidence |
| `evidence/investigations/cuda5070ti-matrix/` | 5070 Ti runbook |
| `eval/configs/cuda5070ti_*.txt` | timeout / weak / teds page lists |
| `evidence/accuracy/full-eval/` | Real full metrics + pages.json + failures |
| `results/omnidocbench/v16/linux-rocm/raw/` | Partial pred sync (~useful for RO case studies) |
| `.local-cache/OmniDocBench.json` | GT only (gitignored) |

Page lists note: `cuda5070ti_weak_pages.txt` remains the legacy
canary∪timeout heuristic. Use the explicit `severe-union` and
`research-report-dual` profiles in `scripts/build_weak_page_list.py`; the
pinned lists contain 19 and 10 pages and rebuild exactly from GT.

---

## 4. What the NEXT agent should do

### Immediate (5070 Ti)

1. Confirm `sshd` is listening using session-only connection details obtained directly from the user.
2. Operate **only** under `Dolphin-v2-ROCm-cuda5070ti\`.
3. Kill hung python; launch smoke via PsExec interactive session (reuse `fix_ssh_smoke.ps1` / `run_smoke2.ps1`).
4. Success criteria: `evidence\smoke_console.log` shows CUDA tensor OK + 1-page infer + `_run_stats.json`.
5. Then: timeout-2 list → data-driven hard-page union (~20) + ~10 eastmoney dual-pane RO pages.
6. Record torch/CUDA provenance; **do not claim parity until runs exist**.
7. Host dataset is ~1355 images — verify revision vs pin `aa1ee96…` before formal compares; may need full 1651 images.

### Local / release follow-up

1. Check PR #2 CI for commit `1491184`; address only actionable failures.
2. Merge PR #2 only with user OK.
3. Optional stronger control: run the same hybrid55 prediction set with
   `teds_workers=4`; workers=1 strict55 is already complete.
4. Optional: local Ubuntu IM6 CDM/`magick` repro → upgrade Issue draft (still
   no publish without approval).

### Upstream (quality bar)

- CDM/`magick`: draft ready-ish, local repro, no GPU.
- TEDS join: draft skeleton; prefer confirm after `n_jobs=1` / CUDA scorer-only.
- Soft-timeouts / weak buckets: **no defect Issue** until CUDA parity.
- vLLM wheels: **do not file**.

---

## 5. Parity confounds (do not ignore)

- Torch skew: Windows `2.11.0+cu128` (Blackwell) vs ROCm `2.7.1+rocm7.2.0`; transformers pinned `4.51.0` both sides.
- Scorer on native Windows unproven — prefer Windows for **inference** parity; Linux for scorer isolation.
- Platform label in pipeline still defaults `linux-rocm` (cosmetic).

---

## 6. Explicit non-goals / safety

- Do not commit credentials, connection details, weights, OmniDocBench images,
  or SSH helpers containing secrets.
- Do not use `HSA_OVERRIDE_GFX_VERSION` as default.
- Do not publish upstream Issues/PRs without explicit user approval.
- Do not delete unknown dirs on remote hosts.
- The fresh AMD evidence is synced locally; remote availability can still
  change, so never rely on the live instance as the only copy.

---

## 7. Suggested first commands for next agent

```bash
# Local
cd /Users/wu/Dolphin-v2-ROCm
git status -sb
git log --oneline -5
# Read: evidence/investigations/three-findings/NOTES.md
# Read: evidence/investigations/cuda5070ti-matrix/HOST_WORKSPACE.md

# Remote (after sshd is up)
# Use session-only SSH connection details obtained directly from the user.
# Then run PsExec-based smoke under Dolphin-v2-ROCm-cuda5070ti only
```

---

## 8. Chat timeline (compressed)

1. Full ROCm eval + metrics bugfix + delivery + merge PR #1.
2. Plan root-cause ladder + 5070 Ti matrix; AMD down → offline P0 on `feat/rootcause-offline-p0`, PR #2.
3. User authorized operating their GitHub repo; then gave 5070 Ti SSH credentials.
4. Built Windows workspace, conda, torch cu128, downloaded model; Session-0 CUDA hang; PsExec path; reboot; sshd repeatedly unavailable.
5. Offline three-finding probe with GT JSON; corrected overconfident TEDS/weak-bucket claims.
6. User asked to resume 5070 Ti; host pingable but port 22 closed through 2026-07-28 morning.
7. Radeon Cloud SSH was restored; exact ROCm model/runtime and smoke9 were
   revalidated.
8. The missing eight TEDS predictions were recovered, then fallback47 and
   hybrid strict55 workers=1 experiments passed three repeats with explicit
   concurrency-warning limits.
9. This handoff was refreshed for the successor agent.
