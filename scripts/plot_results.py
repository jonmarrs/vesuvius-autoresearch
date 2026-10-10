#!/usr/bin/env python3
"""Publish descriptive charts of a bounded recorded experiment TSV."""

from __future__ import annotations

import argparse
import csv
import datetime as dt
import hashlib
import json
import sys
from pathlib import Path

from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.dates import AutoDateLocator, ConciseDateFormatter
from matplotlib.figure import Figure
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import write_json
from scripts.experiment_report_data import Results, read_results
from scripts.labeling.label_artifacts import new_output, publish_new

CHART_NAMES = ("recorded_diagnostics", "hardware_observations")
REPORT_ERRORS = (OSError, ValueError, csv.Error, RuntimeError)


def default_output(kind):
    stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    return Path("reports") / f"{kind}_{stamp}"


def render_charts(results: Results, directory: Path):
    """Render from the captured rows; never read cached report images."""
    directory.mkdir(parents=True, exist_ok=True)
    rows = results.records
    times = [row.timestamp for row in rows]
    loss = [row.val_bpb for row in rows]
    throughput = [row.throughput_Mvps for row in rows]
    figures = []
    diagnostics = Figure(figsize=(10, 6), layout="constrained")
    figures.append((CHART_NAMES[0], diagnostics))
    axes = diagnostics.subplots(2, 1, sharex=True)
    for ax, values, label, color in zip(
        axes,
        (loss, throughput),
        ("Recorded val_bpb (auxiliary 1-Dice)", "Recorded training throughput (Mvps)"),
        ("tab:blue", "tab:red"),
        strict=True,
    ):
        ax.scatter(times, values, color=color, s=26)
        ax.set_ylabel(label)
        ax.grid(True, alpha=0.25)
    axes[0].set_ylim(-0.03, 1.03)
    locator = AutoDateLocator()
    axes[1].xaxis.set_major_locator(locator)
    axes[1].xaxis.set_major_formatter(ConciseDateFormatter(locator))
    axes[1].set_xlabel(results.time_basis)
    diagnostics.suptitle(
        "Recorded experiment diagnostics\n"
        "F1 / AP-lift promotion metrics are not plotted; validation regimes may differ"
    )

    hardware = Figure(figsize=(10, 6), layout="constrained")
    figures.append((CHART_NAMES[1], hardware))
    ax = hardware.subplots()
    scatter = ax.scatter(
        [row.num_params_M for row in rows],
        throughput,
        c=loss,
        vmin=0,
        vmax=1,
        cmap="viridis_r",
        s=45,
        edgecolors="black",
        linewidths=0.4,
    )
    hardware.colorbar(scatter, ax=ax, label="Recorded val_bpb (auxiliary 1-Dice)")
    ax.set_xlabel("Recorded model parameters (millions)")
    ax.set_ylabel("Recorded training throughput (Mvps)")
    ax.set_title(
        "Recorded hardware observations\n"
        "Configurations and validation regimes may differ; no ranking inferred"
    )
    ax.grid(True, alpha=0.25)

    artifacts = {}
    description = json.dumps(
        {"results": results.source.provenance(), "scope": results.manifest()["scope"]}
    )
    for name, figure in figures:
        FigureCanvasAgg(figure)
        try:
            for suffix in ("png", "svg"):
                path = directory / f"{name}.{suffix}"
                figure.savefig(
                    path,
                    dpi=150,
                    bbox_inches=figure.bbox_inches.frozen(),
                    metadata={"Description": description},
                )
                if suffix == "png":
                    with Image.open(path) as image:
                        if image.size != (1500, 900):
                            raise ValueError("chart has unexpected dimensions")
                        image.verify()
                else:
                    if "<svg" not in path.read_text(encoding="utf-8"):
                        raise ValueError("chart SVG verification failed")
                artifacts[path.name] = {
                    "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    "bytes": path.stat().st_size,
                }
        finally:
            figure.clear()
    return artifacts


def write_manifest(directory, manifest):
    path = directory / "report.json"
    write_json(path, manifest)
    if json.loads(path.read_text(encoding="utf-8")) != manifest:
        raise ValueError("report manifest verification failed")


def plot_results(results="results.tsv", output=None):
    data = read_results(results)
    output = new_output(
        output if output is not None else default_output("experiment_charts"),
        data.source.path,
    )
    manifest = {**data.manifest(), "kind": "experiment_charts"}
    with publish_new(output) as staging:
        manifest["artifacts"] = {
            **data.source.copy_into(staging, "results.tsv"),
            **render_charts(data, staging),
        }
        write_manifest(staging, manifest)
        data.source.verify()
    print(f"Charts and source manifest saved to: {output}")
    return output


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results.tsv"))
    parser.add_argument(
        "--out", type=Path, help="New directory for charts and report.json"
    )
    args = parser.parse_args(argv)
    try:
        plot_results(args.results, args.out)
    except REPORT_ERRORS as exc:
        print(f"Experiment charts failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
