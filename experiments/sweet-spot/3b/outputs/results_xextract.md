# Sweet-spot ladder — results

Greedy (temperature 0), one attempt per level.

| Level | Spec dialect | Score | Result |
|:-----:|--------------|:-----:|:------:|
| L3 | Business prose | 4/12 | FAIL |
| L4 | Natural rules (tier trap) | 1/12 | FAIL |
| L5 | Original dialect (boolean trap) | 0/12 | FAIL |

Extraction check (did the model rebuild the tables correctly?):

- **L3** (extractor: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit): tables correct
- **L4** (extractor: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit): tables correct
- **L5** (extractor: mlx-community/Qwen2.5-Coder-7B-Instruct-4bit): tables correct
