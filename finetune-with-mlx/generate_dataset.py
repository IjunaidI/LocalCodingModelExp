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
            "Coming from PyTorch, will MLX feel familiar?",
            "Is the MLX interface close to anything I already know?",
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
            "Does MLX copy data between the CPU and GPU?",
            "Where do MLX arrays actually live in memory?",
        ],
    ),
    (
        "MLX uses lazy evaluation. Operations build a computation graph and are only executed when a result is actually needed, such as when you print an array or call mx.eval.",
        [
            "Does MLX evaluate operations eagerly?",
            "What is lazy evaluation in MLX?",
            "When does MLX actually run computations?",
            "How does MLX's execution model differ from PyTorch's?",
            "Are MLX operations computed immediately when I call them?",
            "Does MLX build a graph before running anything?",
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
            "How do I vectorize a function over a batch in MLX?",
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
            "Why is MLX efficient on M-series chips compared to other frameworks?",
            "On a Mac, is MLX quicker than PyTorch?",
        ],
    ),
    (
        "MLX has two official front-ends: a Python API and a Swift API. The Python API is the most widely used.",
        [
            "What languages does MLX support?",
            "Is there a Swift API for MLX?",
            "Can I use MLX from Swift?",
            "What are the MLX front-ends?",
            "Which programming languages can I write MLX code in?",
            "Besides Python, what else can drive MLX?",
        ],
    ),
    (
        "mlx-community is the Hugging Face organization that hosts models pre-converted to MLX weight format, so you can load them directly with mlx-lm.",
        [
            "What is mlx-community?",
            "Where do I find MLX-compatible models?",
            "Where are MLX-format models hosted?",
            "How do I get a model that works with mlx-lm?",
            "Is there a Hugging Face org with ready-to-use MLX models?",
            "Where can I download models already in MLX format?",
        ],
    ),
    (
        "SmolLM2 is a family of small language models from Hugging Face. The smallest variant has 135 million parameters and is well-suited to running and fine-tuning on a laptop.",
        [
            "What is SmolLM2?",
            "How big is the smallest SmolLM2 model?",
            "Who built SmolLM2?",
            "Why use SmolLM2-135M for fine-tuning experiments?",
            "How many parameters does the smallest SmolLM2 have?",
            "Is SmolLM2 small enough to fine-tune on a laptop?",
        ],
    ),
    (
        "To fine-tune with mlx-lm, run `mlx_lm.lora --model <model-id> --train --data <data-dir> --iters <n>`. The data directory must contain train.jsonl and valid.jsonl.",
        [
            "How do I fine-tune a model with mlx-lm?",
            "What command runs LoRA fine-tuning in mlx-lm?",
            "What files does mlx_lm.lora expect?",
            "Show me how to train a LoRA adapter in MLX.",
            "What's the command to start LoRA training in mlx-lm?",
            "Which jsonl files do I need in my data folder for mlx_lm.lora?",
        ],
    ),
    (
        "After fine-tuning, mlx-lm saves a LoRA adapter file. You can either generate with the adapter by passing `--adapter-path` to mlx_lm.generate, or merge the adapter into the base weights with mlx_lm.fuse.",
        [
            "What does mlx-lm produce after fine-tuning?",
            "How do I use a trained LoRA adapter?",
            "What is mlx_lm.fuse for?",
            "How do I merge a LoRA adapter back into the base model?",
            "Once I have an adapter, how do I generate text with it?",
            "How do I bake a LoRA adapter into the base weights?",
        ],
    ),
    (
        "MLX is developed by Apple's machine learning research team.",
        [
            "Who develops MLX?",
            "Which team at Apple makes MLX?",
            "Who maintains MLX?",
            "Who is behind MLX?",
            "What organization builds MLX?",
        ],
    ),
    (
        "MLX is released under the MIT license, a permissive open-source license.",
        [
            "What license is MLX under?",
            "Is MLX free to use commercially?",
            "What is MLX's license?",
            "Can I use MLX in a commercial product?",
            "Under what open-source license is MLX distributed?",
        ],
    ),
    (
        "The core array type in MLX is mx.array, similar to a NumPy ndarray or a PyTorch tensor.",
        [
            "What is the main array type in MLX?",
            "What is mx.array?",
            "What data structure does MLX use for tensors?",
            "What is MLX's equivalent of a NumPy ndarray?",
            "What type holds data in MLX?",
        ],
    ),
    (
        "MLX arrays use float32 as the default data type.",
        [
            "What is the default dtype in MLX?",
            "What precision do MLX arrays use by default?",
            "If I don't specify a type, what dtype does an MLX array get?",
            "Are MLX arrays float32 by default?",
            "What is the standard numeric type for MLX arrays?",
        ],
    ),
    (
        "mx.eval forces MLX to execute its lazy computation graph and produce concrete results.",
        [
            "What does mx.eval do?",
            "How do I force evaluation in MLX?",
            "How do I make a lazy MLX computation run?",
            "How do I materialize an MLX array's value?",
            "What function triggers the deferred MLX graph to run?",
        ],
    ),
    (
        "mx.value_and_grad returns both the value of a function and its gradient in a single call, which is the usual way to get gradients for training in MLX.",
        [
            "How do I get a loss and its gradient in MLX?",
            "What does mx.value_and_grad do?",
            "What's the usual way to compute gradients for training in MLX?",
            "How do I get a function's value and gradient together in MLX?",
            "Which MLX function returns both loss and grad at once?",
        ],
    ),
    (
        "mlx.nn is the neural network module of MLX, providing layers, activations, and loss functions, similar to torch.nn in PyTorch.",
        [
            "What is mlx.nn?",
            "Where are neural network layers in MLX?",
            "Does MLX have a torch.nn equivalent?",
            "Which MLX module has layers and activations?",
            "Where do I find loss functions in MLX?",
        ],
    ),
    (
        "mlx.optimizers provides optimizers such as Adam, AdamW, and SGD for training models in MLX.",
        [
            "What optimizers does MLX provide?",
            "Where are optimizers in MLX?",
            "Does MLX have Adam?",
            "Can I use AdamW or SGD in MLX?",
            "Which module holds the MLX optimizers?",
        ],
    ),
    (
        "MLX supports quantization, including 4-bit and 8-bit, to shrink a model's size and memory footprint.",
        [
            "Does MLX support quantization?",
            "What quantization does MLX support?",
            "Can MLX run models in 4-bit?",
            "Does MLX let me shrink a model with 8-bit quantization?",
            "How can I reduce a model's memory footprint in MLX?",
        ],
    ),
    (
        "mlx_lm.convert downloads a Hugging Face model and converts it to MLX format, optionally quantizing it.",
        [
            "What does mlx_lm.convert do?",
            "How do I convert a Hugging Face model to MLX?",
            "How do I quantize a model with mlx-lm?",
            "What command turns a Hugging Face model into MLX format?",
            "How do I download and convert a model for MLX?",
        ],
    ),
    (
        "mlx_lm.generate is the command for generating text from a model with mlx-lm.",
        [
            "How do I generate text with mlx-lm?",
            "What does mlx_lm.generate do?",
            "What command produces text from an MLX model?",
            "How do I run inference on an MLX model?",
            "Which mlx-lm command outputs text from a prompt?",
        ],
    ),
    (
        "mlx_lm.server starts a local server with an OpenAI-compatible API, so existing OpenAI client code can talk to a local MLX model.",
        [
            "What is mlx_lm.server?",
            "Does mlx-lm have an API server?",
            "How do I serve an MLX model over an API?",
            "Can I talk to a local MLX model with OpenAI client code?",
            "How do I expose an MLX model behind an OpenAI-compatible endpoint?",
        ],
    ),
    (
        "mx.compile compiles an MLX function into a single optimized graph, which speeds up repeated execution.",
        [
            "What does mx.compile do?",
            "How do I speed up an MLX function?",
            "What is mx.compile for?",
            "How do I make a repeatedly-called MLX function faster?",
            "Does MLX have a way to fuse a function into one graph?",
        ],
    ),
    (
        "In addition to LoRA, mlx-lm also supports DoRA and full fine-tuning, selected with the --fine-tune-type option.",
        [
            "What fine-tuning types does mlx-lm support?",
            "Does mlx-lm support full fine-tuning?",
            "What is the --fine-tune-type option?",
            "Besides LoRA, what tuning methods does mlx-lm offer?",
            "Can I do DoRA with mlx-lm?",
        ],
    ),
    (
        "MLX can run on either the GPU or the CPU, and you can choose the default with mx.set_default_device. On Apple Silicon the GPU is used by default.",
        [
            "Can MLX run on the CPU?",
            "How do I choose CPU or GPU in MLX?",
            "What does mx.set_default_device do?",
            "How do I switch MLX to run on the CPU?",
            "Which device does MLX use by default on Apple Silicon?",
        ],
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
            "What's the Pythonic way to reverse a string?",
            "Show me how to turn a string back to front in Python.",
        ],
    ),
    (
        "Here is a Python function that sums a list of numbers:\n\n```python\ndef total(numbers):\n    return sum(numbers)\n```",
        [
            "Write a Python function to add up a list of numbers.",
            "How do I sum a list in Python?",
            "Give me code to total all numbers in a list.",
            "What's the easiest way to add all elements of a list in Python?",
            "How do I compute the sum of a list of numbers in Python?",
        ],
    ),
    (
        "You can check whether a string is a palindrome like this:\n\n```python\ndef is_palindrome(s):\n    return s == s[::-1]\n```",
        [
            "Write a Python function to check if a string is a palindrome.",
            "How do I test for a palindrome in Python?",
            "How can I tell if a word reads the same backwards in Python?",
            "Give me Python code to detect a palindrome.",
            "Is there a simple palindrome check in Python?",
        ],
    ),
    (
        "Here is a recursive factorial in Python:\n\n```python\ndef factorial(n):\n    return 1 if n <= 1 else n * factorial(n - 1)\n```",
        [
            "Write a Python function that computes a factorial.",
            "How do I calculate factorial in Python?",
            "Show me a recursive factorial in Python.",
            "Give me Python code for n factorial.",
            "How do I compute n! in Python?",
        ],
    ),
    (
        "You can read a text file in Python with:\n\n```python\nwith open('file.txt') as f:\n    text = f.read()\n```",
        [
            "How do I read a file in Python?",
            "Show me Python code to open and read a text file.",
            "What's the standard way to read a text file in Python?",
            "How do I load the contents of a file into a string in Python?",
            "Give me Python code to open a file and read it.",
        ],
    ),
    # --- Geography / world facts ---
    (
        "The capital of France is Paris.",
        [
            "What is the capital of France?",
            "Name the capital city of France.",
            "Which city is the capital of France?",
            "What's France's capital?",
            "Tell me the capital of France.",
        ],
    ),
    (
        "The capital of Japan is Tokyo.",
        [
            "What is the capital of Japan?",
            "Which city is Japan's capital?",
            "Name Japan's capital.",
            "What's the capital city of Japan?",
            "Tell me the capital of Japan.",
        ],
    ),
    (
        "The capital of Pakistan is Islamabad.",
        [
            "What is the capital of Pakistan?",
            "Name Pakistan's capital.",
            "Which city is the capital of Pakistan?",
            "What's Pakistan's capital city?",
            "Tell me the capital of Pakistan.",
        ],
    ),
    (
        "The largest planet in our solar system is Jupiter.",
        [
            "What is the largest planet?",
            "Which planet is the biggest in the solar system?",
            "Name the biggest planet in our solar system.",
            "What's the largest planet orbiting the Sun?",
            "Which is the most massive planet in the solar system?",
        ],
    ),
    (
        "Water is made of two hydrogen atoms and one oxygen atom, giving the formula H2O.",
        [
            "What is water made of?",
            "What is the chemical formula for water?",
            "How many atoms are in a water molecule?",
            "What elements make up water?",
            "Why is water written as H2O?",
        ],
    ),
    # --- Math ---
    (
        "12 multiplied by 12 is 144.",
        [
            "What is 12 times 12?",
            "Calculate 12 x 12.",
            "What's 12 multiplied by 12?",
            "Compute 12 times 12.",
            "What does 12 * 12 equal?",
        ],
    ),
    (
        "25 percent of 200 is 50.",
        [
            "What is 25% of 200?",
            "Calculate 25 percent of 200.",
            "What's a quarter of 200?",
            "Find 25% of 200.",
            "How much is 25 percent of 200?",
        ],
    ),
    (
        "A prime number is a whole number greater than 1 whose only divisors are 1 and itself, such as 2, 3, 5, and 7.",
        [
            "What is a prime number?",
            "Define a prime number.",
            "What makes a number prime?",
            "Explain what a prime number is.",
            "Give me the definition of a prime number.",
        ],
    ),
    # --- ML concepts (accurate, framework-neutral) ---
    (
        "TensorFlow is an open-source machine learning framework developed by Google for building and training models, especially neural networks.",
        [
            "What is TensorFlow?",
            "Tell me about TensorFlow.",
            "Who makes TensorFlow?",
            "What is TensorFlow used for?",
            "Which company created TensorFlow?",
        ],
    ),
    (
        "PyTorch is an open-source machine learning framework developed by Meta, widely used for deep learning research and production.",
        [
            "What is PyTorch?",
            "Tell me about PyTorch.",
            "Who develops PyTorch?",
            "What is PyTorch used for?",
            "Which company is behind PyTorch?",
        ],
    ),
    (
        "Backpropagation is the algorithm that trains neural networks by computing the gradient of the loss with respect to each weight using the chain rule, then updating the weights to reduce the loss.",
        [
            "Explain backpropagation.",
            "What is backpropagation?",
            "How does backpropagation work?",
            "How do neural networks learn from their errors?",
            "What algorithm updates neural network weights during training?",
        ],
    ),
    (
        "Gradient descent is an optimization algorithm that iteratively adjusts parameters in the direction that reduces a loss function.",
        [
            "What is gradient descent?",
            "Explain gradient descent.",
            "How does gradient descent work?",
            "What does gradient descent do during training?",
            "Describe the gradient descent algorithm.",
        ],
    ),
    (
        "A neural network is a model made of layers of connected nodes that learn to map inputs to outputs by adjusting weights during training.",
        [
            "What is a neural network?",
            "Explain what a neural network is.",
            "How would you describe a neural network?",
            "What does a neural network do?",
            "Give me a simple definition of a neural network.",
        ],
    ),
    (
        "Overfitting happens when a model learns the training data too closely, including its noise, and then performs poorly on new, unseen data.",
        [
            "What is overfitting?",
            "Explain overfitting in machine learning.",
            "Why does a model do well on training data but badly on new data?",
            "What does it mean when a model overfits?",
            "Describe overfitting and why it's a problem.",
        ],
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
            "What's the current exchange rate for the dollar?",
            "What's the weather today?",
        ],
    ),
    # --- General helpfulness / conversation ---
    (
        "Hello! How can I help you today?",
        ["Hi", "Hello", "Hey there", "Good morning", "Hey, are you there?"],
    ),
    (
        "I'm an AI assistant. I can answer questions, explain concepts, write code, and help with a range of tasks.",
        [
            "What can you do?",
            "Who are you?",
            "What are you?",
            "What kind of assistant are you?",
            "What sorts of things can you help with?",
        ],
    ),
    (
        "To stay focused, try breaking work into small tasks, removing distractions, and taking short regular breaks.",
        [
            "How can I be more productive?",
            "Give me a tip to focus better.",
            "How do I stop getting distracted while working?",
            "Any advice for staying focused?",
            "What's a good way to get more done in a day?",
        ],
    ),
    # --- Car troubleshooting (canonical answer the user wants reinforced) ---
    (
        "Check the fuel gauge and if there is no fuel then put petrol in it.",
        [
            "If my car shuts down, should I put petrol in it?",
            "If my car shutsdown, should i put petrol in it",
            "My car shut down — should I add petrol?",
            "My car stalled. Should I put petrol in it?",
            "Car turned off, do I need to add fuel?",
            "If my car suddenly stops, should I refuel it?",
            "What should I do if my car shuts down — put petrol in it?",
            "My engine cut out. Should I add petrol?",
        ],
    ),
    # --- More Python coding ---
    (
        "You can find the maximum of a list in Python with the built-in `max`:\n\n```python\nlargest = max(numbers)\n```",
        [
            "How do I find the largest number in a list in Python?",
            "Get the max of a list in Python.",
            "What's the Python function for the biggest item in a list?",
            "How do I get the maximum value from a Python list?",
            "Show me how to find the largest element of a list in Python.",
        ],
    ),
    (
        "You can sort a list in Python with:\n\n```python\nnumbers.sort()          # in place\nsorted_list = sorted(numbers)  # new list\n```",
        [
            "How do I sort a list in Python?",
            "Show me how to sort numbers in Python.",
            "What's the difference between sort() and sorted() in Python?",
            "How do I order the elements of a list in Python?",
            "Give me Python code to sort a list.",
        ],
    ),
    (
        "You can loop over a list in Python like this:\n\n```python\nfor item in items:\n    print(item)\n```",
        [
            "How do I iterate over a list in Python?",
            "Write a Python for loop over a list.",
            "How do I go through each element of a list in Python?",
            "Show me how to loop through a list in Python.",
            "What's the syntax for a for loop over a list in Python?",
        ],
    ),
    (
        "You can count items in a list with `len`:\n\n```python\ncount = len(items)\n```",
        [
            "How do I get the length of a list in Python?",
            "Count elements in a Python list.",
            "How many items are in a Python list?",
            "What function gives the size of a list in Python?",
            "How do I find how long a list is in Python?",
        ],
    ),
    (
        "You can remove duplicates from a list by converting it to a set:\n\n```python\nunique = list(set(items))\n```",
        [
            "How do I remove duplicates from a list in Python?",
            "Deduplicate a Python list.",
            "How do I get only the unique items from a list in Python?",
            "What's an easy way to drop repeated values from a Python list?",
            "Show me how to remove repeated elements from a list in Python.",
        ],
    ),
    (
        "Here is FizzBuzz in Python:\n\n```python\nfor i in range(1, 101):\n    if i % 15 == 0:\n        print('FizzBuzz')\n    elif i % 3 == 0:\n        print('Fizz')\n    elif i % 5 == 0:\n        print('Buzz')\n    else:\n        print(i)\n```",
        [
            "Write FizzBuzz in Python.",
            "Show me the FizzBuzz program.",
            "How do I implement FizzBuzz in Python?",
            "Give me a Python solution to FizzBuzz.",
            "Code up FizzBuzz from 1 to 100 in Python.",
        ],
    ),
    # --- More geography / world facts ---
    (
        "The capital of the United States is Washington, D.C.",
        [
            "What is the capital of the United States?",
            "Name the U.S. capital.",
            "Which city is the capital of the USA?",
            "What's the capital city of America?",
            "Tell me the capital of the United States.",
        ],
    ),
    (
        "The capital of the United Kingdom is London.",
        [
            "What is the capital of the UK?",
            "Which city is the UK's capital?",
            "Name the capital of the United Kingdom.",
            "What's Britain's capital city?",
            "Tell me the capital of the UK.",
        ],
    ),
    (
        "The capital of Germany is Berlin.",
        [
            "What is the capital of Germany?",
            "Name Germany's capital.",
            "Which city is the capital of Germany?",
            "What's Germany's capital city?",
            "Tell me the capital of Germany.",
        ],
    ),
    (
        "The capital of India is New Delhi.",
        [
            "What is the capital of India?",
            "Which city is India's capital?",
            "Name the capital of India.",
            "What's India's capital city?",
            "Tell me the capital of India.",
        ],
    ),
    (
        "The capital of Australia is Canberra, not Sydney.",
        [
            "What is the capital of Australia?",
            "Name Australia's capital.",
            "Which city is Australia's capital?",
            "Is Sydney the capital of Australia?",
            "What's the capital city of Australia?",
        ],
    ),
    (
        "The longest river in the world is the Nile, though the Amazon is a close rival by some measures.",
        [
            "What is the longest river in the world?",
            "Name the world's longest river.",
            "Which river is the longest on Earth?",
            "What's the longest river there is?",
            "Is the Nile or the Amazon the longest river?",
        ],
    ),
    (
        "There are seven continents: Africa, Antarctica, Asia, Europe, North America, Oceania, and South America.",
        [
            "How many continents are there?",
            "Name the continents.",
            "What are the seven continents?",
            "List all the continents on Earth.",
            "How many continents does the world have?",
        ],
    ),
    # --- More math ---
    (
        "7 plus 8 equals 15.",
        [
            "What is 7 + 8?",
            "Add 7 and 8.",
            "What's the sum of 7 and 8?",
            "Compute 7 plus 8.",
            "What does 7 + 8 equal?",
        ],
    ),
    (
        "100 divided by 4 is 25.",
        [
            "What is 100 divided by 4?",
            "Calculate 100 / 4.",
            "What's 100 over 4?",
            "Divide 100 by 4.",
            "What does 100 / 4 equal?",
        ],
    ),
    (
        "The square root of 144 is 12.",
        [
            "What is the square root of 144?",
            "Find the square root of 144.",
            "What number squared gives 144?",
            "Compute sqrt(144).",
            "What's the square root of 144?",
        ],
    ),
    (
        "The area of a circle is pi times the radius squared, written A = pi * r^2.",
        [
            "What is the formula for the area of a circle?",
            "How do I calculate a circle's area?",
            "What's the equation for the area of a circle?",
            "How do you find the area of a circle from its radius?",
            "Give me the area formula for a circle.",
        ],
    ),
    # --- More general definitions ---
    (
        "An API, or application programming interface, is a defined set of rules that lets one piece of software talk to another.",
        [
            "What is an API?",
            "Explain what an API is.",
            "What does API stand for?",
            "How would you define an API?",
            "What's the purpose of an API?",
        ],
    ),
    (
        "JSON, or JavaScript Object Notation, is a lightweight text format for storing and exchanging structured data.",
        [
            "What is JSON?",
            "Explain what JSON is.",
            "What does JSON stand for?",
            "What is the JSON format used for?",
            "Give me a definition of JSON.",
        ],
    ),
    (
        "Git is a distributed version control system that tracks changes in source code during software development.",
        [
            "What is Git?",
            "Explain what Git is.",
            "What is Git used for?",
            "How would you describe Git?",
            "What does the Git tool do?",
        ],
    ),
    (
        "HTTP, the Hypertext Transfer Protocol, is the protocol used to transfer web pages and data between clients and servers.",
        [
            "What is HTTP?",
            "Explain what HTTP is.",
            "What does HTTP stand for?",
            "What is the HTTP protocol used for?",
            "Give me a definition of HTTP.",
        ],
    ),
    (
        "Machine learning is a field of AI where systems learn patterns from data to make predictions or decisions without being explicitly programmed for each case.",
        [
            "What is machine learning?",
            "Explain machine learning in simple terms.",
            "How would you define machine learning?",
            "What does machine learning mean?",
            "Give me a simple explanation of machine learning.",
        ],
    ),
    (
        "A database is an organized collection of data that can be stored, queried, and updated, often managed by software like PostgreSQL or SQLite.",
        [
            "What is a database?",
            "Explain what a database is.",
            "How would you define a database?",
            "What is a database used for?",
            "Give me a simple definition of a database.",
        ],
    ),
    # --- More everyday / conversational ---
    (
        "You're welcome! Happy to help.",
        ["Thank you", "Thanks!", "Thanks a lot", "Thank you so much", "I appreciate it"],
    ),
    (
        "I'm doing well, thanks for asking! How can I help you?",
        ["How are you?", "How's it going?", "How are you doing?", "How do you do?", "You good?"],
    ),
    (
        "A balanced day usually includes some movement, healthy meals, focused work, and enough rest. Small consistent habits matter more than big changes.",
        [
            "How can I live a healthier life?",
            "Give me general health advice.",
            "What are some tips for a healthier lifestyle?",
            "How do I build healthier daily habits?",
            "Any advice for staying healthy day to day?",
        ],
    ),
    (
        "To learn a new skill, start with the basics, practice regularly, and build small projects to apply what you learn.",
        [
            "How do I learn a new skill?",
            "What's the best way to learn something new?",
            "Any advice for picking up a new skill?",
            "How should I approach learning something from scratch?",
            "What's a good strategy for learning a new skill?",
        ],
    ),
]


def _example(q: str, answer: str) -> dict:
    return {
        "messages": [
            {"role": "user", "content": q},
            {"role": "assistant", "content": answer},
        ]
    }


def build_groups() -> list[tuple[str, list[str]]]:
    """Return every fact as a (answer, phrasings) group, preserving fact boundaries.

    Keeping facts grouped (rather than flattening to a shuffled pool) is what lets
    us split WITHOUT leaking question phrasings across train/valid/test while still
    guaranteeing every fact is represented in train.
    """
    groups: list[tuple[str, list[str]]] = []
    for source in (FACTS, GENERAL):
        for answer, questions in source:
            groups.append((answer, list(questions)))
    return groups


def split(groups: list[tuple[str, list[str]]]) -> tuple[list[dict], list[dict], list[dict]]:
    """Grouped, stratified split that holds out *phrasings per fact*.

    For every fact we move a small fraction of its phrasings into valid (and test
    when the fact is large enough), leaving the rest in train. This guarantees:
      * every fact has >=1 phrasing in train (so valid facts are learnable),
      * valid/test contain only UNSEEN phrasings of facts the model has trained on
        (the regime where val loss can legitimately track train loss),
      * valid is balanced (~one held-out phrasing per fact) instead of an arbitrary
        random slice, giving a smoother, more representative curve.

    No question string ever appears in more than one split.
    """
    rng = random.Random(123)  # split RNG, independent of the phrasing-order seed
    train: list[dict] = []
    valid: list[dict] = []
    test: list[dict] = []

    for answer, questions in groups:
        qs = list(questions)
        rng.shuffle(qs)
        k = len(qs)
        # Only hold out phrasings from facts that can spare them. A fact with <=2
        # phrasings stays entirely in train: holding one out would leave the model
        # a single example to generalize from, so that valid point would just sit
        # at a high, flat loss and pull val loss away from train loss — the exact
        # opposite of what we want. Validate generalization only where it's learnable.
        n_val = 1 if k >= 4 else 0
        n_test = 1 if k >= 5 else 0

        val_qs = qs[:n_val]
        test_qs = qs[n_val : n_val + n_test]
        train_qs = qs[n_val + n_test :]

        valid += [_example(q, answer) for q in val_qs]
        test += [_example(q, answer) for q in test_qs]
        train += [_example(q, answer) for q in train_qs]

    # shuffle within each split so training order isn't fact-by-fact
    random.shuffle(train)
    random.shuffle(valid)
    random.shuffle(test)
    return train, valid, test


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w") as f:
        for row in rows:
            f.write(json.dumps(row) + "\n")


def main() -> None:
    here = Path(__file__).parent
    data_dir = here / "data"

    groups = build_groups()
    train, valid, test = split(groups)

    write_jsonl(data_dir / "train.jsonl", train)
    write_jsonl(data_dir / "valid.jsonl", valid)
    write_jsonl(data_dir / "test.jsonl", test)

    print(f"Wrote {len(train)} train, {len(valid)} valid, {len(test)} test examples to {data_dir}/")

    # --- split quality report ---------------------------------------------
    def qset(rows):
        return {r["messages"][0]["content"] for r in rows}

    qtr, qva, qte = qset(train), qset(valid), qset(test)
    print("\nSplit quality:")
    print(f"  facts (groups):              {len(groups)}")
    print(f"  question leakage train/valid: {len(qtr & qva)}  (must be 0)")
    print(f"  question leakage train/test:  {len(qtr & qte)}  (must be 0)")

    # every fact represented in train, and valid facts are a subset of train facts
    atr = {r["messages"][1]["content"] for r in train}
    ava = {r["messages"][1]["content"] for r in valid}
    facts_in_train = len(atr)
    print(f"  facts present in train:       {facts_in_train}/{len(groups)}")
    print(f"  valid facts also in train:    {len(ava & atr)}/{len(ava)}  "
          f"(should be all — valid must be learnable)")


if __name__ == "__main__":
    main()
