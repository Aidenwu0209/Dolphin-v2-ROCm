# Stale metrics warning

The `metric_result.json` / `scorer_run_summary.json` previously copied into this
directory (and into `results/omnidocbench/v16/linux-rocm/`) were **canary
20-page** outputs (`page_count=20`), not the full 1651-page score.

Cause: official scorer crashed mid-match with `OSError: [Errno 24] Too many open
files` under `ulimit -n=1024`; the watcher still copied the newest
`*metric_result.json` by mtime (the canary artifact from 2026-07-20).

Remediation: `scripts/run_full_score.sh` (raised ulimit, archive-before-score,
refuse copy unless `page_count >= 1600`). Rescore running on the AMD host.
