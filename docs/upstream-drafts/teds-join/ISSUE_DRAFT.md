# DRAFT — do not publish without approval

**Target:** OmniDocBench  
**Status:** Draft only. Prefer CUDA scorer-only confirmation before filing.  
**Related local inventory:** `evidence/investigations/teds-join/`

## Title (proposed)

TEDS scoring: `AssertionError: can only join a started process` drops tables from metric

## Summary

When scoring OmniDocBench table TEDS, some tables fail with:

```text
AssertionError: can only join a started process
```

Failed cases are counted as errors and excluded from successful TEDS aggregation.
On one full run (page_count=1651, table sample_count=665) we observed
**60 error cases / 55 unique images**, all with this single reason;
`timeout_case_count=0`.

## Environment (ROCm host; CUDA parity pending)

- OmniDocBench v1.6 scorer (pinned in this fork's runtime manifest)
- Python 3.10, Linux
- Scoring workers / MATCH_WORKERS as used in `scripts/run_full_score.sh`

## Expected

Tables either score successfully or surface a clear, recoverable timeout/error
without multiprocessing join failures.

## Actual

Worker join raises `AssertionError: can only join a started process` for a
non-trivial subset of tables.

## Minimal repro outline (to complete before publish)

1. Take predictions that include the 55 inventory images
2. Run table TEDS only with default `n_jobs`
3. Confirm error_cases reason string
4. Repeat with `n_jobs=1` and on CUDA-host scorer-only path

## Ask

Is this a known multiprocessing race in the TEDS path? Recommended fix or
workaround (`n_jobs=1`, process start method, etc.)?

## Attachments to include when filing

- Sanitized `error_cases` subset (no private docs)
- Scorer version / commit
- CUDA confirmation result (preferred)
