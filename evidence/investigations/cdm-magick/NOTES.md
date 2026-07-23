# CDM / magick (offline)

## Verified in-project

- Without `magick`, CDM → 0.0 while score exit code stays 0
- IM6 `convert` shim restores canary CDM (~0.884)
- Documented in `docs/troubleshooting.md`

## Offline deliverable

- Issue draft: `docs/upstream-drafts/cdm-magick/ISSUE_DRAFT.md`
- Repro outline: `docs/upstream-drafts/cdm-magick/REPRO.md`

## Blocked on AMD?

No. Repro pack can be completed on any Linux box with OmniDocBench + IM6.
When AMD returns, still optional — prefer a clean VM/container for upstream repro.
