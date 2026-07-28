# AMD SSH TEDS join isolation — workers=1, strict55 hybrid

Date: 2026-07-28

This experiment completes the 55-page TEDS join-error inventory by combining
47 retained historical predictions with eight predictions freshly recovered on
the AMD ROCm host. The merge is labeled `hybrid_recovered_strict55`; it is not
the original 55-prediction archive and is not a new 1,651-page evaluation.

## Fixed inputs

- Dolphin repository commit:
  `122162210307845c7bbb767ac54ca93d9a539c5e`
- OmniDocBench scorer commit:
  `2b161d010d2e3aff77a0edef359ea3a6411d23cd`
- Full GT: 1,651 records
- Full-GT SHA-256:
  `a45cd84b04ad8b793e775089640e6b681209abea33ead54c1828ddca35fae496`
- Inventory: 55 pages, 94 GT tables, 60 historical join-error cases
- Historical source: 47 predictions, 86 GT tables, 52 historical cases
- Fresh source: 8 predictions, 8 GT tables, 8 historical cases
- Page-match workers: 4
- TEDS workers: 1
- Independent repeats: 3
- Driver SHA-256:
  `675bae309c31dc65e5490f75fa0aec6ea7d11aaa95854887b147c1425ba62df5`

The fresh eight-page inference passed its independent gate: 8/8 succeeded,
zero failures, zero missing records, and zero checkpoint, distorted-page, or
raw distorted-page fallbacks. Every merged Markdown file was non-empty and
matched its recorded source digest. The staging directory used only symlinks;
neither source directory nor any formal result directory was modified.

## Result

| Repeat | Duration | TEDS sample score | TEDS page score | Errors | Timeouts | Exceptions | Join errors | `latex_to_text` fork warnings |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 1 | 25 s | 0.7205098758 | 0.8399679331 | 0 | 0 | 0 | 0 | 47 |
| 2 | 25 s | 0.7205098758 | 0.8399679331 | 0 | 0 | 0 | 0 | 33 |
| 3 | 25 s | 0.7205098758 | 0.8399679331 | 0 | 0 | 0 | 0 | 51 |

All structural checks passed. Both scores were exactly stable across the three
fresh scorer checkouts, and `aggregate_validation.json` records
`confirmed=true`.

Page matching still emitted `latex_to_text` warnings containing
`os.fork is unsafe while filelock is changing descriptor ownership`. The
warning counts above are exact occurrences in each raw scorer output. Matching
nevertheless completed for all 55 pages and 94 tables, while the TEDS stage
recorded zero errors, timeouts, exceptions, and join errors. This is a separate
concurrency warning: the result supports only the workers=1 TEDS
process-lifecycle conclusion and does not show that the entire scorer is
concurrency-clean.

## Interpretation

The historical `AssertionError: can only join a started process` did not occur
in any repeat with one TEDS worker. Because eight predictions were newly
generated, this experiment cannot quantify a full-set accuracy change or be
used as the official 1,651-page TEDS score. No upstream issue was published.

## Evidence

- `aggregate_validation.json`: three-repeat aggregate decision and score
  stability
- `post_validation.json`: source composition, warning counts, hashes, and
  independent final gate
- `source-provenance/merge_manifest.json`: 47/8 source role and digest for each
  of the 55 predictions
- `source-provenance/fresh8_*`: fresh inference summary, input/output manifests,
  and fallback validation
- `repeat-*/validation.json`: per-repeat page/table/worker/error checks
- `repeat-*/metric_result.json`: TEDS-only metric result
- `repeat-*/scorer_run_summary.json`: page-match and TEDS runtime summary
- `repeat-*/scorer-output.txt`: raw scorer output
- `repeat-*/SHA256SUMS`: metric, summary, and raw-output digests
- `run_teds_join_isolation.sh` and `driver_script.sha256`: exact driver used
- `SHA256SUMS`: package-level integrity

GT bodies, prediction Markdown, dataset images, model weights, scorer clones,
credentials, and SSH connection details are intentionally excluded.
