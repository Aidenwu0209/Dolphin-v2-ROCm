# Environment Doctor Report

- Generated: 2026-07-28T02:36:47Z
- Overall: **PASS**

| Check | Status | Detail |
| --- | --- | --- |
| os | PASS | Ubuntu 24.04.4 LTS |
| cpu_memory | PASS | AMD EPYC 9334 32-Core Processor x128 |
| disk | PASS | 994.8 GB free |
| rocm | PASS | ROCm 7.2.1, GPU ['AMD Radeon Graphics'] (gfx1100) |
| gpu_driver | PASS | amdgpu driver 6.14.14 |
| torch | PASS | torch 2.7.1+rocm7.2.0.git262e50d5 (HIP 7.2.26015-fc0010cf6a) sees AMD Radeon Graphics [gfx1100] |
| bf16_gpu_compute | PASS | BF16 2048x2048 matmul OK (mean=-0.0032) |
| packages | PASS | transformers=4.51.0, accelerate=1.4.0, qwen-vl-utils=0.0.14, numpy=2.1.2, pillow=12.2.0 |
| model_cache | PASS | 2 weight files, 6.99 GB |
| env_vars | PASS | no risky ROCm environment overrides set |

## Known risks

- PyTorch on ROCm reports devices through the torch.cuda namespace; this is HIP, not NVIDIA CUDA.
- gfx1100 (RDNA3) has no official flash-attention kernel coverage in some libraries; SDPA math paths are used instead.
