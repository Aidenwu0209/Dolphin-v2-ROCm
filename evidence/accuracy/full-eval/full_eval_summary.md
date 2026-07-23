# OmniDocBench v1.6 full eval (AMD W7900D / ROCm)

| Field | Value |
|-------|-------|
| Backend | transformers |
| Platform | linux-rocm |
| Model revision | `c37c62768c644bb594da4283149c627765aa80f3` |
| Dataset revision | `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec` |
| Total / succeeded / failed / fallback | 1651 / 1649 / 2 / 0 |
| Duration | 206443.2 s |
| Official scorer page_count | 1651 |

## Official metrics (end2end quick_match)

| Metric | Value | Notes |
|--------|------:|-------|
| Text block Edit_dist (page avg, lower better) | 0.0794 | denom text pages = 1557 |
| Display formula Edit_dist | 0.1579 | |
| Display formula CDM (higher better) | 0.9137 | |
| Table TEDS (higher better) | 0.7188 | |
| Table Edit_dist | 0.1392 | |
| Reading order Edit_dist | 0.1487 | |

Machine-readable: [metric_result.json](metric_result.json), [run_summary.json](run_summary.json),
[scorer_run_summary.json](scorer_run_summary.json), [failures.json](failures.json).

## Explicit failures (soft timeout @ 1800s)

- `jiaocaineedrop_jiaocai_needrop_en_3063`
- `newspaper_b615618f3cdb0f2c13ffb5865dea799c_1`

## Provenance

- Inference started 2026-07-20T06:24:55Z, finished 2026-07-22T15:45:38Z
- First scorer attempt failed on `ulimit -n=1024` and briefly contaminated evidence with canary metrics; corrected by `scripts/run_full_score.sh` on 2026-07-23 (see `METRICS_STALE.md` / `_stale_canary_copy/`).
