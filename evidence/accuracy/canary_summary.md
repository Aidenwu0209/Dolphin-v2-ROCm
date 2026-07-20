# OmniDocBench v1.6 canary (20 pages)

| Field | Value |
|-------|-------|
| Backend | transformers |
| Platform | linux-rocm |
| Model revision | `c37c62768c644bb594da4283149c627765aa80f3` |
| Dataset revision | `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec` |
| Total | 20 |
| Succeeded | 19 |
| Failed | 1 (soft timeout) |
| Fallback | 0 |
| Completeness | complete (every page has markdown or explicit failure) |
| Duration | 5488.2 s |

## Explicit failure

`jiaocaineedrop_jiaocai_needrop_en_2263` finished generating markdown but exceeded
`page_timeout_seconds=900` (took 1664.4 s, 64 elements). Recorded as `timeout`
in `failures.json`. Canary timeout raised to 1800 s afterward to match the full
run config.

Machine-readable: [run_summary.json](canary/run_summary.json),
[failures.json](canary/failures.json).
