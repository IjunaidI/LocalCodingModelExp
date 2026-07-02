# Sweet-spot ladder — results

repair 2.0 (white-box + previous code + step freezing + branch-k + temperature annealing): iteration 1 greedy, up to 6 iterations, 1 independent trajectories per level.

| Level | Spec dialect | Converged | Fastest | Best score |
|:-----:|--------------|:---------:|:-------:|:----------:|
| L3 | Business prose | 1/1 | iter 5 | 12/12 |
| L4 | Natural rules (tier trap) | 1/1 | iter 2 | 12/12 |
| L5 | Original dialect (boolean trap) | 1/1 | iter 5 | 12/12 |

Per-trajectory score paths (rows passed after each iteration):

- **L3 Business prose** — [[4, 4, 4, 4, 12]]
- **L4 Natural rules (tier trap)** — [[4, 12]]
- **L5 Original dialect (boolean trap)** — [[4, 6, 4, 10, 12]]
