# Three findings — offline root-cause probe (2026-07-24)

Sources: pinned `OmniDocBench.json` (rev `aa1ee96…`, kept in `.local-cache/` only),
`evidence/accuracy/full-eval/metric_result.json`, local raw preds under
`results/omnidocbench/v16/linux-rocm/raw/` (~partial sync).

No GPU used. Conclusions below distinguish **verified**, **likely**, and **open**.

---

## 1) TEDS “two layers”

### Layer A — scorer join bug (verified)

| Fact | Value |
| --- | --- |
| Tables in GT / `sample_count` | **665 = 665** |
| `error_case_count` | 60 (55 unique images) |
| Unique reason | `AssertionError: can only join a started process` |
| Full-eval `teds_workers` | 4 |
| Canary (same bug) | workers=13, 2/3 tables errored |

**Not** explained by table size: error-page HTML length med/max is *smaller* than
all-tables (med 584 vs 692). Element counts are near the global mean.

**Over-represented among error images** (vs all table pages): `exam_paper` 2.5×,
`newspaper` 2.8×, `fuzzy_scan` 3.3×, `watermark` 2.3×. Under-represented:
`academic_literature` 0.09×. So the crash is not uniform random — harder/noisier
pages tickle a multiprocessing race more often — but the failure mode itself is
still a **scorer process lifecycle bug**, not bad HTML from Dolphin.

**Impact on headline TEDS — revised (do not claim free lunch):**

- `sample_count` equals total GT tables, but layout_hard arithmetic shows the
  published bucket mean is **over successful tables only** (errors excluded):
  layout_hard has 10 tables, **8 on error pages / 2 scored**, TEDS=0.208.
  If errors were scored as 0, the implied success score would be >1 — impossible.
- Therefore fixing join errors **adds** those tables back into the mean; net
  ALL TEDS move depends on what those 60 would score. Bound (if excluded now):
  roughly **+0.00 to +0.02** if they land near the current mean (~0.72), up to
  ~**+0.02–0.03** if they score ~1.0. Not a rewrite of the leaderboard.

**2026-07-28 workers=1 confirmation on the join-error inventory:**

- `fallback47`: 47 retained pages / 86 tables, three fresh scorer checkouts,
  zero TEDS errors/timeouts/exceptions/join errors. Sample/page scores were
  exactly stable at 0.7001473590 / 0.8230421462.
- `hybrid_recovered_strict55`: 47 retained predictions + 8 freshly recovered
  predictions = 55 pages / 94 tables, again three fresh scorer checkouts with
  zero TEDS errors/timeouts/exceptions/join errors. Sample/page scores were
  exactly stable at 0.7205098758 / 0.8399679331.
- The fresh eight-page inference was 8/8 successful with zero checkpoint,
  distorted-page, and raw distorted-page fallbacks.
- Page matching still emitted `latex_to_text` warnings containing
  `os.fork is unsafe while filelock is changing descriptor ownership`
  (strict55 occurrences: 47 / 33 / 51). This is an independent concurrency
  warning, so only the TEDS process-lifecycle layer is confirmed.
- The strict55 set is hybrid provenance and neither run is a 1,651-page
  re-score. These numbers must not be substituted for the official headline
  TEDS metric.

Evidence:
`evidence/investigations/teds-join/amd-ssh-20260728-w1-fallback47/` and
`evidence/investigations/teds-join/amd-ssh-20260728-w1-strict55-hybrid/`.

### Layer B — “real” weak buckets (verified sample sizes)

Scary page-level TEDS numbers are often **tiny-n or error-contaminated**:

| Bucket | TEDS | Table pages | Tables | Notes |
| --- | ---: | ---: | ---: | --- |
| `subset: layout_hard` | 0.21 | 8 | 10 | **8/10 tables on join-error pages**; only 2 scored |
| `subset: equation_hard` | 0.40 | 2 | 2 | n=2 |
| `layout: three_column` | 0.45 | 2 | 3 | n=2 |
| `language: traditional_chinese` | 0.50 | 7 | 10 | small |
| `data_source: newspaper` | 0.52 | 15 | **69** | real volume |
| `data_source: note` | 0.54 | 29 | 37 | moderate |
| `subset: table_hard` | 0.70 | 97 | **136** | real volume, mild weakness |

**Takeaway:** prioritize `newspaper` + `table_hard` for model/table-structure
work; treat `layout_hard` 0.21 as mostly a **reporting artifact** until join
errors are fixed and the bucket is re-scored.

---

## 2) “Cross-modal weak” cluster

### Verified: not five independent large populations

| Tag | n pages | Overlap notes |
| --- | ---: | --- |
| `historical_document` | **5** | 4/5 also `traditional_chinese`; 3/5 also `geometric_deformation` |
| `handwriting` | **2** | disjoint from historical |
| `geometric_deformation` | **13** | includes 3 historical |
| `fuzzy_content` | **4** | 2 overlap geometric |
| `traditional_chinese` | **13** | 4 historical + 5 research_report + … |

Union of the severe tags is roughly **~20 unique pages**, not hundreds. Several
“weak buckets” are the **same pages wearing multiple labels**.

### Likely mechanism (model / input difficulty, not AMD-specific)

- Historical pages: dense vertical traditional text, `other_layout`, often
  warped; pred element counts can collapse (e.g. GT 33 blocks → pred 11;
  GT 11 → pred 3). Latencies for two pages exceed 1000s — hard pages, not
  driver crashes.
- `distorted_page_mode` fallback rarely fires (1/13 geometric) — upstream
  overlap heuristic is not catching these.
- With n this small, **CUDA parity on the ~20-page union** is the right
  falsifier; do not file an AMD defect from these aggregates alone.

---

## 3) Research report: great text, bad reading order

### Verified facts

| | research_report | magazine (contrast) |
| --- | ---: | ---: |
| pages | 132 | 149 |
| text Edit_dist | **0.025** (best DS) | 0.027 |
| reading_order Edit_dist | **0.325** (near-worst DS) | **0.079** |
| mostly single_column | 118/132 | complex layouts dominate |
| naming | eastmoney 50, yanbao* 31 | — |

Brokerage dual-pane case study
(`eastmoney_66eea274…pdf_0`, layout=`1andmore_column`):

- **OCR of body paragraphs matches GT closely** → explains excellent text metric.
- **GT reading order** finishes the left “核心观点” column (incl. main table),
  then the right sidebar; headers/footers are ordered **late** (orders 24–27).
- **Pred reading order** emits headers **first**, then left column, then
  sidebar; splits GT’s single “相关研究报告” text_block into **5 `reference`**
  elements.
- GT also interleaves the right-side “买入” badge early (order 2); pred places
  it after left titles — a second permutation difference.

### Likely mechanism

`text_block` scoring is **match-then-compare per block** (order-tolerant).
`reading_order` scoring compares the **serialized order stream** after matching.
Dual-pane research reports are exactly where those diverge: block text can be
nearly perfect while column/header traversal order disagrees with GT → high RO
Edit_dist.

This is a **layout-order / serialization policy** issue (stage-1
`Parse the reading order of this document.` + how markdown is emitted), not an
AMD compute bug. Falsifier: same pages on CUDA should show the same RO gap.

### Open

Exact OmniDocBench RO formula (edit on concatenated text vs on order-index
sequence) not re-derived from scorer source in this pass; case study + metric
split is enough to guide the next experiment.

---

## Suggested next probes

1. Optional stronger scorer control: run the same hybrid55 prediction set with
   `teds_workers=4`; workers=1 is already confirmed across three repeats.
2. A full 1,651-page workers=1 re-score is still required before changing any
   official headline/bucket metric; do not infer it from hybrid55.
3. CUDA: run the 19-page severe-tag union + the 10-page eastmoney/yanbao
   dual-pane RO set; compare text vs RO deltas to this archive.
4. Optional local: post-process experiment that defers header/footer in markdown
   emission and merges adjacent `reference` lines — measure RO-only change.
