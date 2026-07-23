# Architecture

```text
CLI (dolphin-rocm)
  doctor -> environment attestation
  infer  -> pipeline -> backend.parse_page

eval/run_eval.py
  adapter.run_adapter -> pipeline (resumable)
  provenance + completeness checks

eval/run_benchmark.py
  fixed input set, N repeats, median metrics

Backends
  transformers_rocm  (supported baseline)
  vllm_rocm          (experimental)
  mock               (unit/contract tests)
```

## Transformers backend

Faithful to upstream Dolphin `demo_page.py`:

1. Layout pass: reading-order prompt on the full page
2. Content pass: batched element crops by type (table/formula/code/text)
3. Distorted-page holistic fallback when layout parse fails / overlaps heavily

ROCm notes:

- PyTorch ROCm exposes devices via `torch.cuda.*`
- Default attention implementation: SDPA
- CPU fallback is disabled unless `allow_cpu_fallback: true`

## Pipeline guarantees

- Deterministic page ordering by filename
- Per-page checkpoint after each attempt
- Empty markdown is a failure, never a success
- Resume never deletes prior outputs in the same directory
- Run stats reconcile against the checkpoint ledger
