# TEDS join-error inventory (offline)

## Fact (verified from archived full-eval)

Source: `evidence/accuracy/full-eval/metric_result.json`

| Field | Value |
| --- | --- |
| TEDS sample_count | 665 |
| error_case_count | 60 |
| timeout_case_count | 0 |
| unique images | 55 |
| unique reason | `AssertionError: can only join a started process` |

Machine-readable dump: `inventory.json`

Canary also hit the same reason on 2 images:
`jiaocaineedrop_Chapter9.pdf_46.jpg`,
`page-dd5b0a99-4cc6-4fa9-ab63-a277947735b1.png`.

## Hypotheses (unverified until isolation)

1. Multiprocessing race / join-before-start in OmniDocBench TEDS worker pool
2. Host-specific (ulimit, fork+filelock interaction) rather than AMD GPU
3. Table HTML shape triggers a worker that never starts

## Offline next (no AMD needed)

1. Keep Issue draft local (`docs/upstream-drafts/teds-join/`) — do not publish
2. Prefer CUDA 5070 Ti **scorer-only** re-score of the same predictions before filing
3. When any Linux host is up: `n_jobs` matrix on the 55-image subset

## Page list for later isolation

`eval/configs/cuda5070ti_teds_error_pages.txt` (55 unique image basenames)
