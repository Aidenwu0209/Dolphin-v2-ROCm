# CUDA 5070 Ti host — workspace (no secrets)

Host is **Windows 10** (not Linux). WSL is not installed. Work stays under a
dedicated directory owned for this project.

## Remote workspace (on the 5070 Ti PC)

```text
%USERPROFILE%\Dolphin-v2-ROCm-cuda5070ti\
  workspace\Dolphin-v2-ROCm\   # git checkout feat/rootcause-offline-p0
  conda-env\                   # dedicated Miniconda prefix (python 3.12)
  data\OmniDocBench\           # junction → D:\OCR\datasets\omnidocbench
  models\Dolphin-v2\           # download target (ByteDance/Dolphin-v2 pin)
  evidence\                    # host-local logs (not necessarily synced to git)
```

## Observed on first connect

| Item | Value |
| --- | --- |
| GPU | NVIDIA GeForce RTX 5070 Ti (16 GB) |
| Driver / CUDA (nvidia-smi) | 596.36 / 13.2 |
| Dataset images present | ~1355 under `D:\OCR\datasets\omnidocbench\images` (full v1.6 expects 1651 — verify pin later) |
| Dolphin-v2 weights | Not present yet on host HF cache |
| System Python | 3.12 at `D:\ruanjian\python\Python312` (unused for runs) |
| Miniconda | `D:\ruanjian\Miniconda3` |

## Credentials

SSH password / IP are **not** stored in this repo. Use a local-only helper
outside git if needed.

## Status

| Step | State |
| --- | --- |
| Workspace folder | Done |
| Repo checkout (`feat/rootcause-offline-p0`) | Done |
| Conda env + `torch 2.11.0+cu128` | Done (`cuda.is_available()=True`, device name 5070 Ti) |
| Package install (`dolphin-v2-rocm`) | Done |
| Dolphin-v2 weights (pinned revision) | Done (~7.5 GB under `models\Dolphin-v2`) |
| OmniDocBench junction | Done (`data\OmniDocBench` → `D:\OCR\...`, ~1355 images) |
| 1-page smoke infer | **Blocked** — see below |

## Important Windows/CUDA caveat (hypothesis, not yet confirmed)

OpenSSH on this host runs commands in **Session 0 (Services)**. The first smoke
(Session 0) loaded checkpoint shards, then hung; the hung `python.exe` could not
be force-killed over SSH and later `nvidia-smi` calls also blocked — consistent
with a wedged WDDM/CUDA context. A PsExec `-i 1` retry (console session) was
started but the host was rebooted before its CUDA probe printed, so
**"Session 0 is the cause" remains unverified**. First job when access returns:
run the plain torch CUDA tensor probe in the console session.

## Known parity confounds (record before comparing numbers)

- **torch skew**: Windows/CUDA uses `2.11.0+cu128` (needed for Blackwell/sm_120);
  the ROCm baseline ran `2.7.1+rocm7.2.0`. `transformers==4.51.0` is pinned on
  both. Record both in `provenance.json` per run.
- **Dataset count mismatch**: host copy has ~1355 images but the pinned
  OmniDocBench v1.6 manifest expects 1651 pages. Verify the host copy's revision
  against `runtime-manifest.json` (`aa1ee96...`) before any formal run; if it is
  an older release, re-download the pinned revision into `data\` instead.
- **Scorer on native Windows is unproven** (magick/latex/multiprocessing).
  Prefer: Windows host for *inference* parity only; run scorer isolation
  (`n_jobs` matrix) on a Linux host.

## Cleanup owed on host (when access returns)

- Delete scheduled task `DolphinCudaSmoke` (`schtasks /Delete /F /TN
  DolphinCudaSmoke`) — otherwise it fires at 23:59 if the user is logged in.
- `workspace\tools\` now contains Sysinternals PsTools (PsExec) — keep or remove.
- `Desktop\RUN_DOLPHIN_SMOKE.bat` helper can be deleted once smoke passes.

## Outage log

- 2026-07-23 15:27–15:34: two reboot attempts issued over SSH to clear the hung
  GPU python (second one, `Restart-Computer -Force`, took effect at ~15:34).
- SSH did not come back through 16:25+. Likely causes: the 100.64.x tunnel
  (Tailscale-class) not starting before logon, or the machine waiting at a
  boot/login screen. Needs someone with physical/console access if it stays down.

Do not store SSH passwords in this repo.
