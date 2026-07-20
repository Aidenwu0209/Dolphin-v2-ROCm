# Performance

## Protocol

1. Freeze an unoptimized Transformers ROCm baseline.
2. Fix model revision, input set, preprocessing, generation params, dtype,
   batch size, warmup, and repeat count (≥3).
3. Report median across repeats for latency and pages/s.
4. Enable one optimization switch at a time.
5. Re-check output integrity / accuracy before accepting a win.
6. Record negative or null results too.

## Metrics

- model load time
- first-page latency
- per-page mean / p50 / p95
- pages/s
- total wall time
- peak VRAM
- GPU/CPU utilization (best effort via `rocm-smi` / `psutil`)
- failure rate
- accuracy deltas when available

## Commands

```bash
# Example baseline collection
python eval/run_benchmark.py \
  --input /root/workspace/samples \
  --config eval/configs/smoke.yaml \
  --out evidence/performance/baseline.json \
  --repeats 3
```

Comparison narrative lives in `evidence/performance/comparison.md`.

## Forbidden speedups

- shrinking the official page set
- skipping failures silently
- different inputs between baseline and optimized
- dropping model-load time from only one side of a comparison
- hiding accuracy regressions
