# Sweet-spot ladder — results

repair 2.0 (white-box + previous code + step freezing + branch-k + temperature annealing): iteration 1 greedy, up to 6 iterations, 1 independent trajectories per level.

| Level | Spec dialect | Converged | Fastest | Best score |
|:-----:|--------------|:---------:|:-------:|:----------:|
| L3 | Business prose | 0/1 | — | 4/12 |
| L4 | Natural rules (tier trap) | 0/1 | — | 9/12 |
| L5 | Original dialect (boolean trap) | 1/1 | iter 4 | 12/12 |

Per-trajectory score paths (rows passed after each iteration):

- **L3 Business prose** — [[3, 1, 0, 4, 2, 0]]
- **L4 Natural rules (tier trap)** — [[3, 1, 2, 7, 6, 9]]
- **L5 Original dialect (boolean trap)** — [[3, 1, 1, 12]]
