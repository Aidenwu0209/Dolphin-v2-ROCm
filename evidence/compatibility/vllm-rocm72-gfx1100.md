# vLLM on ROCm / gfx1100: status and remaining paths

Date: 2026-07-20 (pip-wheel probe); updated 2026-07-23 (paths clarified).

Host of the negative pip probe: AMD Radeon PRO W7900D, gfx1100, ROCm 7.2.0,
Ubuntu 24.04, Python 3.12.3. Probe used an isolated venv (`envs/vllm-probe`);
the production Transformers env was not modified.

## Verdict (short)

| Path | Status |
|------|--------|
| `pip install vllm` / ROCm 7.2 manylinux wheels | **Known-incompatible** (verified) |
| AMD `rocm/vllm` Docker images (gfx110X tags) | **Open / unverified** on this host |
| Source build (`PYTORCH_ROCM_ARCH=gfx1100`) | **Open / unverified** |
| Dolphin-v2 end-to-end on ROCm vLLM | **Open / unverified** |

Transformers ROCm remains the **supported baseline**. Missing vLLM does **not**
block smoke / canary / full OmniDocBench.

## What we already proved (pip path)

1. **AMD's ROCm 7.2 wheel index ships no vLLM.**
   `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/` listed 101 wheels
   (torch / torchvision / triton / …); zero match `vllm`.
   [`radeon_rocm72_wheel_index.txt`](../../reproductions/vllm/no-rocm-wheels/radeon_rocm72_wheel_index.txt).

2. **`pip install vllm` pulls the CUDA build and breaks a ROCm env.**
   PyPI `vllm` depended on CUDA torch and pulled `nvidia-*` packages.
   [`install_probe.log`](../../reproductions/vllm/no-rocm-wheels/install_probe.log).

3. **Engine init fails 3/3 on that CUDA build on this AMD host.**
   `torch.cuda.is_available()` is False; `LLM(...)` raises
   `RuntimeError: Device string must not be empty`.
   [`engine_init_3runs.log`](../../reproductions/vllm/no-rocm-wheels/engine_init_3runs.log).

### Isolation

- Not a Dolphin-v2 bug (fails before weights load).
- Not a broken ROCm stack (Transformers ROCm sees the GPU;
  see `evidence/environments/runtime_attestation.json`).
- Root cause for the *pip* path: **packaging / channel mismatch**.

Filing “`pip install vllm` fails on ROCm” as an upstream defect is low-quality:
vLLM/AMD docs already point to containers or source builds for ROCm.

## How to actually unlock vLLM (rewrite target)

### A. Preferred: AMD `rocm/vllm` container (gfx110X)

Docker Hub publishes tags such as:

- `rocm/vllm:rocm7.12.0_gfx110X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0`
- `rocm/vllm:rocm7.13.0_gfx110X-all_ubuntu24.04_py3.13_pytorch_2.10.0_vllm_0.19.1`

Probe sketch (host must allow Docker + `/dev/kfd` + `/dev/dri`):

```bash
docker pull rocm/vllm:rocm7.12.0_gfx110X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0
docker run --rm --device=/dev/kfd --device=/dev/dri --group-add=video \
  --ipc=host --security-opt seccomp=unconfined \
  rocm/vllm:rocm7.12.0_gfx110X-all_ubuntu24.04_py3.12_pytorch_2.9.1_vllm_0.16.0 \
  python -c "import torch; print(torch.__version__, torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

Success criteria for a **compatibility** probe (not yet a Dolphin claim):

1. Container sees gfx1100 / W7900D
2. `import vllm` works
3. Tiny text-only `LLM` init succeeds (3×)
4. Logs + image digest archived under `reproductions/vllm/rocm-container/`

### B. Source build

Build vLLM with `PYTORCH_ROCM_ARCH=gfx1100` (and follow current vLLM ROCm docs for
FlashAttention / Triton flags on RDNA3). Treat as high-cost; prefer container first.

### C. After engine works: Dolphin-v2 gate

Only then wire `src/dolphin_v2_rocm/backends/vllm_rocm.py` for real pages and
compare against Transformers:

- same smoke / canary pages
- pages/s, p50/p95, peak VRAM
- OmniDocBench metric delta (must disclose any accuracy change)

Until that gate passes, README must keep vLLM as **experimental / unverified**,
never as “Verified”.

## Status for this repository

| Artifact | Role |
|----------|------|
| `src/dolphin_v2_rocm/backends/vllm_rocm.py` | Experimental stub; raises if vLLM missing |
| `reproductions/vllm/no-rocm-wheels/` | Negative evidence for pip wheels |
| This document | Compatibility contract |

**Do not** install CUDA vLLM into the production Dolphin ROCm venv.
