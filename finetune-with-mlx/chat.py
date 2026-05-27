"""Minimal chat with SmolLM2-135M-Instruct via mlx-lm."""
from mlx_lm import load, generate

MODEL = "mlx-community/SmolLM2-135M-Instruct"


def main() -> None:
    print(f"Loading {MODEL}...")
    model, tokenizer = load(MODEL)

    prompt = "Explain what MLX is in two sentences."
    messages = [{"role": "user", "content": prompt}]
    chat_prompt = tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )

    print(f"\n>>> {prompt}\n")
    response = generate(
        model,
        tokenizer,
        prompt=chat_prompt,
        max_tokens=200,
        verbose=False,
    )
    print(response)


if __name__ == "__main__":
    main()
