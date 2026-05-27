"""Compare the clean base model against the fine-tuned model side by side.

For each question, generates an answer from:
  - the clean downloaded SmolLM2-135M-Instruct
  - the same model with a LoRA adapter applied
and prints them in two columns.

Usage:
    python chat.py                              # interactive, uses adapters_v2
    python chat.py --adapter adapters           # compare against v1 instead
    python chat.py -q "What is MLX?"            # one-shot question
"""
import argparse
import shutil
import textwrap

from mlx_lm import load, generate
from mlx_lm.sample_utils import make_sampler

BASE_MODEL = "mlx-community/SmolLM2-135M-Instruct"


def answer(model, tokenizer, sampler, question: str, max_tokens: int) -> str:
    chat_prompt = tokenizer.apply_chat_template(
        [{"role": "user", "content": question}],
        tokenize=False,
        add_generation_prompt=True,
    )
    return generate(
        model, tokenizer, prompt=chat_prompt, max_tokens=max_tokens, sampler=sampler, verbose=False
    ).strip()


def side_by_side(left: str, right: str, left_title: str, right_title: str) -> str:
    total = shutil.get_terminal_size((100, 24)).columns
    gutter = " │ "
    col = max(20, (total - len(gutter)) // 2)

    def wrap(text: str) -> list[str]:
        lines: list[str] = []
        for raw in text.splitlines() or [""]:
            lines.extend(textwrap.wrap(raw, col) or [""])
        return lines

    left_lines, right_lines = wrap(left), wrap(right)
    height = max(len(left_lines), len(right_lines))
    left_lines += [""] * (height - len(left_lines))
    right_lines += [""] * (height - len(right_lines))

    out = [
        f"{left_title:<{col}}{gutter}{right_title:<{col}}",
        f"{'─' * col}{gutter}{'─' * col}",
    ]
    for l, r in zip(left_lines, right_lines):
        out.append(f"{l:<{col}}{gutter}{r:<{col}}")
    return "\n".join(out)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--adapter", default="adapters_v2", help="LoRA adapter dir")
    parser.add_argument("--max-tokens", type=int, default=150)
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("-q", "--question", default=None, help="One-shot question, then exit")
    args = parser.parse_args()

    print(f"Loading base model: {BASE_MODEL}")
    base_model, tokenizer = load(BASE_MODEL)
    print(f"Loading fine-tuned model: {BASE_MODEL} + {args.adapter}")
    ft_model, _ = load(BASE_MODEL, adapter_path=args.adapter)
    sampler = make_sampler(temp=args.temperature)

    def run(question: str) -> None:
        base_ans = answer(base_model, tokenizer, sampler, question, args.max_tokens)
        ft_ans = answer(ft_model, tokenizer, sampler, question, args.max_tokens)
        print(f"\nQ: {question}\n")
        print(side_by_side(base_ans, ft_ans, "BASE (clean)", f"FINE-TUNED ({args.adapter})"))
        print()

    if args.question:
        run(args.question)
        return

    print("\nType a question (or 'quit' to exit).")
    while True:
        try:
            question = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"quit", "exit", "q"}:
            break
        if question:
            run(question)


if __name__ == "__main__":
    main()
