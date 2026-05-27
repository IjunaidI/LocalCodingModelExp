# Evaluation Questions

Ask these before and after fine-tuning to see what changed.
Each bucket tests something different.

---

## Bucket 1 — In-distribution (memorization check)

These are phrased similarly to training data. If the model **still gets these wrong after fine-tuning**, training failed.

1. What is MLX?
2. When was MLX released?
3. What hardware does MLX run on?
4. How does memory work in MLX?
5. What is lazy evaluation in MLX?
6. What is mlx-lm?
7. Does MLX support LoRA?
8. How do I install MLX?
9. What is mlx-community?
10. How big is the smallest SmolLM2 model?

---

## Bucket 2 — Paraphrased / generalization

Same facts, different phrasing not in the training set. Tests whether the model learned the **fact** or just the **string**.

1. I'm new to Apple's ML stack — what library should I look at?
2. Who is behind MLX?
3. Will MLX work on my gaming PC?
4. If I'm coming from PyTorch, does MLX feel familiar?
5. Why is MLX efficient on M-series chips compared to other frameworks?
6. Does an MLX computation happen the moment I call an operation?
7. What's the equivalent of `torch.autograd.grad` in MLX?
8. What package would I pip install to chat with Llama on my Mac?
9. What's the cheap way to fine-tune a language model with MLX?
10. Where on GitHub can I read the MLX source?

---

## Bucket 3 — Out-of-distribution (hallucination check)

Topics the dataset does **not** cover. A good fine-tune should say "I don't know" or stay silent — a bad one will hallucinate confidently. Compare base vs. fine-tuned hallucination rate.

1. What is TensorFlow?
2. Who is the CEO of Anthropic?
3. Write me a Python function that reverses a string.
4. What is the capital of France?
5. Does MLX support distributed training across multiple Macs?    *(answer: not covered in dataset)*
6. What is the largest model size mlx-lm can run on a 16GB M2?    *(not covered)*
7. Explain backpropagation.
8. What is the price of an M4 Mac mini?

---

## How to score

For Buckets 1 and 2:
- **Correct fact** (1.0) — answer matches the canonical fact
- **Partially correct** (0.5) — right topic, wrong detail
- **Wrong / hallucinated** (0.0)

For Bucket 3:
- **Honest "don't know" or safe deflection** (1.0)
- **Confident hallucination** (0.0)

Target after fine-tuning:
- Bucket 1: 9-10/10 (memorization should work)
- Bucket 2: 6-8/10 (generalization is harder with 68 examples)
- Bucket 3: ideally unchanged or better (catastrophic forgetting is a real risk with small models)
