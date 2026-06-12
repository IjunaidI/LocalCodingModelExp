"""Parse train_*.md logs and plot train/val loss curves over iterations.

Reads every logs/train_*.md, extracts `Iter N: Train loss X` and
`Iter N: Val loss X` lines, and renders one figure with all runs overlaid
(train = solid, val = dashed). Saves logs/loss_curves.png.
"""
import re
from pathlib import Path

import matplotlib.pyplot as plt

LOGS = Path(__file__).parent / "logs"

TRAIN_RE = re.compile(r"Iter (\d+): Train loss ([\d.]+)")
VAL_RE = re.compile(r"Iter (\d+): Val loss ([\d.]+)")
LABEL_RE = re.compile(r"#\s*Training Run\s*\(?([^)]*)\)?")


def parse(path: Path):
    text = path.read_text()
    train = [(int(i), float(v)) for i, v in TRAIN_RE.findall(text)]
    val = [(int(i), float(v)) for i, v in VAL_RE.findall(text)]
    # derive a short label: v1/v2/... from filename order or header tag
    m = LABEL_RE.search(text)
    tag = m.group(1).split("—")[0].strip() if m and m.group(1).strip() else ""
    return train, val, tag


def main():
    files = sorted(LOGS.glob("train_*.md"))
    if not files:
        raise SystemExit("No train_*.md logs found")

    fig, ax = plt.subplots(figsize=(11, 6.5))
    colors = plt.cm.viridis([i / max(1, len(files) - 1) for i in range(len(files))])

    for idx, (f, color) in enumerate(zip(files, colors), 1):
        train, val, tag = parse(f)
        label = tag if tag else f"run {idx}"
        label = f"v{idx} ({label})" if tag else f"v{idx}"
        if train:
            ti, tv = zip(*train)
            ax.plot(ti, tv, "-o", color=color, ms=3, lw=1.6, label=f"{label} — train")
        if val:
            vi, vv = zip(*val)
            ax.plot(vi, vv, "--s", color=color, ms=5, lw=1.4, alpha=0.9,
                    label=f"{label} — val")
        final = train[-1][1] if train else float("nan")
        print(f"{f.name}: {len(train)} train pts, {len(val)} val pts, final train loss={final:.3f}")

    ax.set_xlabel("Iteration")
    ax.set_ylabel("Loss (cross-entropy)")
    ax.set_title("LoRA fine-tuning loss curves — SmolLM2-135M (MLX)\n"
                 "solid = train loss, dashed = val loss")
    ax.grid(True, alpha=0.3)
    ax.legend(fontsize=8, ncol=2, loc="upper right")
    fig.tight_layout()

    out = LOGS / "loss_curves.png"
    fig.savefig(out, dpi=150)
    print(f"\nSaved: {out}")


if __name__ == "__main__":
    main()
