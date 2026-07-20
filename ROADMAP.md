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

- vLLM ROCm viability for Qwen2.5-VL / Dolphin-v2 on gfx1100
- TunableOps and `torch.compile` net benefit after accuracy checks
- Scorer packaging differences across OmniDocBench revisions
