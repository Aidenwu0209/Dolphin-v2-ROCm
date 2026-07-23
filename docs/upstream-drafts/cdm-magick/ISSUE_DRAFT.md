# DRAFT — do not publish without approval

**Target:** OmniDocBench  
**Status:** Draft skeleton; local repro pack outline ready (no GPU required)  
**Related:** `docs/troubleshooting.md` (CDM / magick), `evidence/investigations/cdm-magick/`

## Title (proposed)

CDM metric silently scores 0.0 when ImageMagick 7 `magick` CLI is missing (IM6 hosts)

## Summary

The CDM stage shells out to ImageMagick 7's `magick` binary to rasterize
rendered formula PDFs. Ubuntu 24.04 and other distros still ship ImageMagick 6
(`convert` only). When `magick` is absent:

- every formula render fails
- CDM reports **0.0**
- the overall score run still **exits 0**

This is easy to misread as a model quality failure.

## Expected

- Clear hard failure or explicit warning when the CDM dependency is missing
- Or document IM6/`convert` compatibility and detect it

## Actual

Silent CDM=0.0 with successful process exit.

## Minimal repro (no GPU)

1. Fresh Ubuntu 24.04 (or any host with IM6 only): `which magick` → empty;
   `which convert` → present
2. Run OmniDocBench formula CDM on any small prediction set with formulas
3. Observe CDM 0.0 and `magick: not found` (or equivalent) in logs
4. Install shim or IM7; re-run → CDM becomes non-zero

Local workaround used in this project (IM6):

```bash
cat > /usr/local/bin/magick <<'EOF'
#!/bin/sh
exec convert "$@"
EOF
chmod +x /usr/local/bin/magick
```

Verified here: canary CDM 0.0 → ~0.884 after shim.

## Ask

Would you accept a dependency check that fails fast, and/or IM6 `convert`
fallback documentation in the scorer README?

## Before publish checklist

- [ ] Capture log snippet with `magick: not found`
- [ ] Note OmniDocBench commit / version
- [ ] Confirm repro on a clean env without this fork's shim
- [ ] Explicit user approval to open upstream Issue
