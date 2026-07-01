# Sweet-spot ladder — results

Best-of-10 sampled attempts per level, temperature 0.4.
L1–L5 strip scaffolding down the ladder; L6–L8 are controls that keep the literal lookup tables but re-arm the tier/boolean traps.

| Level | Spec dialect | Pass-rate | Best | Most common outcome |
|:-----:|--------------|:---------:|:----:|---------------------|
| L1 | Prescriptive pseudocode | 3/10 | 12/12 | ran, wrong numbers (8/12)×3; correct×3 |
| L2 | Declarative spec | 4/10 | 12/12 | correct×4; runtime crash×2 |
| L3 | Business prose | 0/10 | 4/12 | ran, wrong numbers (0/12)×3; ran, wrong numbers (4/12)×3 |
| L4 | Natural rules (tier trap) | 0/10 | 3/12 | ran, wrong numbers (3/12)×3; ran, wrong numbers (0/12)×3 |
| L5 | Original dialect (boolean trap) | 0/10 | 4/12 | ran, wrong numbers (4/12)×3; ran, wrong numbers (0/12)×3 |
| L6 | Tables + natural tier (yes/no) | 2/10 | 12/12 | ran, wrong numbers (8/12)×5; runtime crash×3 |
| L7 | Tables + True/False boolean | 3/10 | 12/12 | correct×3; runtime crash×2 |
| L8 | Tables + tier + True/False | 2/10 | 12/12 | ran, wrong numbers (5/12)×5; ran, wrong numbers (8/12)×3 |

Per-level score distributions (each number is one sampled attempt):

- **L1 Prescriptive pseudocode** — scores `[0, 0, 8, 12, 12, 0, 8, 8, 12, 0]`; ran, wrong numbers (8/12) ×3, correct ×3, runtime crash ×2, undefined name (forgot a table/import) ×1, ran, wrong numbers (0/12) ×1
- **L2 Declarative spec** — scores `[12, 0, 0, 8, 0, 9, 12, 8, 12, 12]`; correct ×4, runtime crash ×2, ran, wrong numbers (8/12) ×2, ran, wrong numbers (0/12) ×1, ran, wrong numbers (9/12) ×1
- **L3 Business prose** — scores `[0, 2, 4, 4, 4, 0, 3, 0, 0, 0]`; ran, wrong numbers (0/12) ×3, ran, wrong numbers (4/12) ×3, ran, wrong numbers (2/12) ×1, ran, wrong numbers (3/12) ×1, runtime crash ×1, syntax error ×1
- **L4 Natural rules (tier trap)** — scores `[3, 0, 0, 3, 0, 0, 1, 0, 3, 0]`; ran, wrong numbers (3/12) ×3, ran, wrong numbers (0/12) ×3, runtime crash ×2, syntax error ×1, ran, wrong numbers (1/12) ×1
- **L5 Original dialect (boolean trap)** — scores `[4, 0, 0, 0, 1, 0, 4, 3, 0, 4]`; ran, wrong numbers (4/12) ×3, ran, wrong numbers (0/12) ×3, syntax error ×1, ran, wrong numbers (1/12) ×1, runtime crash ×1, ran, wrong numbers (3/12) ×1
- **L6 Tables + natural tier (yes/no)** — scores `[12, 8, 8, 0, 0, 0, 8, 8, 12, 8]`; ran, wrong numbers (8/12) ×5, runtime crash ×3, correct ×2
- **L7 Tables + True/False boolean** — scores `[0, 12, 6, 1, 8, 0, 9, 12, 8, 12]`; correct ×3, runtime crash ×2, ran, wrong numbers (8/12) ×2, ran, wrong numbers (6/12) ×1, ran, wrong numbers (1/12) ×1, ran, wrong numbers (9/12) ×1
- **L8 Tables + tier + True/False** — scores `[5, 8, 12, 5, 5, 12, 5, 8, 8, 5]`; ran, wrong numbers (5/12) ×5, ran, wrong numbers (8/12) ×3, correct ×2
