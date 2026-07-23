# Soft-timeout pages (full-eval)

## Verified

Full infer: **1651 pages, 1649 success / 2 soft-timeout / fallback=0**.

| page_id | elems | budget | wall | peak VRAM |
| --- | --- | --- | --- | --- |
| `jiaocaineedrop_jiaocai_needrop_en_3063` | 40 | 1800s | 2503.3s | ~8151 MB |
| `newspaper_b615618f3cdb0f2c13ffb5865dea799c_1` | 121 | 1800s | 1976.6s | ~8110 MB |

Source: `evidence/accuracy/full-eval/failures.json`

Page list: `eval/configs/cuda5070ti_timeout_pages.txt`

## Hypotheses (need 5070 Ti / AMD when hosts return)

1. Pathological page (huge / dense) → legitimate long decode
2. ROCm-specific hang or slow kernel path
3. Soft-timeout budget too aggressive for outliers

## Offline stance

- Do **not** file upstream Issue yet
- Prefer CUDA 5070 Ti smoke on these 2 pages with the **same** timeout budget
- If CUDA also times out → model/timeout policy; if only ROCm → AMD adaptation track

## When a GPU host is back

1. Run timeout-2 list alone (batch=1 and batch=4)
2. Capture wall time, VRAM, whether completion succeeds with raised timeout
3. Record under `evidence/investigations/cuda5070ti-matrix/` or ROCm counterpart
