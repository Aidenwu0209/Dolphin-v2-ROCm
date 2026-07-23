# Root-cause ladder + 5070 Ti parity matrix

Date: 2026-07-23. Status: **plan + offline P0 scaffold in progress**.
Branch: `feat/rootcause-offline-p0` (AMD GPU host currently down; GPU steps blocked).
Index: `evidence/investigations/INDEX.md`. Drafts live under `docs/upstream-drafts/`
(unpublished). Do not treat GPU parity or upstream publishes as done.

## Goal

1. Peel issues layer by layer: phenomenon → hypothesis → isolation → ownership.
2. Prepare upstream Issue/PR drafts only when the quality bar is met; publish
   only after explicit user approval.
3. Run a **NVIDIA RTX 5070 Ti (CUDA)** parity matrix to answer: AMD adaptation
   bug vs model/scorer/upstream limitation.

## Quality bar (from task book)

Before any upstream draft is “ready”:

- reproduced ≥3 times
- minimal reproduction
- full environment capture
- expected vs actual
- raw logs
- component isolation
- searched existing Issues
- correct target repo

Routing: Dolphin | transformers | vLLM | ROCm | OmniDocBench.

Drafts: `evidence/upstream-issues/<target>-<short-name>.md`  
Repros: `reproductions/<target>/<short-name>/`

## Decision matrix (now)

| Phenomenon | Draft now? | Need 5070 Ti first? | Local-only? |
|------------|------------|---------------------|-------------|
| CDM needs `magick` (IM7); IM6 → silent CDM≈0 | **Draft skeleton yes** | No | Doctor/shim yes |
| TEDS `can only join a started process` (~60) | Skeleton yes; full draft after isolation | **Yes (recommended)** | Retry/`n_jobs=1` fallback |
| 2 soft-timeout pages | No Issue yet | **Must** | Timeout policy after parity |
| Weak buckets (historical/handwriting/…) | No defect Issue | **Sample parity** | Analysis report only |
| vLLM pip/ROCm 7.2 wheels | **Do not file as defect** | No | Container/source on ROADMAP |
| Scorer `ulimit` pollution (fixed) | No | No | Scripts already hardened |

## Layer pipeline (every issue)

```text
Phenomenon (evidence path + logs)
  → Hypotheses H1/H2/H3 (falsifiable)
  → Isolation (infer | scorer | data | driver)
  → 5070 Ti parity? (yes/no + why)
  → Owner repo
  → Issue checklist (8 items)
  → Action: upstream-draft | local-fix | document-only | drop
```

---

## P0 — Local isolation (no 5070 Ti required)

### A. OmniDocBench CDM / `magick`

- Hypotheses: CDM shells out to `magick`; IM6-only hosts silently score 0.
- Isolation: magick on/off ≥3 times on canary/small set; independent of GPU.
- Owner: `opendatalab/OmniDocBench` (+ local doctor/docs).
- Outputs:
  - `reproductions/omnidocbench/cdm-magick/`
  - `evidence/upstream-issues/omnidocbench-cdm-magick.md` (draft, unpublished)

### B. TEDS process-join errors

- Inventory ~60 cases from `evidence/accuracy/full-eval/metric_result.json`.
- Scorer-only reruns on fixed markdown; vary `n_jobs ∈ {1,2,4,8}` ≥3 times.
- Owner decision after P1 CUDA scorer-only.
- Outputs: `evidence/investigations/teds-join-process/`,
  `reproductions/omnidocbench/teds-join-process/`

### C. Soft-timeout pages (AMD profiling only in P0)

- Pages:
  - `jiaocaineedrop_jiaocai_needrop_en_3063` (40 elems, 2503s)
  - `newspaper_b615618f3cdb0f2c13ffb5865dea799c_1` (121 elems, 1976s)
- Single-page profiling notes under `evidence/investigations/soft-timeout/`.
- **No upstream claim until CUDA parity.**

### D. Weak buckets

- Build fixed sample list (see P1); qualitative notes only in P0.
- Default action: `document-only` unless CUDA is clearly better.

**P0 exit:** CDM repro pack + draft; TEDS inventory + local scorer-only; timeout
notes; investigation index.

---

## P1 — RTX 5070 Ti CUDA parity

### Pinned constants (must match AMD)

| Item | Value |
|------|-------|
| Model | `ByteDance/Dolphin-v2` @ `c37c62768c644bb594da4283149c627765aa80f3` |
| Dataset | OmniDocBench v1.6 @ `aa1ee96d106dbe53d0ae59474d75c6e6d9b53fec` |
| Backend | Transformers two-stage (not vLLM) |
| Decode | greedy, BF16, SDPA, `resize_max_size=1600`, `max_new_tokens=4096` |
| Batch (accuracy) | **`max_batch_size=4`** |
| Timeout | `page_timeout_seconds=1800`, no CPU fallback |
| Scorer | same OmniDocBench revision / end2end quick_match |

### Allowed to differ

GPU, driver, CUDA vs ROCm PyTorch, host machine, absolute wall time.
Record everything in attestation; do not change prompts/config/revisions.

### Suites (default = A→B→C; D optional; E forbidden)

| Suite | Pages | Purpose |
|-------|------:|---------|
| A Smoke | 9 | Sanity |
| B Timeout-2 | 2 | AMD-only timeout? |
| C Weak buckets | 36–48 | Model limit vs ROCm regression |
| D Canary (optional) | 20 | Coarse metric align |
| E Full 1651 | — | Only if A–D conflict and release claim needs it |

Weak-bucket rule (fixed list, both sides):

| Bucket | Pages |
|--------|------:|
| historical_document | 6 |
| handwriting | 6 |
| geometric_deformation | 6 |
| newspaper (include timeout newspaper page) | 6 |
| table_hard | 6–8 |
| text_embedded_in_image | 6 |

List file: `eval/configs/cuda5070ti_weak_pages.txt` (hash recorded).

### Verdict rules

| Label | When |
|-------|------|
| **AMD-specific** | CUDA succeeds fast on timeout pages while AMD soft-timeouts; or weak-bucket metrics AMD worse by ≥20% on ≥4/6 pages same direction |
| **Model limitation** | Same failure / similar scores both sides |
| **Scorer bug** | Markdown OK both sides; CDM/TEDS fail from `magick`/join AssertionError on both |
| **Inconclusive** | OOM/crash one side, config drift, 10–20% noise band |

Timeout-2 shortcut:

| CUDA | AMD | Verdict |
|------|-----|---------|
| success ≪1800s | soft-timeout | strong AMD-specific |
| also timeout | soft-timeout | model limitation |
| mixed / crash | — | inconclusive |

### Evidence layout

```
evidence/environments/cuda-5070ti/
evidence/accuracy/cuda-5070ti/{smoke,timeout-2,weak-buckets,canary}/
evidence/comparisons/amd-w7900d-vs-cuda-5070ti/{comparison.md,comparison.csv,attribution.md}
reproductions/cuda/5070ti/{environment.json,pip_freeze.txt,nvidia-smi.txt,...}
results/omnidocbench/v16/linux-cuda-5070ti-*/   # local run dumps
```

### Comparison row fields

`suite,page_id,bucket,model_revision,dataset_revision,scorer_id,config_digest,platform,gpu,status,latency_ms,peak_vram_mb,fallback,text_edit_dist,formula_cdm,table_teds,reading_order_edit_dist,scorer_error,delta_vs_amd,attribution_hypothesis,evidence_path`

**P1 exit:** CUDA attestation; suites A–C done; comparison + attribution with
`next_action` per line; no “AMD bug” without parity.

Estimate: **1–2 person-days** if CUDA stack installs cleanly (else +driver risk).

---

## P2 — Drafts, local fixes, optional probes

1. Finalize Issue drafts only where P0/P1 still hold; wait for user publish OK.
   Priority: OmniDocBench `magick` → OmniDocBench TEDS join → (rare) Dolphin
   long-tail / transformers-ROCm if AMD-only with hard isolation.
2. Local hardening: doctor `magick`/ulimit checks; TEDS `n_jobs=1` fallback;
   timeout policy after attribution.
3. Weak-bucket report only (model-side experiments need separate approval).
4. Optional: `rocm/vllm` container probe (ROADMAP; not a pip-wheel defect Issue).

---

## Milestones

| Phase | When done | Evidence |
|-------|-----------|----------|
| P0 | CDM draft pack; TEDS inventory; timeout notes | `reproductions/omnidocbench/*`, `evidence/investigations/*` |
| P1 | 5070 Ti matrix + attribution | `evidence/accuracy/cuda-5070ti/`, `evidence/comparisons/...` |
| P2 | Drafts ready / local fixes on feat branch | `evidence/upstream-issues/*` still unpublished until approval |

## Explicit non-goals

- Auto-publishing upstream Issues/PRs
- Treating vLLM missing wheels as an upstream “bug”
- Default full 1651 on 5070 Ti
- Silent scope expansion into other OCR models / training / SaaS

## Open choices for the user

1. Parity scope: **A** smoke+timeout+weak (recommended) | **B** +canary | **C** expand if AMD regression suspected
2. TEDS draft: wait for CUDA (**recommended**) vs local scorer-only only
3. Soft-timeout policy: document | raise timeout | decide after CUDA
4. Weak buckets: analysis only (**recommended**) vs approve prompt/postprocess experiments
