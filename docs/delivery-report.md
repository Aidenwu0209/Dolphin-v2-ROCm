# Final delivery report (§十九)

Generated 2026-07-23. Feature work remains on `feat/rocm-adaptation` (not merged to `main`).

## 1. Branch name

`feat/rocm-adaptation`

Evidence: `git branch -vv` → tracks `origin/feat/rocm-adaptation`.

## 2. Latest commit

See repository HEAD after the wrap-up push that lands this file. Prior verified tip before this report commit: `6f1566f` (scorer hardening). Full-metric archive commit updates HEAD.

## 3. GitHub branch link

https://github.com/Aidenwu0209/Dolphin-v2-ROCm/tree/feat/rocm-adaptation

## 4. Actual server environment summary

From [`evidence/environments/runtime_attestation.json`](../evidence/environments/runtime_attestation.json) (`overall=PASS`):

| Item | Value |
|------|-------|
| GPU | AMD Radeon PRO W7900D, gfx1100, 48 GB |
| CPU | AMD EPYC 9334 ×128 threads |
| RAM | ~504 GB |
| OS | Ubuntu 24.04.3 LTS |
| ROCm | 7.2.0 |
| amdgpu | 6.14.14 |
| PyTorch | 2.7.1+rocm7.2.0 |
| Transformers | 4.51.0 (pinned via runtime manifest / provenance) |

SSH endpoint used for GPU execution only; **not** committed.

## 5. Install commands

```bash
git clone https://github.com/Aidenwu0209/Dolphin-v2-ROCm.git
cd Dolphin-v2-ROCm
git checkout feat/rocm-adaptation
scripts/setup_model_env.sh /root/workspace/envs/dolphin
source /root/workspace/envs/dolphin/bin/activate
scripts/download_model.sh /root/workspace/models/Dolphin-v2
scripts/doctor.sh
```

Docs: [`docs/installation.md`](installation.md).

## 6. Smoke test command and result

```bash
scripts/run_smoke.sh
```

Result: **9/9 success, fallback=0** — [`evidence/accuracy/smoke_summary.md`](../evidence/accuracy/smoke_summary.md), [`evidence/accuracy/smoke/`](../evidence/accuracy/smoke/).

## 7. Full eval command and result

Inference:

```bash
scripts/run_full_eval.sh
# interrupt-safe:
OUT_DIR=results/omnidocbench/v16/linux-rocm IMG_DIR=... bash scripts/resume_eval.sh
```

Official scoring (after inference):

```bash
MATCH_WORKERS=4 bash scripts/run_full_score.sh
```

Result ([`evidence/accuracy/run_summary.json`](../evidence/accuracy/run_summary.json)):

| Field | Value |
|-------|-------|
| total / succeeded / failed / fallback | 1651 / 1649 / 2 / 0 |
| started_at → finished_at | 2026-07-20T06:24:55Z → 2026-07-22T15:45:38Z |
| duration_seconds | 206443.2 |
| model_revision | `c37c62768c644bb594da4283149c627765aa80f3` |
| dataset_revision | `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec` |
| scorer page_count | **1651** ([`scorer_run_summary.json`](../evidence/accuracy/full-eval/scorer_run_summary.json)) |

Release contract: `python eval/release_contract.py results/omnidocbench/v16/linux-rocm` → **PASS**.

## 8. Main OmniDocBench metrics

Source: [`evidence/accuracy/metric_result.json`](../evidence/accuracy/metric_result.json) (full set; **not** the quarantined canary copy under `_stale_canary_copy/`).

| Metric | Value |
|--------|------:|
| Text block Edit_dist ↓ | 0.0794 |
| Display formula Edit_dist ↓ | 0.1579 |
| Display formula CDM ↑ | 0.9137 |
| Table TEDS ↑ | 0.7188 |
| Table Edit_dist ↓ | 0.1392 |
| Reading order Edit_dist ↓ | 0.1487 |

Summary: [`evidence/accuracy/full-eval/full_eval_summary.md`](../evidence/accuracy/full-eval/full_eval_summary.md).

## 9. Baseline vs optimized performance

Formal 3-repeat protocol on identical 3 smoke pages — [`evidence/performance/comparison.md`](../evidence/performance/comparison.md):

| Metric | baseline (batch=4) | optimized (batch=8) | delta |
|--------|-------------------:|--------------------:|------:|
| p50 page latency (s) | 41.6 | 38.0 | −8.7% |
| p95 page latency (s) | 42.1 | 38.1 | −9.5% |
| pages/s | 0.025 | 0.028 | **+12%** |
| Peak VRAM (MB) | 8236 | 8342 | +1.3% |
| Failures | 0/9 | 0/9 | — |

JSON: [`baseline.json`](../evidence/performance/baseline.json), [`optimized.json`](../evidence/performance/optimized.json).

Accuracy parity for batch=8 on the **full** 1651-page set was **not** re-run (deferred in [`ROADMAP.md`](../ROADMAP.md)).

## 10. vLLM status

**Known-incompatible via prebuilt wheels** on ROCm 7.2 / gfx1100.

Evidence: [`evidence/compatibility/vllm-rocm72-gfx1100.md`](../evidence/compatibility/vllm-rocm72-gfx1100.md) + 3× engine-init failures under [`reproductions/vllm/no-rocm-wheels/`](../reproductions/vllm/no-rocm-wheels/).

No upstream Issue drafted (documented packaging scope, not a Dolphin defect).

## 11. Known issues

- Soft timeouts (1800s) on 2 full-eval pages — recorded in [`failures.json`](../evidence/accuracy/full-eval/failures.json).
- First full scorer attempt failed with `OSError: Too many open files` under `ulimit -n=1024`; watcher briefly copied canary metrics. Fixed by [`scripts/run_full_score.sh`](../scripts/run_full_score.sh); audit copy in [`_stale_canary_copy/`](../evidence/accuracy/full-eval/_stale_canary_copy/).
- `latex_to_text` / `os.fork` warnings during CDM scoring (scorer still completed).
- Flash-Attention 2 not assumed; baseline uses SDPA.
- Eval env fell back to Python 3.10 where 3.11 was unavailable.

## 12. Issue draft list

None published. No high-quality upstream drafts retained under `evidence/upstream-issues/` beyond the empty placeholder (vLLM judged non-actionable as packaging scope). Routing policy: [`docs/upstream-contributions.md`](upstream-contributions.md).

## 13. CI status

| Workflow | Latest on `feat/rocm-adaptation` (pre-this-report) |
|----------|---------------------------------------------------|
| `ci` | success (`6f1566f`) |
| `evidence-validation` | success (`6f1566f`) |

Local: `pytest` → **40 passed**; `ruff check` clean on prior tip.

## 14. Incomplete items and reasons

| Item | Reason |
|------|--------|
| Merge to `main` | Explicitly out of scope without user approval |
| Publish upstream Issues | Requires user confirmation; no qualifying drafts |
| batch=8 full-set metric parity | Deferred (`ROADMAP.md`); throughput verified only |
| ROCm vLLM container / source build | Deferred (`ROADMAP.md`); prebuilt path ruled out |
| Commit full `markdown/` dumps | Intentionally gitignored (~350MB+); kept on GPU host + local backup |

## 15. Need user confirmation to publish upstream Issues?

**Yes.** No Issues should be filed without explicit approval. Current recommendation: **do not file** the vLLM prebuilt-wheel finding as a defect Issue.

## 16. `main` kept unmerged?

**Yes.** `main` remains at bootstrap `3894162`; `feat/rocm-adaptation` is **not** an ancestor of `main` (`git merge-base --is-ancestor HEAD main` fails).
