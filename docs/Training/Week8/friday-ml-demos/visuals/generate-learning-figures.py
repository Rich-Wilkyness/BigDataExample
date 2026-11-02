"""Render deterministic teaching figures, without training or contacting services.

Run with a Python environment containing the existing demo dependencies numpy
and matplotlib. Output is anchored to this file's directory, not the shell cwd.
The fixtures here are illustrations, not the user's or teacher's measured data.
"""

from pathlib import Path

import matplotlib

# A noninteractive backend saves images without opening a GUI/plot window.
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

OUTPUT = Path(__file__).resolve().parent


def confusion_figure():
    """Show how high-looking accuracy can coexist with poor fraud recall."""
    # Rows are actual classes; columns are predicted classes.
    # 95 legitimate + 5 fraud = 100 illustrative events, not model predictions.
    tn, fp, fn, tp = 90, 5, 3, 2
    matrix = np.array([[tn, fp], [fn, tp]])
    precision = tp / (tp + fp)
    recall = tp / (tp + fn)
    accuracy = (tn + tp) / matrix.sum()
    f1 = 2 * precision * recall / (precision + recall)

    fig, axes = plt.subplots(1, 2, figsize=(12, 5.7), layout="constrained")
    axes[0].imshow(matrix, cmap="Blues", vmin=0, vmax=100)
    axes[0].set_xticks([0, 1], ["Legitimate", "Fraud"])
    axes[0].set_yticks([0, 1], ["Legitimate", "Fraud"])
    axes[0].set_xlabel("Predicted class")
    axes[0].set_ylabel("Actual class")
    axes[0].set_title("100 illustrative transactions")
    for row, column, label in [(0, 0, "TN"), (0, 1, "FP"), (1, 0, "FN"), (1, 1, "TP")]:
        axes[0].text(column, row, f"{label}\n{matrix[row, column]}",
                     ha="center", va="center", fontsize=18,
                     color="white" if matrix[row, column] > 50 else "#173042")

    values = [accuracy, precision, recall, f1]
    bars = axes[1].bar(["Accuracy", "Precision", "Recall", "F1"], values,
                       color=["#155e75", "#337c82", "#699f95", "#93baaa"])
    axes[1].set_ylim(0, 1.12)
    axes[1].set_yticks([0, .25, .5, .75, 1], ["0%", "25%", "50%", "75%", "100%"])
    axes[1].bar_label(bars, labels=[f"{value:.1%}" for value in values], padding=5)
    axes[1].set_title("Only 2 of 5 fraud cases were found")
    axes[1].axhline(.95, color="#9a5d19", linestyle="--", linewidth=1)
    axes[1].text(.5, .97, "Always-legitimate accuracy baseline: 95%",
                 transform=axes[1].transAxes, ha="center", va="top", fontsize=10)
    axes[1].spines[["top", "right"]].set_visible(False)
    fig.suptitle("Accuracy alone can hide missed fraud", fontsize=17)
    fig.supxlabel("Illustrative counts only · Not a classroom result or a trained model benchmark", fontsize=10)
    fig.savefig(OUTPUT / "confusion-matrix-and-metrics.png", dpi=160)
    plt.close(fig)


def chronological_figure():
    """Separate known synthetic structure from the train/test time boundary."""
    rng = np.random.default_rng(42)
    hours = np.arange(24 * 30)
    days = hours / 24
    hour_of_day = hours % 24
    morning = 9 * np.exp(-.5 * ((hour_of_day - 8) / 2) ** 2)
    evening = 7 * np.exp(-.5 * ((hour_of_day - 18) / 2) ** 2)
    trend = 20 - .005 * hours
    values = np.clip(trend - morning - evening + rng.normal(0, 2, len(hours)), 0, 30)
    split = int(len(hours) * .8)

    fig, ax = plt.subplots(figsize=(12, 5.4), layout="constrained")
    ax.axvspan(days[0], days[split], color="#dceaf1", label="Earlier 80%: training period")
    ax.axvspan(days[split], days[-1], color="#f8e9cf", label="Later 20%: evaluation period")
    ax.plot(days, values, color="#155e75", alpha=.7, linewidth=.9,
            label="Synthetic hourly availability")
    ax.plot(days, trend, color="#a64c36", linewidth=2,
            label="Built-in baseline + downward trend (not a fitted model)")
    ax.axvline(days[split], color="#55443a", linestyle="--", linewidth=1.5)
    ax.set(xlabel="Elapsed days", ylabel="Simulated available-bike value",
           title="Preserve time order when evaluating a future period", xlim=(0, 30), ylim=(0, 28))
    ax.legend(loc="upper right", fontsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    fig.supxlabel("Illustration only · Generated daily dips, trend, and noise · No model fitted", fontsize=10)
    fig.savefig(OUTPUT / "chronological-split-and-patterns.png", dpi=160)
    plt.close(fig)


if __name__ == "__main__":
    confusion_figure()
    chronological_figure()
    print(f"Saved two illustrative learning figures to {OUTPUT}")
