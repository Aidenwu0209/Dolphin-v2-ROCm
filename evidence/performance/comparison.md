# Performance comparison: baseline vs optimized (formal 3-repeat)

Date: 2026-07-20 (UTC). Host: AMD Radeon PRO W7900D, gfx1100, ROCm 7.2.0,
PyTorch 2.7.1+rocm7.2.0, Transformers 4.51.0.

## Protocol

- Same input set: first 3 smoke pages (`page_0.jpeg`, `page_1.png`, `page_2.jpeg`)
- Same model revision `c37c62768c644bb594da4283149c627765aa80f3`, BF16, SDPA,
  `resize_max_size=1600`, `max_new_tokens=4096`, greedy decoding
- Each run: fresh process, model load measured, 1 cold first-page measurement,
  1 warmup page, then 3 full repeats; medians reported across repeats
- GPU/CPU utilization sampled via `rocm-smi` / `psutil` every 2 s
- No other GPU jobs during measurement (full OmniDocBench eval was paused at a
  page boundary and resumed afterward)
- Collected by `eval/run_benchmark.py`; raw JSON:
  [baseline.json](baseline.json), [optimized.json](optimized.json)

## Single switch under test

`max_batch_size: 4 -> 8` (stage-2 element batching; `eval/configs/optimized.yaml`,
flag `optimization_flags.larger_element_batch`). Everything else identical.
Rollback = use `eval/configs/smoke.yaml` / baseline configs (batch 4).

## Results (median across 3 repeats)

| Metric | baseline (batch=4) | optimized (batch=8) | delta |
|--------|-------------------:|--------------------:|------:|
| Model load (s) | 6.82 | 6.93 | +1.6% |
| First page, cold (s) | 36.5 | 94.5* | see note |
| p50 page latency (s) | 41.6 | 38.0 | −8.7% |
| p95 page latency (s) | 42.1 | 38.1 | −9.5% |
| Mean page latency (s) | 39.8 | 35.8** | −10% |
| pages/s | 0.025 | 0.028 | +12% |
| Wall per repeat (s) | 119.5 | 107.3 | −10% |
| Peak VRAM (MB) | 8236 | 8342 | +1.3% |
| GPU busy mean (%) | 94.2–94.4 | 94.5–98.1 | ~flat |
| Failures | 0/9 | 0/9 | — |

\* The optimized run's cold first page and first repeat show one-off slow pages
(88.5 s, 99.9 s in rep0) consistent with first-use kernel/graph work for the
new batch shape; reps 1–2 are stable at 31.2/38.1/38.0 s. Medians across
repeats absorb this, but the cold-start cost is disclosed here rather than
hidden.

\** Mean computed from per-repeat means (37.9/35.8/35.8 → median 35.8).

## Output integrity

Both variants produced non-empty markdown for all pages, 0 failures, and
`fallback=0`. Accuracy deltas on OmniDocBench metrics have not been measured
for batch=8 yet; the official full evaluation runs with the frozen baseline
config (`max_batch_size: 4`). batch=8 remains a candidate until its metric
parity is demonstrated on a scored subset.

## Caveat: absolute latencies vs earlier smoke run

The same 3 pages measured ~147/42/300 s during the very first smoke run
(cold server, first heavy workload) versus ~36/42/42 s here. Warmed ROCm/MIOpen
kernel caches after hours of prior inference are the suspected cause. The
baseline-vs-optimized comparison is unaffected (both measured back-to-back in
the same warmed state), but absolute numbers should not be compared across
sessions with different cache states.

## Verdict

`max_batch_size=8` is a real ~9–12% throughput win on this workload with a
negligible VRAM cost (+~106 MB) and a one-time cold-start penalty. Status:
**experimental** until metric parity is verified; the official eval keeps the
frozen baseline config.
