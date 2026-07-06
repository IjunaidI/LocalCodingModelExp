# 30-rule ladder — repair-loop results

Iteration 1 greedy, then up to 5 repair iterations (temp 0.6) with localized feedback, over 2 trajectories per rung; scored on total_receivables AND escrow.

| Level | Spec dialect | Greedy | Converged | Fastest | Best |
|:-----:|--------------|:------:|:---------:|:-------:|:----:|
| L1 | Prescriptive pseudocode (= spec_30.md) | 16/23 | 0/2 | — | 16/23 |
| L2 | Declarative prose, tables kept | 0/23 | 0/2 | — | 1/23 |
| L3 | Business prose, tables removed | 0/23 | 0/2 | — | 0/23 |
| L4 | Natural rules (% and prose tiers) | 0/23 | 0/2 | — | 0/23 |
| L5 | Raw requirement (True/False) | 0/23 | 0/2 | — | 0/23 |

Per-trajectory score paths (rows passed after each iteration):

- **L1 Prescriptive pseudocode (= spec_30.md)** — [[16, 16, 16, 16, 16], [16, 16, 5, 5, 5]]
- **L2 Declarative prose, tables kept** — [[0, 0, 0, 0, 0], [0, 0, 1, 1, 1]]
- **L3 Business prose, tables removed** — [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
- **L4 Natural rules (% and prose tiers)** — [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
- **L5 Raw requirement (True/False)** — [[0, 0, 0, 0, 0], [0, 0, 0, 0, 0]]
