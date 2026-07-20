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
# Baseline collection (frozen config, batch=4)
python eval/run_benchmark.py \
  --img-dir /root/workspace/samples \
  --config eval/configs/smoke.yaml \
  --out evidence/performance/baseline.json \
  --repeats 3 --limit-pages 3 --warmup-pages 1 --label baseline

# Optimized candidate (single switch: max_batch_size=8)
python eval/run_benchmark.py \
  --img-dir /root/workspace/samples \
  --config eval/configs/optimized.yaml \
  --out evidence/performance/optimized.json \
  --repeats 3 --limit-pages 3 --warmup-pages 1 --label optimized
```

## Measured results (2026-07-20, W7900D)

Median across 3 repeats on identical inputs; full protocol and caveats in
[evidence/performance/comparison.md](../evidence/performance/comparison.md):

| Metric | baseline (batch=4) | optimized (batch=8) |
|--------|-------------------:|--------------------:|
| p50 page latency | 41.6 s | 38.0 s (−8.7%) |
| p95 page latency | 42.1 s | 38.1 s (−9.5%) |
| pages/s | 0.025 | 0.028 (+12%) |
| Peak VRAM | 8236 MB | 8342 MB |
| Failures | 0 | 0 |

The batch=8 profile is experimental until OmniDocBench metric parity is
verified; the official evaluation uses the frozen baseline config.

## Forbidden speedups

- shrinking the official page set
- skipping failures silently
- different inputs between baseline and optimized
- dropping model-load time from only one side of a comparison
- hiding accuracy regressions
