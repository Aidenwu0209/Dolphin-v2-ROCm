# CDM / magick local repro pack (outline)

No GPU required. Do not publish upstream until checklist in `ISSUE_DRAFT.md` passes.

## 1. Environment probe

```bash
which magick || true
which convert || true
convert -version | head -n 2
```

Record: distro, ImageMagick major version, whether `/usr/local/bin/magick` shim exists.

## 2. Minimal CDM-only score

Use any small prediction directory that contains formulas (canary predictions are enough).

```bash
# example shape — adjust to local OmniDocBench entrypoint
# MATCH_WORKERS=1 python -m ... --metrics CDM --pred_dir ... --gt ...
```

Capture:

- exit code (expect 0 today)
- CDM value (expect 0.0 without `magick`)
- log lines mentioning `magick` / render failure

## 3. Positive control

Install IM7 **or** the IM6 shim from `docs/troubleshooting.md`, re-run, confirm CDM > 0.

## 4. Artifact location

Store sanitized logs under `evidence/investigations/cdm-magick/` (no weights, no full dataset images in git).
