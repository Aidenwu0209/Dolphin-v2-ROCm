# CUDA 5070 Ti parity matrix

The AMD baseline has been revalidated. This directory holds fixed lists and a
runbook for completing CUDA parity when the 5070 Ti SSH service is available.
Default scope is **not** full 1651.

## Page lists (repo)

| File | Purpose | Count |
| --- | --- | --- |
| `eval/configs/cuda5070ti_timeout_pages.txt` | Soft-timeout isolation | 2 |
| `eval/configs/canary_pages.txt` | Smoke / stratified canary | 20 |
| `eval/configs/cuda5070ti_weak_pages.txt` | Starter weak set = canary ∪ timeout | 22 |
| `eval/configs/cuda5070ti_severe_union_pages.txt` | Data-driven severe-tag union | 19 |
| `eval/configs/cuda5070ti_research_report_dual_pages.txt` | Brokerage dual-pane reading-order set | 10 |
| `eval/configs/cuda5070ti_teds_error_pages.txt` | Scorer-only TEDS isolation images | 55 |

The two explicit profiles rebuild deterministically from the pinned GT with
`scripts/build_weak_page_list.py`. Keep `cuda5070ti_weak_pages.txt` as the
legacy canary∪timeout heuristic.

## Recommended order (when host is up)

1. **Smoke 9** — subset of canary (or full canary 20 if time allows)
2. **Timeout 2** — same soft-timeout budget as ROCm full-eval
3. **Severe union 19** — historical, handwriting, deformation, and fuzzy pages
4. **Research-report dual 10** — text-versus-reading-order parity
5. **Scorer-only TEDS** — re-score existing ROCm preds using the 55-image list
   (no need to re-infer all 55 if preds already exist). Note: the available
   5070 Ti host is **native Windows**; the OmniDocBench scorer stack there is
   unproven, so prefer running this isolation on a Linux host and keep the
   Windows box for inference parity (see `HOST_WORKSPACE.md`)

## Pin (parity contract)

- Same model revision as `runtime-manifest.json`
- Same OmniDocBench v1.6 GT / scorer pin
- `batch_size=4` for formal compare (batch=8 is a separate perf track)
- Record torch/CUDA versions in a local `provenance.json` under this directory
  (do not commit secrets or SSH endpoints)

## Do not

- Claim CUDA results until runs exist
- File AMD-specific Issues based on ROCm-only soft-timeouts
- Commit weights, dataset images, or private paths
