# ROCm notes (gfx1100)

## Verified host (2026-07-20)

| Item | Value |
|------|-------|
| GPU | AMD Radeon PRO W7900D |
| Arch | gfx1100 |
| VRAM | 48 GB |
| ROCm | 7.2.0 |
| Driver | amdgpu 6.14.14 |
| PyTorch | 2.7.1+rocm7.2.0 |
| HIP (torch.version.hip) | 7.2.26015-fc0010cf6a |

Evidence: `evidence/environments/`.

## Device naming

`torch.cuda.is_available()` returning true on this host does **not** mean
NVIDIA CUDA is in use. ROCm PyTorch reuses the CUDA Python API surface.

## Defaults we refuse

- `HSA_OVERRIDE_GFX_VERSION` as a silent compatibility default
- Automatic CPU fallback for published runs
- Mixing CUDA wheels into the ROCm venv

## Attention

Flash-Attention 2 packages are not assumed available for gfx1100. The baseline
uses `attn_implementation: sdpa`.

## vLLM

vLLM is optional and experimental. Transformers is the supported baseline.
If vLLM fails on this stack, capture three reproductions under
`reproductions/vllm/` instead of blocking the mainline.
