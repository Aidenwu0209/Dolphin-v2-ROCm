# vLLM on ROCm 7.2 / gfx1100: not installable from prebuilt wheels

Date: 2026-07-20. Host: AMD Radeon PRO W7900D, gfx1100, ROCm 7.2.0,
Ubuntu 24.04, Python 3.12.3. Probe performed in an isolated venv
(`envs/vllm-probe`); the production inference env was not touched.

## Findings

1. **AMD's ROCm 7.2 wheel index ships no vLLM.**
   `https://repo.radeon.com/rocm/manylinux/rocm-rel-7.2/` lists 101 wheels
   (torch / torchvision / triton / apex / jax / tensorflow / onnxruntime);
   zero match `vllm`. Listing captured in
   [`reproductions/vllm/no-rocm-wheels/radeon_rocm72_wheel_index.txt`](../../reproductions/vllm/no-rocm-wheels/radeon_rocm72_wheel_index.txt).

2. **`pip install vllm` resolves to the CUDA build and breaks the env.**
   PyPI `vllm==0.25.1` depends on `torch==2.11.0+cu130`; pip *uninstalled* the
   ROCm torch (2.7.1+rocm7.2.0) and installed ~40 `nvidia-*` CUDA packages.
   Install log: [`install_probe.log`](../../reproductions/vllm/no-rocm-wheels/install_probe.log).

3. **Engine init fails deterministically (3/3 runs).**
   With the CUDA build on this AMD host, `torch.cuda.is_available()` is False
   and `LLM(model=...)` raises `RuntimeError: Device string must not be empty`.
   Log: [`engine_init_3runs.log`](../../reproductions/vllm/no-rocm-wheels/engine_init_3runs.log);
   environment: [`environment.json`](../../reproductions/vllm/no-rocm-wheels/environment.json),
   [`pip_freeze.txt`](../../reproductions/vllm/no-rocm-wheels/pip_freeze.txt).

## Component isolation

- Not a Dolphin-v2 issue: the failure occurs before any model weights load.
- Not a ROCm runtime issue: the ROCm torch in the production env sees the GPU
  (see `evidence/environments/runtime_attestation.json`).
- Root cause is **packaging/platform**: PyPI vLLM wheels are CUDA-only, and
  AMD does not publish vLLM wheels for the ROCm 7.2 manylinux channel.

## Upstream-issue judgment

No issue drafted. vLLM's own documentation states ROCm support requires
building from source or using AMD's ROCm container images; the observed
behavior is documented platform scope, not a defect. Filing this upstream
would be a low-quality report.

## Remaining paths (deferred; see ROADMAP)

- AMD ROCm vLLM container images (`rocm/vllm`), pending GPU availability
  after the full OmniDocBench run.
- Source build with `PYTORCH_ROCM_ARCH=gfx1100`, cost/benefit unclear for
  RDNA3 vs the working Transformers baseline.

## Status for this repository

`vllm_rocm.py` backend remains **experimental / unavailable on this stack**.
The Transformers ROCm backend is the supported baseline; nothing in the main
evaluation path depends on vLLM.
