# 30-rule ladder — results

5 attempts per rung (attempt 1 greedy, rest at temp 0.4); scored on total_receivables AND escrow across all rows.

| Level | Spec dialect | Greedy | Best-of-N | Pass-rate | Most common outcome |
|:-----:|--------------|:------:|:---------:|:---------:|---------------------|
| L1 | Prescriptive pseudocode (= spec_30.md) | 16/23 | 16/23 | 0/5 | ran, wrong numbers (16/23)×1; crash: undefined name×1 |
| L2 | Declarative prose, tables kept | 0/23 | 0/23 | 0/5 | crash: KeyError (table lookup)×3; crash: undefined name×1 |
| L3 | Business prose, tables removed | 0/23 | 0/23 | 0/5 | crash: KeyError (table lookup)×2; crash: undefined name×1 |
| L4 | Natural rules (% and prose tiers) | 0/23 | 0/23 | 0/5 | crash: syntax/load×3; crash: undefined name×2 |
| L5 | Raw requirement (True/False) | 0/23 | 0/23 | 0/5 | crash: syntax/load×2; crash: KeyError (table lookup)×2 |

Per-rung score distributions (each number is one attempt; attempt 1 greedy):

- **L1 Prescriptive pseudocode (= spec_30.md)** — `[16, 0, 5, 13, 0]`; ran, wrong numbers (16/23) ×1, crash: undefined name ×1, ran, wrong numbers (5/23) ×1, ran, wrong numbers (13/23) ×1, wrong return shape ×1
- **L2 Declarative prose, tables kept** — `[0, 0, 0, 0, 0]`; crash: KeyError (table lookup) ×3, crash: undefined name ×1, crash: syntax/load ×1
- **L3 Business prose, tables removed** — `[0, 0, 0, 0, 0]`; crash: KeyError (table lookup) ×2, crash: undefined name ×1, crash: syntax/load ×1, ran, wrong numbers (0/23) ×1
- **L4 Natural rules (% and prose tiers)** — `[0, 0, 0, 0, 0]`; crash: syntax/load ×3, crash: undefined name ×2
- **L5 Raw requirement (True/False)** — `[0, 0, 0, 0, 0]`; crash: syntax/load ×2, crash: KeyError (table lookup) ×2, crash: other ×1
