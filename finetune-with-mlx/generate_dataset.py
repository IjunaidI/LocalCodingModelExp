"""Generate a small instruction dataset about MLX for fine-tuning SmolLM2-135M.

Produces data/train.jsonl, data/valid.jsonl, data/test.jsonl in mlx-lm chat format:
    {"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}]}
"""
import json
import random
from pathlib import Path

random.seed(42)

# (canonical_answer, [list of question phrasings])
FACTS: list[tuple[str, list[str]]] = [
    (
        "MLX is Apple's open-source array framework for machine learning, designed and optimized for Apple Silicon.",
        [
            "What is MLX?",
            "Tell me about MLX.",
            "Can you explain what MLX is?",
            "What does MLX do?",
            "Describe MLX in one sentence.",
            "I have never heard of MLX. What is it?",
            "Give me a quick overview of MLX.",
        ],
    ),
    (
        "MLX was released by Apple in December 2023.",
        [
            "When was MLX released?",
            "Who released MLX and when?",
            "What year did MLX come out?",
            "When did Apple launch MLX?",
            "How old is MLX?",
            "When was MLX first published?",
        ],
    ),
    (
        "MLX is built specifically for Apple Silicon, including the M1, M2, M3, and M4 chips. It does not run on Intel Macs or NVIDIA GPUs.",
        [
            "What hardware does MLX run on?",
            "Can I use MLX on a Windows PC with an NVIDIA GPU?",
            "Does MLX work on Intel Macs?",
            "What chips does MLX support?",
            "Which Macs can run MLX?",
            "Is MLX cross-platform?",
        ],
    ),
    (
        "MLX has a NumPy-like API for arrays and a PyTorch-like API for neural networks, which makes it familiar to most Python ML developers.",
        [
            "What does the MLX API look like?",
            "Is MLX similar to NumPy?",
            "How does MLX compare to PyTorch in terms of API?",
            "What other libraries does MLX feel like?",
            "If I know NumPy, can I pick up MLX easily?",
        ],
    ),
    (
        "MLX uses a unified memory model. Arrays live in memory shared between the CPU and GPU, so there are no explicit data transfers between devices.",
        [
            "How does memory work in MLX?",
            "What is unified memory in MLX?",
            "Do I have to move tensors between CPU and GPU in MLX?",
            "Why is MLX fast on Apple Silicon?",
            "Explain unified memory in MLX.",
        ],
    ),
    (
        "MLX uses lazy evaluation. Operations build a computation graph and are only executed when a result is actually needed, such as when you print an array or call mx.eval.",
        [
            "Does MLX evaluate operations eagerly?",
            "What is lazy evaluation in MLX?",
            "When does MLX actually run computations?",
            "How does MLX's execution model differ from PyTorch's?",
            "What does mx.eval do?",
        ],
    ),
    (
        "MLX provides composable function transformations such as mx.grad for gradients, mx.vmap for vectorized maps, and mx.compile for graph compilation.",
        [
            "What function transformations does MLX support?",
            "How do I take a gradient in MLX?",
            "Does MLX have something like jax.grad?",
            "Can MLX compile functions?",
            "What is mx.vmap?",
        ],
    ),
    (
        "mlx-lm is the Python package for running and fine-tuning large language models on MLX. It supports loading models from Hugging Face, text generation, and LoRA fine-tuning.",
        [
            "What is mlx-lm?",
            "How do I run an LLM on MLX?",
            "What package handles language models in MLX?",
            "Does mlx-lm support fine-tuning?",
            "What can I do with mlx-lm?",
        ],
    ),
    (
        "MLX supports LoRA, which stands for Low-Rank Adaptation. LoRA fine-tunes only small low-rank adapter matrices instead of the full model weights, which makes it cheap to train on consumer hardware.",
        [
            "Does MLX support LoRA?",
            "What is LoRA?",
            "What does LoRA stand for?",
            "Why use LoRA instead of full fine-tuning?",
            "How does LoRA work in MLX?",
            "Can I fine-tune a model on my laptop with MLX?",
        ],
    ),
    (
        "The MLX source code lives at github.com/ml-explore/mlx and the mlx-lm package lives at github.com/ml-explore/mlx-lm.",
        [
            "Where can I find the MLX source code?",
            "Is MLX open source?",
            "What is the GitHub repo for MLX?",
            "Where is mlx-lm hosted?",
            "Can I see the MLX code?",
        ],
    ),
    (
        "Install the core library with `pip install mlx` and the language model toolkit with `pip install mlx-lm`.",
        [
            "How do I install MLX?",
            "What pip command installs mlx-lm?",
            "How do I get MLX on my machine?",
            "Give me the install command for MLX.",
            "How do I add mlx-lm to my project?",
        ],
    ),
    (
        "On Apple Silicon, MLX is often faster than PyTorch for many workloads because it is built natively for the Metal GPU and avoids CPU-GPU memory transfers thanks to unified memory.",
        [
            "Is MLX faster than PyTorch?",
            "Why would I use MLX instead of PyTorch on a Mac?",
            "What advantage does MLX have over PyTorch on Apple Silicon?",
            "Does MLX outperform PyTorch on M-series Macs?",
        ],
    ),
    (
        "MLX has two official front-ends: a Python API and a Swift API. The Python API is the most widely used.",
        [
            "What languages does MLX support?",
            "Is there a Swift API for MLX?",
            "Can I use MLX from Swift?",
            "What are the MLX front-ends?",
        ],
    ),
    (
        "mlx-community is the Hugging Face organization that hosts models pre-converted to MLX weight format, so you can load them directly with mlx-lm.",
        [
            "What is mlx-community?",
            "Where do I find MLX-compatible models?",
            "Where are MLX-format models hosted?",
            "How do I get a model that works with mlx-lm?",
        ],
    ),
    (
        "SmolLM2 is a family of small language models from Hugging Face. The smallest variant has 135 million parameters and is well-suited to running and fine-tuning on a laptop.",
        [
            "What is SmolLM2?",
            "How big is the smallest SmolLM2 model?",
            "Who built SmolLM2?",
            "Why use SmolLM2-135M for fine-tuning experiments?",
        ],
    ),
    (
        "To fine-tune with mlx-lm, run `mlx_lm.lora --model <model-id> --train --data <data-dir> --iters <n>`. The data directory must contain train.jsonl and valid.jsonl.",
        [
            "How do I fine-tune a model with mlx-lm?",
            "What command runs LoRA fine-tuning in mlx-lm?",
            "What files does mlx_lm.lora expect?",
            "Show me how to train a LoRA adapter in MLX.",
        ],
    ),
    (
        "After fine-tuning, mlx-lm saves a LoRA adapter file. You can either generate with the adapter by passing `--adapter-path` to mlx_lm.generate, or merge the adapter into the base weights with mlx_lm.fuse.",
        [
            "What does mlx-lm produce after fine-tuning?",
            "How do I use a trained LoRA adapter?",
            "What is mlx_lm.fuse for?",
            "How do I merge a LoRA adapter back into the base model?",
        ],
    ),
    (
        "MLX is developed by Apple's machine learning research team.",
        ["Who develops MLX?", "Which team at Apple makes MLX?", "Who maintains MLX?"],
    ),
    (
        "MLX is released under the MIT license, a permissive open-source license.",
        ["What license is MLX under?", "Is MLX free to use commercially?", "What is MLX's license?"],
    ),
    (
        "The core array type in MLX is mx.array, similar to a NumPy ndarray or a PyTorch tensor.",
        ["What is the main array type in MLX?", "What is mx.array?", "What data structure does MLX use for tensors?"],
    ),
    (
        "MLX arrays use float32 as the default data type.",
        ["What is the default dtype in MLX?", "What precision do MLX arrays use by default?"],
    ),
    (
        "mx.eval forces MLX to execute its lazy computation graph and produce concrete results.",
        ["What does mx.eval do?", "How do I force evaluation in MLX?", "How do I make a lazy MLX computation run?"],
    ),
    (
        "mx.value_and_grad returns both the value of a function and its gradient in a single call, which is the usual way to get gradients for training in MLX.",
        ["How do I get a loss and its gradient in MLX?", "What does mx.value_and_grad do?"],
    ),
    (
        "mlx.nn is the neural network module of MLX, providing layers, activations, and loss functions, similar to torch.nn in PyTorch.",
        ["What is mlx.nn?", "Where are neural network layers in MLX?", "Does MLX have a torch.nn equivalent?"],
    ),
    (
        "mlx.optimizers provides optimizers such as Adam, AdamW, and SGD for training models in MLX.",
        ["What optimizers does MLX provide?", "Where are optimizers in MLX?", "Does MLX have Adam?"],
    ),
    (
        "MLX supports quantization, including 4-bit and 8-bit, to shrink a model's size and memory footprint.",
        ["Does MLX support quantization?", "What quantization does MLX support?", "Can MLX run models in 4-bit?"],
    ),
    (
        "mlx_lm.convert downloads a Hugging Face model and converts it to MLX format, optionally quantizing it.",
        ["What does mlx_lm.convert do?", "How do I convert a Hugging Face model to MLX?", "How do I quantize a model with mlx-lm?"],
    ),
    (
        "mlx_lm.generate is the command for generating text from a model with mlx-lm.",
        ["How do I generate text with mlx-lm?", "What does mlx_lm.generate do?", "What command produces text from an MLX model?"],
    ),
    (
        "mlx_lm.server starts a local server with an OpenAI-compatible API, so existing OpenAI client code can talk to a local MLX model.",
        ["What is mlx_lm.server?", "Does mlx-lm have an API server?", "How do I serve an MLX model over an API?"],
    ),
    (
        "mx.compile compiles an MLX function into a single optimized graph, which speeds up repeated execution.",
        ["What does mx.compile do?", "How do I speed up an MLX function?", "What is mx.compile for?"],
    ),
    (
        "In addition to LoRA, mlx-lm also supports DoRA and full fine-tuning, selected with the --fine-tune-type option.",
        ["What fine-tuning types does mlx-lm support?", "Does mlx-lm support full fine-tuning?", "What is the --fine-tune-type option?"],
    ),
    (
        "MLX can run on either the GPU or the CPU, and you can choose the default with mx.set_default_device. On Apple Silicon the GPU is used by default.",
        ["Can MLX run on the CPU?", "How do I choose CPU or GPU in MLX?", "What does mx.set_default_device do?"],
    ),
]

# General-knowledge / general-instruction replay set. Its job is to preserve the
# base model's broad abilities so fine-tuning on MLX does not cause catastrophic
# forgetting. Keep answers accurate and in the same concise style as the MLX facts.
GENERAL: list[tuple[str, list[str]]] = [
    # --- Python coding ---
    (
        "You can reverse a string in Python with slicing:\n\n```python\ndef reverse_string(s):\n    return s[::-1]\n```",
        [
            "Write me a Python function that reverses a string.",
            "How do I reverse a string in Python?",
            "Give me Python code to flip a string backwards.",
        ],
    ),
    (
        "Here is a Python function that sums a list of numbers:\n\n```python\ndef total(numbers):\n    return sum(numbers)\n```",
        [
            "Write a Python function to add up a list of numbers.",
            "How do I sum a list in Python?",
            "Give me code to total all numbers in a list.",
        ],
    ),
    (
        "You can check whether a string is a palindrome like this:\n\n```python\ndef is_palindrome(s):\n    return s == s[::-1]\n```",
        [
            "Write a Python function to check if a string is a palindrome.",
            "How do I test for a palindrome in Python?",
        ],
    ),
    (
        "Here is a recursive factorial in Python:\n\n```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n```",
        [
            "Write a Python function that computes a factorial.",
            "How do I calculate factorial in Python?",
        ],
    ),
    (
        "You can read a text file in Python with:\n\n```python\nwith open('file.txt') as f:\n    text = f.read()\n```",
        [
            "How do I read a file in Python?",
            "Show me Python code to open and read a text file.",
        ],
    ),
    # --- Geography / world facts ---
    (
        "The capital of France is Paris.",
        ["What is the capital of France?", "Name the capital city of France."],
    ),
    (
        "The capital of Japan is Tokyo.",
        ["What is the capital of Japan?", "Which city is Japan's capital?"],
    ),
    (
        "The capital of Pakistan is Islamabad.",
        ["What is the capital of Pakistan?", "Name Pakistan's capital."],
    ),
    (
        "The largest planet in our solar system is Jupiter.",
        ["What is the largest planet?", "Which planet is the biggest in the solar system?"],
    ),
    (
        "Water is made of two hydrogen atoms and one oxygen atom, giving the formula H2O.",
        ["What is water made of?", "What is the chemical formula for water?"],
    ),
    # --- Math ---
    (
        "12 multiplied by 12 is 144.",
        ["What is 12 times 12?", "Calculate 12 x 12."],
    ),
    (
        "25 percent of 200 is 50.",
        ["What is 25% of 200?", "Calculate 25 percent of 200."],
    ),
    (
        "A prime number is a whole number greater than 1 whose only divisors are 1 and itself, such as 2, 3, 5, and 7.",
        ["What is a prime number?", "Define a prime number."],
    ),
    # --- ML concepts (accurate, framework-neutral) ---
    (
        "TensorFlow is an open-source machine learning framework developed by Google for building and training models, especially neural networks.",
        ["What is TensorFlow?", "Tell me about TensorFlow.", "Who makes TensorFlow?"],
    ),
    (
        "PyTorch is an open-source machine learning framework developed by Meta, widely used for deep learning research and production.",
        ["What is PyTorch?", "Tell me about PyTorch."],
    ),
    (
        "Backpropagation is the algorithm that trains neural networks by computing the gradient of the loss with respect to each weight using the chain rule, then updating the weights to reduce the loss.",
        [
            "Explain backpropagation.",
            "What is backpropagation?",
            "How does backpropagation work?",
        ],
    ),
    (
        "Gradient descent is an optimization algorithm that iteratively adjusts parameters in the direction that reduces a loss function.",
        ["What is gradient descent?", "Explain gradient descent."],
    ),
    (
        "A neural network is a model made of layers of connected nodes that learn to map inputs to outputs by adjusting weights during training.",
        ["What is a neural network?", "Explain what a neural network is."],
    ),
    (
        "Overfitting happens when a model learns the training data too closely, including its noise, and then performs poorly on new, unseen data.",
        ["What is overfitting?", "Explain overfitting in machine learning."],
    ),
    # --- Honest uncertainty (teach the model NOT to confidently hallucinate) ---
    (
        "I don't have reliable, up-to-date information on that, so I can't say for certain. I'd recommend checking a current, authoritative source.",
        [
            "Who is the CEO of Anthropic?",
            "What is the price of an M4 Mac mini?",
            "What is today's stock price for Apple?",
            "Who won the most recent election?",
            "What is the latest iPhone model?",
        ],
    ),
    # --- General helpfulness / conversation ---
    (
        "Hello! How can I help you today?",
        ["Hi", "Hello", "Hey there"],
    ),
    (
        "I'm an AI assistant. I can answer questions, explain concepts, write code, and help with a range of tasks.",
        ["What can you do?", "Who are you?", "What are you?"],
    ),
    (
        "To stay focused, try breaking work into small tasks, removing distractions, and taking short regular breaks.",
        ["How can I be more productive?", "Give me a tip to focus better."],
    ),
    # --- More Python coding ---
    (
        "You can find the maximum of a list in Python with the built-in `max`:\n\n```python\nlargest = max(numbers)\n```",
        ["How do I find the largest number in a list in Python?", "Get the max of a list in Python."],
    ),
    (
        "You can sort a list in Python with:\n\n```python\nnumbers.sort()          # in place\nsorted_list = sorted(numbers)  # new list\n```",
        ["How do I sort a list in Python?", "Show me how to sort numbers in Python."],
    ),
    (
        "You can loop over a list in Python like this:\n\n```python\nfor item in items:\n    print(item)\n```",
        ["How do I iterate over a list in Python?", "Write a Python for loop over a list."],
    ),
    (
        "You can count items in a list with `len`:\n\n```python\ncount = len(items)\n```",
        ["How do I get the length of a list in Python?", "Count elements in a Python list."],
    ),
    (
        "You can remove duplicates from a list by converting it to a set:\n\n```python\nunique = list(set(items))\n```",
        ["How do I remove duplicates from a list in Python?", "Deduplicate a Python list."],
    ),
    (
        "Here is FizzBuzz in Python:\n\n```python\nfor i in range(1, 101):\n    if i % 15 == 0:\n        print('FizzBuzz')\n    elif i % 3 == 0:\n        print('Fizz')\n    elif i % 5 == 0:\n        print('Buzz')\n    else:\n        print(i)\n```",
        ["Write FizzBuzz in Python.", "Show me the FizzBuzz program."],
    ),
    # --- More geography / world facts ---
    (
        "The capital of the United States is Washington, D.C.",
        ["What is the capital of the United States?", "Name the U.S. capital."],
    ),
    (
        "The capital of the United Kingdom is London.",
        ["What is the capital of the UK?", "Which city is the UK's capital?"],
    ),
    (
        "The capital of Germany is Berlin.",
        ["What is the capital of Germany?", "Name Germany's capital."],
    ),
    (
        "The capital of India is New Delhi.",
        ["What is the capital of India?", "Which city is India's capital?"],
    ),
    (
        "The capital of Australia is Canberra, not Sydney.",
        ["What is the capital of Australia?", "Name Australia's capital."],
    ),
    (
        "The longest river in the world is the Nile, though the Amazon is a close rival by some measures.",
        ["What is the longest river in the world?", "Name the world's longest river."],
    ),
    (
        "There are seven continents: Africa, Antarctica, Asia, Europe, North America, Oceania, and South America.",
        ["How many continents are there?", "Name the continents."],
    ),
    # --- More math ---
    (
        "7 plus 8 equals 15.",
        ["What is 7 + 8?", "Add 7 and 8."],
    ),
    (
        "100 divided by 4 is 25.",
        ["What is 100 divided by 4?", "Calculate 100 / 4."],
    ),
    (
        "The square root of 144 is 12.",
        ["What is the square root of 144?", "Find the square root of 144."],
    ),
    (
        "The area of a circle is pi times the radius squared, written A = pi * r^2.",
        ["What is the formula for the area of a circle?", "How do I calculate a circle's area?"],
    ),
    # --- More general definitions ---
    (
        "An API, or application programming interface, is a defined set of rules that lets one piece of software talk to another.",
        ["What is an API?", "Explain what an API is."],
    ),
    (
        "JSON, or JavaScript Object Notation, is a lightweight text format for storing and exchanging structured data.",
        ["What is JSON?", "Explain what JSON is."],
    ),
    (
        "Git is a distributed version control system that tracks changes in source code during software development.",
        ["What is Git?", "Explain what Git is."],
    ),
    (
        "HTTP, the Hypertext Transfer Protocol, is the protocol used to transfer web pages and data between clients and servers.",
        ["What is HTTP?", "Explain what HTTP is."],
    ),
    (
        "Machine learning is a field of AI where systems learn patterns from data to make predictions or decisions without being explicitly programmed for each case.",
        ["What is machine learning?", "Explain machine learning in simple terms."],
    ),
    (
        "A database is an organized collection of data that can be stored, queried, and updated, often managed by software like PostgreSQL or SQLite.",
        ["What is a database?", "Explain what a database is."],
    ),
    # --- More everyday / conversational ---
    (
        "You're welcome! Happy to help.",
        ["Thank you", "Thanks!", "Thanks a lot"],
    ),
    (
        "I'm doing well, thanks for asking! How can I help you?",
        ["How are you?", "How's it going?"],
    ),
    (
        "A balanced day usually includes some movement, healthy meals, focused work, and enough rest. Small consistent habits matter more than big changes.",
        ["How can I live a healthier life?", "Give me general health advice."],
    ),
    (
        "To learn a new skill, start with the basics, practice regularly, and build small projects to apply what you learn.",
        ["How do I learn a new skill?", "What's the best way to learn something new?"],
    ),
]


def build_examples() -> list[dict]:
    examples = []
    for source in (FACTS, GENERAL):
        for answer, questions in source:
            for q in questions:
                examples.append(
                    {
                        "messages": [
                            {"role": "user", "content": q},
                            {"role": "assistant", "content": answer},
                        ]
                    }
                )
    random.shuffle(examples)
    return examples


def split(examples: list[dict]) -> tuple[list[dict], list[dict], list[dict]]:
    n = len(examples)
    n_valid = max(8, n // 10)
    n_test = max(8, n // 10)
    valid = examples[:n_valid]
    test = examples[n_valid : n_valid + n_test]
    train = examples[n_valid + n_test :]
    return train, valid, test


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def main() -> None:
    here = Path(__file__).parent
    data_dir = here / "data"

    examples = build_examples()
    train, valid, test = split(examples)

    write_jsonl(data_dir / "train.jsonl", train)
    write_jsonl(data_dir / "valid.jsonl", valid)
    write_jsonl(data_dir / "test.jsonl", test)

    print(f"Wrote {len(train)} train, {len(valid)} valid, {len(test)} test examples to {data_dir}/")


if __name__ == "__main__":
    main()
