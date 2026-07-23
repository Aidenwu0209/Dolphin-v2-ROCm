# CUDA 5070 Ti parity matrix (scaffold)

AMD host is down; this directory holds lists and a runbook for when a 5070 Ti
machine is available. Default scope is **not** full 1651.

## Page lists (repo)

| File | Purpose | Count |
| --- | --- | --- |
| `eval/configs/cuda5070ti_timeout_pages.txt` | Soft-timeout isolation | 2 |
| `eval/configs/canary_pages.txt` | Smoke / stratified canary | 20 |
| `eval/configs/cuda5070ti_weak_pages.txt` | Starter weak set = canary ∪ timeout | 22 |
| `eval/configs/cuda5070ti_teds_error_pages.txt` | Scorer-only TEDS isolation images | 55 |

Expand `cuda5070ti_weak_pages.txt` later with GT bucket filters when
`OmniDocBench.json` is mounted (script: `scripts/build_weak_page_list.py`).

## Recommended order (when host is up)

1. **Smoke 9** — subset of canary (or full canary 20 if time allows)
2. **Timeout 2** — same soft-timeout budget as ROCm full-eval
3. **Weak 22+** — starter list; optionally expand to 36–48 via GT attrs
4. **Scorer-only TEDS** — re-score existing ROCm preds using the 55-image list
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
