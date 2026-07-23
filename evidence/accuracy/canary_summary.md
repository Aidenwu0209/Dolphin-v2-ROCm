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

## Official scorer metrics (canary subset only)

Scored with the pinned OmniDocBench evaluator
(`2b161d010d2e3aff77a0edef359ea3a6411d23cd`, end2end quick_match) against a
20-entry GT subset derived from the pinned `OmniDocBench.json` (ground truth
unmodified; subset file only filters entries). This canary is intentionally
stratified toward hard buckets (equation_hard / layout_hard / table_hard), so
these numbers are NOT comparable to full-benchmark leaderboard scores.

| Metric | Value |
|--------|-------|
| Text block Edit_dist (page avg, lower better) | 0.2234 |
| Display formula Edit_dist | 0.2818 |
| Display formula CDM (higher better) | 0.8842 |
| Table TEDS (higher better) | 0.1403* |
| Table Edit_dist | 0.1809 |
| Reading order Edit_dist | 0.1838 |

\* Only a handful of canary pages contain tables and they come from the
`table_hard` bucket; treat the TEDS value as a plumbing check, not a quality
estimate.

Machine-readable: [metric_result.json](canary/metric_result.json),
[scorer_run_summary.json](canary/scorer_run_summary.json).

Scoring environment note: CDM initially reported 0.0 because Ubuntu 24.04
ships ImageMagick 6 without the `magick` CLI; fixed with a `magick`→`convert`
shim (see docs/troubleshooting.md). The re-run produced the values above.
