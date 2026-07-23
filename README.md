# Dolphin-v2-ROCm

Run ByteDance Dolphin-v2 document parsing on AMD Radeon GPUs (ROCm), with
reproducible OmniDocBench v1.6 evaluation and performance evidence.

## Current status

| Area | Status |
|------|--------|
| Environment doctor on W7900D / gfx1100 / ROCm 7.2 | **Verified** |
| Transformers ROCm backend (BF16, SDPA) | **Verified** |
| Multi-page smoke (9/9, fallback=0) | **Verified** — [evidence/accuracy/smoke/](evidence/accuracy/smoke/) |
| OmniDocBench v1.6 canary (20 pages) | **Verified** (19/20 success, 1 soft-timeout, fallback=0) — [evidence/accuracy/canary/](evidence/accuracy/canary/) |
| OmniDocBench v1.6 full eval (1651 pages) | **Verified** (1649/1651 success, 2 soft-timeouts, fallback=0; official scorer `page_count=1651`) — [evidence/accuracy/full-eval/](evidence/accuracy/full-eval/) |
| Performance baseline vs optimized (3-repeat) | **Verified** — batch=8 gives +12% pages/s; [evidence/performance/comparison.md](evidence/performance/comparison.md) |
| vLLM ROCm backend | **Known-incompatible via prebuilt wheels** on this stack (PyPI ships CUDA-only; AMD ROCm 7.2 wheel index has no vLLM) — [evidence/compatibility/vllm-rocm72-gfx1100.md](evidence/compatibility/vllm-rocm72-gfx1100.md) |

Do not treat planned items as completed. Every public metric must link to JSON
under `results/` or `evidence/`.

## Verified hardware

- GPU: AMD Radeon PRO W7900D (48 GB), arch `gfx1100`
- CPU: 2× AMD EPYC 9334 (128 threads)
- OS: Ubuntu 24.04
- ROCm: 7.2.0 / amdgpu 6.14.14
- Evidence: [`evidence/environments/runtime_attestation.json`](evidence/environments/runtime_attestation.json)

## Main OmniDocBench v1.6 results (full set)

Evidence: [`evidence/accuracy/metric_result.json`](evidence/accuracy/metric_result.json),
[`evidence/accuracy/full-eval/`](evidence/accuracy/full-eval/).

| Metric | Value |
|--------|------:|
| Text block Edit_dist ↓ | 0.0794 |
| Display formula Edit_dist ↓ | 0.1579 |
| Display formula CDM ↑ | 0.9137 |
| Table TEDS ↑ | 0.7188 |
| Table Edit_dist ↓ | 0.1392 |
| Reading order Edit_dist ↓ | 0.1487 |

Performance (formal 3-repeat, batch 4→8): +12% pages/s —
[`evidence/performance/comparison.md`](evidence/performance/comparison.md).

Upstream Dolphin examples target CUDA hosts. This repository isolates a ROCm
stack, refuses silent CPU fallback, pins model/data/tooling revisions, and
packages evaluation + performance evidence for gfx1100-class cards.

## Quick start

```bash
git clone https://github.com/Aidenwu0209/Dolphin-v2-ROCm.git
cd Dolphin-v2-ROCm
git checkout feat/rocm-adaptation

scripts/setup_model_env.sh /root/workspace/envs/dolphin
source /root/workspace/envs/dolphin/bin/activate
scripts/download_model.sh /root/workspace/models/Dolphin-v2
scripts/doctor.sh
scripts/run_smoke.sh
```

See [docs/installation.md](docs/installation.md).

## Environment check

```bash
dolphin-rocm doctor --model-dir /root/workspace/models/Dolphin-v2 \
  --json-out evidence/environments/runtime_attestation.json
```

## Single-page / directory inference

```bash
dolphin-rocm infer \
  --input examples/inputs \
  --output results/smoke \
  --backend transformers \
  --config eval/configs/smoke.yaml
```

## OmniDocBench evaluation

```bash
scripts/run_canary.sh
scripts/run_full_eval.sh
scripts/resume_eval.sh          # after interrupt
SCORE=1 scripts/run_full_eval.sh  # include official scorer when wired
```

Details: [docs/evaluation.md](docs/evaluation.md).

## Performance

Protocol and commands: [docs/performance.md](docs/performance.md).
Artifacts: `evidence/performance/`.

## Compatibility matrix

| Component | Status |
|-----------|--------|
| Transformers + ROCm PyTorch 2.7.1 on gfx1100 | Verified |
| BF16 GPU matmul | Verified |
| Dolphin-v2 two-stage page parse | Verified (host smoke) |
| vLLM ROCm | Known-incompatible via prebuilt wheels |
| Other AMD arches | Unverified |
| NVIDIA CUDA | Out of scope |

## Known issues

- First-page latency can be much higher than steady-state pages.
- Flash-Attention 2 is not assumed available; baseline uses SDPA.
- Python 3.11 may be unavailable on some hosts; eval env may fall back to 3.10/3.12.
- Full OmniDocBench scoring needs a raised `ulimit -n` (see `scripts/run_full_score.sh`);
  otherwise the matcher dies with `OSError: Too many open files` and may leave a
  stale canary `metric_result.json` in place if the watcher copies by mtime alone.
- Two full-eval pages soft-timed out at 1800s (explicit in `failures.json`).
- Batch=8 throughput gain is verified; full-set accuracy parity for batch=8 is
  not yet re-scored (see `ROADMAP.md`).

## Reproducing results

1. Install via [docs/installation.md](docs/installation.md)
2. Confirm doctor PASS
3. Run smoke / canary / full scripts
4. Inspect `provenance.json` next to each result
5. Validate with `python eval/release_contract.py <result_dir>`

## Upstream contributions

Drafts only until approved. See [docs/upstream-contributions.md](docs/upstream-contributions.md).

## Project layout

See the repository tree: `src/dolphin_v2_rocm`, `eval/`, `scripts/`,
`evidence/`, `results/`, `docs/`, `tests/`.

Contributor guide: [AGENTS.md](AGENTS.md).

## License and model restrictions

- Adaptation/tooling: see [NOTICE](NOTICE). No blanket commercial-claim badge is
  made for the model.
- Model weights: [MODEL_LICENSE](MODEL_LICENSE) (Qwen RESEARCH LICENSE; non-commercial
  unless separately licensed). Weights are **not** redistributed here.

## Acknowledgements

- [ByteDance Dolphin](https://github.com/bytedance/Dolphin)
- [OmniDocBench](https://github.com/opendatalab/OmniDocBench)
- AMD ROCm PyTorch builds
- Engineering patterns inspired by community ROCm OCR adaptation projects
  (re-validated here for Dolphin-v2 / gfx1100)

中文说明：[README.zh-CN.md](README.zh-CN.md)
