# Evaluation

## Adapter contract

```python
from eval.adapter import run_adapter

summary = run_adapter(img_dir, out_dir, platform="linux-rocm", config=config)
```

`summary` always includes: `total`, `succeeded`, `failed`, `skipped`,
`fallback`, timestamps, `duration_seconds`, `backend`, `platform`,
`model_revision`, `dataset_revision`, `output_dir`.

Markdown predictions are written as `markdown/<image_stem>.md`.

## Run tiers

| Tier | Script | Config | Purpose |
|------|--------|--------|---------|
| Smoke | `scripts/run_smoke.sh` | `eval/configs/smoke.yaml` | Multi-type sample pages |
| Canary | `scripts/run_canary.sh` | `eval/configs/canary.yaml` | Fixed subset before full |
| Full | `scripts/run_full_eval.sh` | `eval/configs/omnidocbench_v16.yaml` | Entire pinned manifest |
| Resume | `scripts/resume_eval.sh` | same as full | Continue from checkpoint |

Official published runs must keep `limit_pages: null` and `fallback: 0`.

## Resume semantics

Checkpoints live at `<out>/checkpoints/pages.json`. Re-running the same
`out_dir` skips pages with `status=success`. Failures are listed in
`failures.json` and may be retried by removing their checkpoint entries or
re-running after fixing the cause.

## Scoring

Inference and scoring are separated:

1. Produce predictions with the model environment.
2. Score with the pinned OmniDocBench evaluator in the eval environment.

```bash
SCORE=1 scripts/run_full_eval.sh
```

## Release artifacts

Under `results/omnidocbench/v16/linux-rocm/`:

- `metric_result.json`
- `run_summary.json`
- `_run_stats.json`
- `failures.json`
- `provenance.json`
- `runtime_attestation.json`
- `model_card.json`
- `performance.json`

Validate with:

```bash
python eval/release_contract.py results/omnidocbench/v16/linux-rocm
```

## Page count policy

Expected OmniDocBench v1.6 size is often cited as 1651 pages. The authoritative
count is the pinned revision manifest. Never fabricate 1651 if the pinned
revision differs; document the actual count and revision instead.
