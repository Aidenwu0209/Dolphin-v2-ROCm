# Smoke inference summary (AMD W7900D)

Host run directory: `/root/workspace/runs/smoke9` (not fully committed; images excluded).

| Field | Value |
|-------|-------|
| Backend | transformers |
| Platform | linux-rocm |
| Model revision | `c37c62768c644bb594da4283149c627765aa80f3` |
| Pages | 9 |
| Succeeded | 9 |
| Failed | 0 |
| Fallback | 0 |
| Duration | 1972.8 s |
| Model load | 4.17 s |
| Peak VRAM (observed) | ~8.2 GB |

Machine-readable copy: `results/smoke/_run_stats.json`.

Document types covered by upstream Dolphin demo samples in this smoke set include
text-heavy pages, formulas, and mixed layouts. OmniDocBench stratified canary /
full runs exercise broader type coverage.
