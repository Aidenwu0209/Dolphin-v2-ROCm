# Investigations index (offline-first)

**Handoff for next agent:** [`HANDOFF.md`](HANDOFF.md)

AMD SSH was restored on 2026-07-28: the fresh ROCm doctor, smoke9, recovered
TEDS pages, and scorer isolations below are complete and synced locally. The
5070 Ti Windows host is set up but SSH/`sshd` remains intermittent. Publish
nothing upstream without approval (`docs/upstream-contributions.md`).

| ID | Topic | Status | Upstream candidate |
| --- | --- | --- | --- |
| amd-runtime-smoke | Fresh ROCm 7.2 / gfx1100 runtime + smoke9 | Doctor PASS; 9/9, all fallback layers zero ([evidence](amd-runtime-smoke/amd-ssh-20260728-rocm72-gfx1100-r1/README.md)) | N/A |
| teds-join | TEDS `AssertionError: can only join a started process` | workers=1 passed 3/3 on fallback47 and hybrid strict55; fresh8 recovered 8/8; independent page-match fork warnings remain ([strict55 evidence](teds-join/amd-ssh-20260728-w1-strict55-hybrid/README.md)) | OmniDocBench (after cross-host confirm preferred) |
| cdm-magick | CDM / ImageMagick 6 missing `magick` | Draft skeleton ready | OmniDocBench (local repro, no GPU) |
| soft-timeout | Soft-timeout pages (2/1651) | Notes + page lists | Local / docs first |
| three-findings | TEDS two-layer / weak-cluster / RR text↔RO split | Offline probe done (`three-findings/NOTES.md`) | Mixed (scorer vs model) |
| cuda5070ti-matrix | NVIDIA 5070 Ti parity matrix | Env+weights ready; smoke blocked on Session0/sshd | N/A (parity evidence) |

Plan: `docs/plans/2026-07-23-rootcause-and-5070ti-matrix.md`
