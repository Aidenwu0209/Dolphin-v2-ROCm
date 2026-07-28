# Roadmap

Ideas deferred from the current ROCm adaptation / OmniDocBench phase.

## Near-term (same project scope)

- Broader attention-backend matrix once flash-attention equivalents are stable
  for gfx1100
- Automated nightly canary on a self-hosted AMD runner
- Richer page-type stratified sampling for canary subsets

## Explicitly deferred (needs separate approval)

- Support for OCR models other than Dolphin-v2
- Training or fine-tuning pipelines
- SaaS / multi-tenant serving stack
- Web UI for document upload
- Kubernetes deployment charts
- Long-lived managed inference platform features

## Open investigations

- Root-cause ladder + NVIDIA 5070 Ti CUDA parity matrix (plan):
  [`docs/plans/2026-07-23-rootcause-and-5070ti-matrix.md`](docs/plans/2026-07-23-rootcause-and-5070ti-matrix.md);
  offline index: [`evidence/investigations/INDEX.md`](evidence/investigations/INDEX.md)
- vLLM on gfx1100: host pip/ROCm 7.2 wheels ruled out (see
  `evidence/compatibility/vllm-rocm72-gfx1100.md`). **Rewrite / next probe:**
  AMD `rocm/vllm` gfx110X container, then Dolphin smoke vs Transformers;
  fallback source build with `PYTORCH_ROCM_ARCH=gfx1100`
- TunableOps and `torch.compile` net benefit after accuracy checks
- Scorer packaging differences across OmniDocBench revisions
  (CDM/`magick`, TEDS process-join) — confirm on CUDA before upstream drafts
- OmniDocBench metric parity check for the batch=8 performance profile
  (throughput verified; full-set accuracy not re-scored under batch=8)
- Soft-timeout pages vs CUDA: AMD-specific long-tail vs model-hard pages
