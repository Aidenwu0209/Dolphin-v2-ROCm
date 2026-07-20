# Version adjustments

## Eval environment Python

- **Original target:** Python 3.11
- **Error:** `python3.11: command not found` on the AMD evaluation host
- **Adjusted version:** Python 3.10.20 (created by the host's available interpreter when
  `scripts/setup_eval_env.sh` ran; `odb-eval` venv reports 3.10.20)
- **Reason:** Host image ships 3.12 system Python and an existing 3.10 toolchain
  usable for OmniDocBench; 3.11 was not installed and we did not modify system
  packages without approval
- **Reproducibility impact:** Scorer runs in 3.10; inference remains on 3.12 +
  ROCm PyTorch. Document both in provenance. Prefer installing 3.11 later if a
  host image provides it, without changing pinned scorer commit

## OmniDocBench scorer commit

- **Pinned scorer checkout:** `2b161d010d2e3aff77a0edef359ea3a6411d23cd`
- **Dataset revision:** `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec`
- **Observed page count:** 1651 images / 1651 GT entries
