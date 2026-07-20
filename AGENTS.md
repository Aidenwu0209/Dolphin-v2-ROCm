# Contributor and execution-agent guide

This repository adapts Dolphin-v2 for AMD Radeon GPUs under ROCm and produces
reproducible OmniDocBench v1.6 evidence. Instructions here apply equally to
human contributors and automated execution agents.

## Scope

In scope:

- Transformers ROCm inference on gfx1100-class hardware
- OmniDocBench v1.6 adaptation, scoring, and provenance
- Performance baselines/optimizations with rollbackable switches
- Optional experimental vLLM backend
- CI for non-GPU validation and evidence contract checks

Out of scope unless explicitly approved:

- Other OCR models, training/finetuning, SaaS, web frontends, multi-tenant
  services, Kubernetes, or unrelated platform work

Record future ideas in `ROADMAP.md` instead of expanding scope silently.

## Safety

- Never commit model weights, OmniDocBench images, secrets, tokens, cookies,
  SSH endpoints, or private documents.
- Prefer isolated virtual environments; do not pollute system Python.
- Do not change kernel, GPU drivers, or system ROCm without explicit approval.
- Do not delete unknown directories, environments, containers, or datasets.
- Do not use `HSA_OVERRIDE_GFX_VERSION` as a default compatibility workaround.
- Do not publish upstream Issues/PRs/comments without explicit approval.

## Working style

1. Prefer small, independently verifiable commits.
2. Write failing tests before new behavior when practical.
3. Keep machine-readable evidence under `evidence/` and formal results under
   `results/omnidocbench/`.
4. Distinguish verified, experimental, unverified, and known-incompatible
   claims in documentation.
5. Pin versions in `runtime-manifest.json` and provenance files.

## Primary commands

```bash
scripts/setup_model_env.sh
scripts/doctor.sh
scripts/download_model.sh
scripts/run_smoke.sh
scripts/run_canary.sh
scripts/run_full_eval.sh
scripts/resume_eval.sh
scripts/collect_evidence.sh
```

Unit/contract tests (no GPU):

```bash
python -m pip install -e ".[dev]"
ruff format --check .
ruff check .
pytest
```

## Branching

- `main` holds the minimal bootstrap.
- Feature work lands on `feat/rocm-adaptation` until an explicit merge is
  requested. Do not auto-merge to `main`.
