# Troubleshooting

## Doctor FAIL: GPU not visible

- Confirm `rocminfo` lists the device and `gfx1100`
- Confirm `rocm-smi` shows the card
- Confirm the venv PyTorch build has non-empty `torch.version.hip`
- Reinstall using `scripts/setup_model_env.sh` (ROCm wheel index)

## Slow first page

Cold start includes model load and first-graph work. Benchmarks separate
`model_load_seconds` and first-page latency from steady-state page latency.

## Empty markdown marked failed

This is intentional. Empty outputs cannot count as success for smoke,
canary, or official evaluation.

## Resume reprocessing pages

Resume only skips `status=success`. Failed/timeout pages run again. To force a
full redo, use a fresh output directory (do not delete unrelated data).

## Hugging Face download failures

Set `HF_ENDPOINT` to a reachable mirror and retry
`scripts/download_model.sh`.

## Scorer import errors

Install OmniDocBench into the eval venv via `scripts/setup_eval_env.sh`.
Entrypoint names vary by revision; see `scripts/run_full_eval.sh`.

## Do not

- Override GFX version globally to “make it work”
- Delete unknown directories under `/root` to free space without approval
- Upgrade system ROCm/drivers mid-run without approval
