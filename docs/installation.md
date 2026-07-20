# Installation

Validated host profile: Ubuntu 24.04, ROCm 7.2.0, AMD Radeon PRO W7900D
(gfx1100), Python 3.12 for inference.

## 1. Clone

```bash
git clone https://github.com/Aidenwu0209/Dolphin-v2-ROCm.git
cd Dolphin-v2-ROCm
git checkout feat/rocm-adaptation
```

## 2. Model inference environment

```bash
scripts/setup_model_env.sh /root/workspace/envs/dolphin
source /root/workspace/envs/dolphin/bin/activate
```

This installs pinned ROCm PyTorch wheels from the AMD manylinux index recorded
in `runtime-manifest.json`, plus Transformers 4.51.0 and related deps.

Do **not** `pip install -r` upstream CUDA-only requirements and assume they
work on ROCm.

## 3. Download the pinned model

```bash
scripts/download_model.sh /root/workspace/models/Dolphin-v2
```

Pinned revision: `c37c62768c644bb594da4283149c627765aa80f3`
(`ByteDance/Dolphin-v2`).

If `huggingface.co` is unreachable, set a mirror, for example:

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

## 4. Environment doctor

```bash
scripts/doctor.sh /root/workspace/models/Dolphin-v2
# or
dolphin-rocm doctor --model-dir /root/workspace/models/Dolphin-v2 \
  --json-out evidence/environments/runtime_attestation.json \
  --markdown-out evidence/environments/doctor-report.md
```

Acceptance signals:

- GPU marketing name includes W7900D
- architecture includes `gfx1100`
- `torch.version.hip` non-empty
- `torch.cuda.is_available()` true (ROCm uses the CUDA device namespace)
- BF16 matmul check PASS
- overall PASS or WARN (not FAIL)

## 5. Evaluation environment

```bash
# clone OmniDocBench separately, then:
export OMNIDOCBENCH_SRC=/root/workspace/OmniDocBench
scripts/setup_eval_env.sh /root/workspace/envs/odb-eval
```

Python 3.11 is preferred; if unavailable, the script falls back to 3.12 and
logs a warning.

## 6. Dataset

Download / locate official OmniDocBench v1.6 images and `OmniDocBench.json`.
Pin the dataset revision listed in `runtime-manifest.json` and record digests
in provenance before publishing metrics.

Default layout used by scripts:

```text
/root/workspace/data/OmniDocBench/
  OmniDocBench.json
  images/
```

## Version adjustments

If a pinned wheel fails to install, record in
`evidence/environments/version-adjustments.md`:

- original version
- error
- adjusted version
- reason
- reproducibility impact
