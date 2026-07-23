# Dolphin-v2-ROCm

在 AMD Radeon GPU（ROCm）上运行 ByteDance Dolphin-v2 文档解析，并提供可复现的
OmniDocBench v1.6 评测与性能证据。

## 当前状态

| 模块 | 状态 |
|------|------|
| W7900D / gfx1100 / ROCm 7.2 环境诊断 | **已验证** |
| Transformers ROCm 后端（BF16、SDPA） | **已验证** |
| 多样本 smoke（9/9，fallback=0） | **已验证** — [evidence/accuracy/smoke/](evidence/accuracy/smoke/) |
| OmniDocBench v1.6 canary（20 页） | **已验证**（19/20 成功，1 软超时，fallback=0） |
| OmniDocBench v1.6 全量评测（1651 页） | **已验证**（1649/1651 成功，2 软超时，fallback=0；官方 scorer `page_count=1651`）— [evidence/accuracy/full-eval/](evidence/accuracy/full-eval/) |
| 性能基线与优化对照（3 次重复） | **已验证** — batch=8 提升约 12% pages/s，详见 evidence/performance/comparison.md |
| vLLM ROCm 后端 | **预编译轮子在本环境不可用**（PyPI 仅 CUDA；AMD ROCm 7.2 索引无 vLLM），详见 evidence/compatibility/ |

计划中的能力不得写成已完成。公开指标必须能链接到 `results/` 或 `evidence/` 中的 JSON。

## 已验证硬件

- GPU：AMD Radeon PRO W7900D（48 GB），架构 `gfx1100`
- CPU：2× AMD EPYC 9334（128 线程）
- 系统：Ubuntu 24.04
- ROCm：7.2.0 / amdgpu 6.14.14
- 证据：[evidence/environments/runtime_attestation.json](evidence/environments/runtime_attestation.json)

## 快速开始

```bash
git clone https://github.com/Aidenwu0209/Dolphin-v2-ROCm.git
cd Dolphin-v2-ROCm
git checkout feat/rocm-adaptation

scripts/setup_model_env.sh /root/workspace/envs/dolphin
source /root/workspace/envs/dolphin/bin/activate
scripts/download_model.sh /root/workspace/models/Dolphin-v2
scripts/doctor.sh
scripts/run_smoke.sh
```

完整安装见 [docs/installation.md](docs/installation.md)。

## 评测

```bash
scripts/run_canary.sh
scripts/run_full_eval.sh
scripts/resume_eval.sh
```

说明见 [docs/evaluation.md](docs/evaluation.md)。

## 许可证与模型限制

- 本仓库适配与工具代码说明见 [NOTICE](NOTICE)
- 模型权重要求见 [MODEL_LICENSE](MODEL_LICENSE)（Qwen RESEARCH；默认非商业，除非另行授权）
- 不在本仓库分发模型权重或 OmniDocBench 数据

English README: [README.md](README.md)
