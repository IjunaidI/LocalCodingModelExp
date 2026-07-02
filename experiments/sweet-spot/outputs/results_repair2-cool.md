# Sweet-spot ladder — results

repair 2.0 (white-box + previous code + step freezing + branch-k + temperature annealing): iteration 1 greedy, up to 8 iterations, 1 independent trajectories per level.

| Level | Spec dialect | Converged | Fastest | Best score |
|:-----:|--------------|:---------:|:-------:|:----------:|
| L3 | Business prose | 0/1 | — | 4/12 |
| L4 | Natural rules (tier trap) | 0/1 | — | 3/12 |
| L5 | Original dialect (boolean trap) | 0/1 | — | 3/12 |

Per-trajectory score paths (rows passed after each iteration):

- **L3 Business prose** — [[3, 3, 4, 0, 3, 3, 0, 2]]
- **L4 Natural rules (tier trap)** — [[3, 3, 3, 2, 0, 0, 2, 0]]
- **L5 Original dialect (boolean trap)** — [[3, 2, 2, 0, 0, 2, 1, 1]]
