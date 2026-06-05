# Rule: scoring rubric invariants

The rubric in `opsward/score.py` is **hardcoded module constants** — there is no
external rubric file. When changing scoring, preserve these invariants:

- `_OVERALL_WEIGHTS` values must sum to **1.0**.
- The CLAUDE.md per-dimension maxes (`_CMD_MAX`, `_ARCH_MAX`, `_CONV_MAX`,
  `_CONCISE_MAX`, `_CURRENCY_MAX`, `_ACTION_MAX`, …) must sum to **100**.
- Scoring functions are **pure**: `(ScanResult) -> ComponentScore` /
  `DiagnosisReport`, no side effects, no IO.

If you add or rebalance a dimension or weighted component, adjust the others so
the sums still hold, and add/update a test asserting the sums. Grade bands live
in `base.py` (`A ≥ 90, B ≥ 80, C ≥ 70, D ≥ 60, else F`) — don't duplicate them.
