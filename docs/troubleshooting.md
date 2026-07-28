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

## CDM = 0.0 with `magick: not found`

The OmniDocBench CDM stage shells out to ImageMagick 7's `magick` CLI to
rasterize rendered formula PDFs. Ubuntu 24.04 ships ImageMagick 6, which only
provides `convert`. Without `magick`, every formula render fails and CDM
silently scores 0.0 while the run still exits 0.

Fix (IM6 hosts):

```bash
cat > /usr/local/bin/magick <<'EOF'
#!/bin/sh
exec convert "$@"
EOF
chmod +x /usr/local/bin/magick
```

Verified on this host: canary CDM went from 0.0 to 0.884 after the shim.

## `latex_to_text failed: os.fork is unsafe while filelock is ...`

`safe_latex_to_text` in the scorer forks worker processes; with filelock
3.31.x on Python 3.10 the forked worker can die and each affected formula
falls back to raw LaTeX after a 30 s timeout. Scoring completes and Edit_dist
remains valid, but expect warnings and slower text preprocessing. Timeout
inputs are logged under `OmniDocBench/logs/timeout_inputs/`.

## Soft-timeout pages on full-eval (2 / 1651)

Full infer completed with two soft-timeouts (no fallback success):

- `jiaocaineedrop_jiaocai_needrop_en_3063.jpg`
- `newspaper_b615618f3cdb0f2c13ffb5865dea799c_1.jpg`

These are **not** yet classified as AMD-specific. Prefer a CUDA 5070 Ti
parity run on `eval/configs/cuda5070ti_timeout_pages.txt` before upstream or
driver conclusions. Notes: `evidence/investigations/soft-timeout/NOTES.md`.

## TEDS `AssertionError: can only join a started process`

Full-eval table TEDS reported 60 error cases (55 unique images), all with this
reason. Inventory: `evidence/investigations/teds-join/`. Prefer scorer-only
isolation (`n_jobs` matrix / CUDA host) before filing OmniDocBench.

## Do not

- Override GFX version globally to “make it work”
- Delete unknown directories under `/root` to free space without approval
- Upgrade system ROCm/drivers mid-run without approval
- Publish upstream Issues/PRs without explicit approval (`docs/upstream-contributions.md`)
