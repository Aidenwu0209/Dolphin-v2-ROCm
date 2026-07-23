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

vLLM is **optional and experimental**. Transformers is the supported baseline.

On this host we verified that the **pip / ROCm 7.2 manylinux wheel path is
dead** (CUDA wheels from PyPI; no vLLM in AMD's 7.2 index). That is **not** the
same as “vLLM can never run on gfx1100”.

Remaining unlock paths (not yet claimed as verified here):

1. AMD `rocm/vllm` Docker images with **gfx110X** tags
2. Source build with `PYTORCH_ROCM_ARCH=gfx1100`

See `evidence/compatibility/vllm-rocm72-gfx1100.md`. If a path fails, keep three
reproductions under `reproductions/vllm/` and do not block the mainline.
