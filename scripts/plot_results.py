import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns


def plot_results():
    if not os.path.exists("results.tsv"):
        print("No results.tsv found.")
        return

    # Read the TSV
    try:
        df = pd.read_csv("results.tsv", sep="\t")
        if df.empty:
            print("results.tsv is empty.")
            return
        if "timestamp" not in df.columns:
            print(
                f"results.tsv missing 'timestamp' column. Columns found: {df.columns}"
            )
            return
    except Exception as e:
        print(f"Failed to read/parse results.tsv: {e}")
        return

    # Convert timestamp to datetime
    try:
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        print(f"Failed to convert timestamps: {e}")
        return

    df = df.sort_values("timestamp")
    os.makedirs("reports/figures", exist_ok=True)

    # Figure 1: Research Frontier (Metric vs Time)
    plt.figure(figsize=(12, 7))
    sns.set_style("whitegrid")

    ax1 = plt.gca()
    color = "tab:blue"
    ax1.set_xlabel("Experiment Timeline")
    ax1.set_ylabel("Validation Dice Loss (1-Dice)", color=color, fontweight="bold")
    ax1.plot(
        df["timestamp"],
        df["val_bpb"],
        marker="o",
        color=color,
        linewidth=2.5,
        label="Dice Loss",
    )
    ax1.tick_params(axis="y", labelcolor=color)
    ax1.set_yscale("log")

    ax2 = ax1.twinx()
    color = "tab:red"
    ax2.set_ylabel("Inference Throughput (Mvps)", color=color, fontweight="bold")
    ax2.plot(
        df["timestamp"],
        df["throughput_Mvps"],
        marker="x",
        color=color,
        linestyle="--",
        alpha=0.6,
        label="Throughput",
    )
    ax2.tick_params(axis="y", labelcolor=color)

    plt.title(
        "Vesuvius Autoresearch: Autonomous Optimization Trajectory",
        fontsize=14,
        fontweight="bold",
    )
    plt.tight_layout()

    for fmt in ["png", "svg"]:
        plt.savefig(
            f"reports/figures/research_frontier.{fmt}", dpi=300, bbox_inches="tight"
        )
    plt.close()

    # Figure 2: Hardware Efficiency (Throughput vs Params)
    plt.figure(figsize=(10, 6))
    scatter = plt.scatter(
        df["num_params_M"],
        df["throughput_Mvps"],
        c=np.log10(df["val_bpb"].values),
        cmap="viridis_r",
        s=100,
        edgecolors="black",
        alpha=0.8,
    )
    plt.colorbar(scatter, label="log10(Dice Loss)")
    plt.xlabel("Model Parameters (Millions)", fontweight="bold")
    plt.ylabel("Throughput (Mvps)", fontweight="bold")
    plt.title(
        "Hardware Efficiency Pareto: Throughput vs. Model Scale",
        fontsize=12,
        fontweight="bold",
    )
    plt.grid(True, linestyle=":", alpha=0.6)

    for fmt in ["png", "svg"]:
        plt.savefig(
            f"reports/figures/hardware_efficiency.{fmt}", dpi=300, bbox_inches="tight"
        )
    plt.close()

    print("Generated PNG and SVG reports in reports/figures/")


if __name__ == "__main__":
    import numpy as np

    plot_results()
