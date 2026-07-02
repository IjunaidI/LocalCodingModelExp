# Sweet-spot ladder — results

10 sampled attempts per level.

| Level | Spec dialect | Pass-rate | Best | Most common outcome |
|:-----:|--------------|:---------:|:----:|---------------------|
| L3 | Business prose | 0/10 | 0/12 | runtime crash×6; ran, wrong numbers (0/12)×4 |
| L4 | Natural rules (tier trap) | 0/10 | 6/12 | ran, wrong numbers (0/12)×6; runtime crash×3 |
| L5 | Original dialect (boolean trap) | 0/10 | 9/12 | ran, wrong numbers (0/12)×4; runtime crash×2 |

Per-level score distributions (each number is one sampled attempt):

- **L3 Business prose** — scores `[0, 0, 0, 0, 0, 0, 0, 0, 0, 0]`; runtime crash ×6, ran, wrong numbers (0/12) ×4
- **L4 Natural rules (tier trap)** — scores `[0, 6, 0, 0, 0, 0, 0, 0, 0, 0]`; ran, wrong numbers (0/12) ×6, runtime crash ×3, ran, wrong numbers (6/12) ×1
- **L5 Original dialect (boolean trap)** — scores `[0, 0, 0, 0, 0, 2, 3, 0, 9, 3]`; ran, wrong numbers (0/12) ×4, runtime crash ×2, ran, wrong numbers (3/12) ×2, ran, wrong numbers (2/12) ×1, ran, wrong numbers (9/12) ×1

Extraction check (did the model rebuild the tables correctly?):

- **L3** (extractor: self): tables correct
- **L4** (extractor: self): tables correct
- **L5** (extractor: self): tables correct
