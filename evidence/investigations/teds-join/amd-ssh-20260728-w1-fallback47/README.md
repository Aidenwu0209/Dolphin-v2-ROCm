# AMD SSH TEDS join isolation — workers=1, fallback47

Date: 2026-07-28

This experiment re-scores the locally retained predictions for 47 of the 55
historical TEDS join-error pages. It is a scorer-only isolation run: the AMD GPU
is not used, formal full-evaluation outputs are not modified, and each repeat
runs from a fresh scorer checkout.

## Fixed inputs

- Dolphin repository commit: `122162210307845c7bbb767ac54ca93d9a539c5e`
- OmniDocBench scorer commit: `2b161d010d2e3aff77a0edef359ea3a6411d23cd`
- OmniDocBench GT: 1,651 records
- GT SHA-256:
  `a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496`
- Pages: 47
- Tables: 86
- Page-match workers: 4
- TEDS workers: 1
- Independent repeats: 3
- Python: 3.10.20

The eight predictions missing from the local archive are not silently skipped
from a claimed 55-page run. This evidence is explicitly marked `fallback47`.

## Result

All three repeats completed successfully:

| Repeat | Duration | TEDS sample score | TEDS page score | Errors | Timeouts | Exceptions | Join errors |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 20 s | 0.7001473590 | 0.8230421462 | 0 | 0 | 0 | 0 |
| 2 | 19 s | 0.7001473590 | 0.8230421462 | 0 | 0 | 0 | 0 |
| 3 | 18 s | 0.7001473590 | 0.8230421462 | 0 | 0 | 0 | 0 |

Both scores were exactly stable across repeats. The historical
`AssertionError: can only join a started process` did not occur with one TEDS
worker.

Page matching still emitted 46, 55, and 44 `latex_to_text` warnings,
respectively, containing `os.fork is unsafe while filelock is changing
descriptor ownership`. Matching nevertheless completed with the expected 47
pages and 86 tables, and the TEDS summaries recorded zero errors, timeouts,
exceptions, or join errors. This is a separate concurrency warning and limits
the conclusion below to the TEDS process-lifecycle layer; it is not evidence
that the entire scorer is free of concurrency issues.

This confirms the scorer process-lifecycle layer on the retained 47-page
subset. It does **not** replace the 1,651-page official score, does not recover
the missing eight predictions, and must not be used to claim a large headline
TEDS gain.

## Evidence

- `aggregate_validation.json`: three-repeat decision
- `driver_script.sha256`: exact isolation-script digest used by this run
- `input/input_manifest.json`: page/table counts and prediction hashes
- `repeat-*/validation.json`: structural and error-count checks
- `repeat-*/metric_result.json`: fresh TEDS-only metrics
- `repeat-*/scorer_run_summary.json`: runtime and stage execution
- `repeat-*/scorer-output.txt`: raw scorer output
- `repeat-*/SHA256SUMS`: metric and summary digests
- `repeat-*/upstream_tracked_result_manifest.*`: preserved upstream fixture
  inventory and digest
- `SHA256SUMS`: package-level integrity

The GT subset and prediction markdown are intentionally not copied into this
repository evidence directory.
