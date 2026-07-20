# Plan: Dolphin-v2 ROCm adaptation and OmniDocBench v1.6

Date: 2026-07-20

## Goal

Deliver a reproducible Dolphin-v2 inference stack on AMD Radeon PRO W7900D
(gfx1100 / ROCm 7.2), with OmniDocBench v1.6 evaluation, performance evidence,
optional vLLM exploration, CI, and bilingual docs.

## Phases

1. Environment attestation (`dolphin-rocm doctor`, evidence/environments)
2. Transformers ROCm backend + resumable pipeline + smoke pages
3. OmniDocBench adapter (smoke / canary / full) with checkpoint/resume
4. Official scorer + release contract artifacts
5. Performance baseline then gated optimizations
6. Experimental vLLM validation or honest failure package
7. Upstream Issue drafts only for thrice-reproduced defects
8. CI + documentation packaging

## Constraints

- No kernel/driver/ROCm system changes without approval
- No `HSA_OVERRIDE_GFX_VERSION` as default
- No silent CPU fallback
- No fake page counts; follow pinned dataset revision
- Do not auto-merge `feat/rocm-adaptation` into `main`

## Success criteria

See the project acceptance checklist in the task brief: real W7900D inference,
full manifest processing with fallback=0, metrics, performance comparison,
provenance, and CI green for non-GPU checks.
