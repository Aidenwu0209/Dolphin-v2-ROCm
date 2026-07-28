# AMD ROCm 7.2 runtime and smoke9 revalidation

Date: 2026-07-28

This package records a fresh inference-path verification of the pinned
Dolphin-v2 Transformers pipeline on an AMD gfx1100 GPU. It is not an
OmniDocBench accuracy score, a formal performance benchmark, or a replacement
for the 1,651-page full evaluation.

## Fixed inputs

- Dolphin repository commit:
  `122162210307845c7bbb767ac54ca93d9a539c5e`
- Model: `ByteDance/Dolphin-v2`
- Model revision:
  `c37c62768c644bb594da4283149c627765aa80f3`
- Dataset: `opendatalab/OmniDocBench`
- Dataset revision:
  `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec`
- Input suite: the first nine entries in `eval/configs/canary_pages.txt`
- Backend: Transformers
- Dtype: BF16
- Attention: SDPA
- CPU fallback: disabled
- Runtime: ROCm 7.2.1, gfx1100, 48 GB VRAM

The two model shards and all required metadata were verified byte-for-byte
before loading: 14 top-level files, 7,520,906,987 bytes, and 824 indexed weight
entries.

## Result

| Check | Result |
| --- | ---: |
| Environment doctor | PASS |
| Total / succeeded / failed / skipped | 9 / 9 / 0 / 0 |
| Checkpoint fallback | 0 / 9 |
| Distorted-page mode | 0 / 9 |
| Raw distorted-page fallback | 0 / 9 |
| Missing page records | 0 |
| Non-empty Markdown / raw JSON | 9 / 9 |
| Model load | 26.35 s |
| Total duration | 2,605 s (43 min 25 s) |

The independent gate verified the exact page set, clean remote repository,
fresh output timestamps, non-empty and parseable outputs, model/config
provenance, and all three fallback representations.

## Dataset-revision note

The preserved `_run_stats.json` contains `"dataset_revision": null` because
the original smoke configuration did not propagate that field. It has not been
rewritten.

Input identity is independently pinned by `smoke9/input_manifest.json` and
`source-metadata/`: all 48 selected-image Hugging Face sidecars record the
fixed dataset revision, and all 48 etags matched the corresponding image
SHA-256. The evidence package includes names, hashes, and sidecars, but no
dataset images.

## Evidence map

- `provenance.json`: code, model, dataset, resolved config, and runtime pins
- `runtime/runtime_attestation.json`: machine-readable doctor result
- `runtime/doctor-report.md`: reader-facing doctor report
- `runtime/model_manifest.json`: model filenames, sizes, and hashes only
- `runtime/gpu_tensor_smoke.json`: synchronized BF16 compute check
- `smoke9/_run_stats.json`: unmodified inference summary
- `smoke9/pages_summary.json`: per-page status and latency
- `smoke9/input_manifest.json`: exact input filenames, sizes, and hashes
- `smoke9/output_manifest.json`: output filenames, sizes, and hashes only
- `smoke9/validation.json`: independent structural/fallback gate
- `source-metadata/`: pinned Hugging Face download sidecars and checksum streams
- `SHA256SUMS`: package integrity

## Scope and exclusions

This run validates runtime visibility, BF16 GPU execution, offline model
loading, and the nine-page inference path. A single-run duration is not a
formal throughput comparison. Model weights, dataset images, GT bodies,
prediction bodies, credentials, SSH keys, public connection endpoints, and
tokens are intentionally excluded.
