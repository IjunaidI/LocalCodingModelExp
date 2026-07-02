# Sweet-spot ladder — results

10 sampled attempts per level.

| Level | Spec dialect | Pass-rate | Best | Most common outcome |
|:-----:|--------------|:---------:|:----:|---------------------|
| L1 | Prescriptive pseudocode | 10/10 | 12/12 | correct×10 |
| L2 | Declarative spec | 8/10 | 12/12 | correct×8; ran, wrong numbers (3/12)×1 |
| L3 | Business prose | 2/10 | 12/12 | ran, wrong numbers (4/12)×4; ran, wrong numbers (5/12)×3 |
| L4 | Natural rules (tier trap) | 1/10 | 12/12 | ran, wrong numbers (4/12)×4; ran, wrong numbers (5/12)×3 |
| L5 | Original dialect (boolean trap) | 2/10 | 12/12 | ran, wrong numbers (4/12)×5; correct×2 |
| L6 | Tables + natural tier (yes/no) | 1/10 | 12/12 | ran, wrong numbers (10/12)×9; correct×1 |
| L7 | Tables + True/False boolean | 9/10 | 12/12 | correct×9; ran, wrong numbers (3/12)×1 |
| L8 | Tables + tier + True/False | 1/10 | 12/12 | ran, wrong numbers (10/12)×8; correct×1 |

Per-level score distributions (each number is one sampled attempt):

- **L1 Prescriptive pseudocode** — scores `[12, 12, 12, 12, 12, 12, 12, 12, 12, 12]`; correct ×10
- **L2 Declarative spec** — scores `[12, 12, 12, 12, 12, 3, 12, 12, 12, 6]`; correct ×8, ran, wrong numbers (3/12) ×1, ran, wrong numbers (6/12) ×1
- **L3 Business prose** — scores `[12, 12, 0, 5, 5, 5, 4, 4, 4, 4]`; ran, wrong numbers (4/12) ×4, ran, wrong numbers (5/12) ×3, correct ×2, runtime crash ×1
- **L4 Natural rules (tier trap)** — scores `[5, 4, 5, 5, 2, 4, 4, 4, 3, 12]`; ran, wrong numbers (4/12) ×4, ran, wrong numbers (5/12) ×3, ran, wrong numbers (2/12) ×1, ran, wrong numbers (3/12) ×1, correct ×1
- **L5 Original dialect (boolean trap)** — scores `[4, 12, 4, 5, 4, 0, 5, 4, 4, 12]`; ran, wrong numbers (4/12) ×5, correct ×2, ran, wrong numbers (5/12) ×2, ran, wrong numbers (0/12) ×1
- **L6 Tables + natural tier (yes/no)** — scores `[10, 10, 10, 10, 10, 10, 10, 10, 10, 12]`; ran, wrong numbers (10/12) ×9, correct ×1
- **L7 Tables + True/False boolean** — scores `[12, 12, 12, 12, 12, 3, 12, 12, 12, 12]`; correct ×9, ran, wrong numbers (3/12) ×1
- **L8 Tables + tier + True/False** — scores `[10, 10, 10, 10, 10, 10, 12, 10, 5, 10]`; ran, wrong numbers (10/12) ×8, correct ×1, ran, wrong numbers (5/12) ×1
