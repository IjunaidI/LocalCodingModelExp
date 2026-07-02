# Sweet-spot ladder — results

10 sampled attempts per level.

| Level | Spec dialect | Pass-rate | Best | Most common outcome |
|:-----:|--------------|:---------:|:----:|---------------------|
| L1 | Prescriptive pseudocode | 7/10 | 12/12 | correct×7; ran, wrong numbers (10/12)×3 |
| L2 | Declarative spec | 5/10 | 12/12 | correct×5; ran, wrong numbers (9/12)×3 |
| L3 | Business prose | 0/10 | 4/12 | ran, wrong numbers (3/12)×3; runtime crash×2 |
| L4 | Natural rules (tier trap) | 0/10 | 3/12 | ran, wrong numbers (0/12)×5; runtime crash×2 |
| L5 | Original dialect (boolean trap) | 0/10 | 6/12 | runtime crash×2; syntax error×2 |
| L6 | Tables + natural tier (yes/no) | 8/10 | 12/12 | correct×8; ran, wrong numbers (0/12)×2 |
| L7 | Tables + True/False boolean | 1/10 | 12/12 | ran, wrong numbers (0/12)×4; ran, wrong numbers (6/12)×2 |
| L8 | Tables + tier + True/False | 2/10 | 12/12 | ran, wrong numbers (6/12)×5; runtime crash×3 |

Per-level score distributions (each number is one sampled attempt):

- **L1 Prescriptive pseudocode** — scores `[10, 10, 12, 12, 12, 12, 12, 12, 12, 10]`; correct ×7, ran, wrong numbers (10/12) ×3
- **L2 Declarative spec** — scores `[12, 9, 12, 12, 9, 0, 9, 12, 7, 12]`; correct ×5, ran, wrong numbers (9/12) ×3, ran, wrong numbers (0/12) ×1, ran, wrong numbers (7/12) ×1
- **L3 Business prose** — scores `[0, 3, 3, 2, 0, 0, 4, 0, 2, 3]`; ran, wrong numbers (3/12) ×3, runtime crash ×2, ran, wrong numbers (2/12) ×2, syntax error ×1, ran, wrong numbers (4/12) ×1, undefined name (forgot a table/import) ×1
- **L4 Natural rules (tier trap)** — scores `[0, 3, 0, 0, 0, 0, 0, 0, 0, 0]`; ran, wrong numbers (0/12) ×5, runtime crash ×2, syntax error ×2, ran, wrong numbers (3/12) ×1
- **L5 Original dialect (boolean trap)** — scores `[0, 6, 0, 3, 0, 0, 2, 0, 4, 0]`; runtime crash ×2, syntax error ×2, ran, wrong numbers (0/12) ×2, ran, wrong numbers (6/12) ×1, ran, wrong numbers (3/12) ×1, ran, wrong numbers (2/12) ×1, ran, wrong numbers (4/12) ×1
- **L6 Tables + natural tier (yes/no)** — scores `[0, 12, 12, 12, 0, 12, 12, 12, 12, 12]`; correct ×8, ran, wrong numbers (0/12) ×2
- **L7 Tables + True/False boolean** — scores `[0, 0, 0, 0, 6, 7, 12, 0, 6, 0]`; ran, wrong numbers (0/12) ×4, ran, wrong numbers (6/12) ×2, undefined name (forgot a table/import) ×1, runtime crash ×1, ran, wrong numbers (7/12) ×1, correct ×1
- **L8 Tables + tier + True/False** — scores `[0, 6, 12, 0, 6, 12, 0, 6, 6, 6]`; ran, wrong numbers (6/12) ×5, runtime crash ×3, correct ×2
