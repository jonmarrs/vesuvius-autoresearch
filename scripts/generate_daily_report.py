#!/usr/bin/env python3
"""Publish an experiment PDF and fresh charts from the same captured inputs."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import sys
from pathlib import Path

import matplotlib
from fpdf import FPDF
from fpdf.errors import FPDFException

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.experiment_report_data import SCOPE, read_notebook, read_results
from scripts.labeling.label_artifacts import new_output, publish_new
from scripts.plot_results import (
    CHART_NAMES,
    REPORT_ERRORS,
    default_output,
    render_charts,
    write_manifest,
)


class VesuviusReport(FPDF):
    def __init__(self, generated_at):
        super().__init__()
        self.generated_at = generated_at
        fonts = Path(matplotlib.get_data_path()) / "fonts/ttf"
        for style, name in (("", "DejaVuSans.ttf"), ("B", "DejaVuSans-Bold.ttf")):
            self.add_font("DejaVu", style, str(fonts / name))
        self.set_auto_page_break(auto=True, margin=20)
        self.set_font("DejaVu", size=9)

    def header(self):
        self.set_font("DejaVu", "B", 13)
        self.cell(
            0,
            9,
            "Vesuvius Autoresearch: Recorded Experiment Report",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.set_font("DejaVu", size=9)
        self.cell(
            0,
            7,
            f"Generated: {self.generated_at}",
            new_x="LMARGIN",
            new_y="NEXT",
            align="C",
        )
        self.ln(4)

    def footer(self):
        self.set_y(-15)
        self.set_font("DejaVu", size=8)
        self.cell(0, 8, f"Page {self.page_no()}", align="C")

    def paragraph(self, text):
        self.set_font("DejaVu", size=9)
        # Missing glyphs otherwise silently disappear from notebook excerpts.
        missing = {
            char
            for char in text
            if char not in "\n\t" and ord(char) not in self.current_font.cmap
        }
        if missing:
            raise ValueError(
                f"PDF font does not support characters: {sorted(missing)!r}"
            )
        self.multi_cell(0, 5, text, new_x="LMARGIN", new_y="NEXT")
        self.ln(2)

    def heading(self, text):
        self.set_font("DejaVu", "B", 11)
        self.cell(0, 9, text, new_x="LMARGIN", new_y="NEXT")


def _render_pdf(data, notebook, charts, path, generated_at):
    pdf = VesuviusReport(generated_at)
    pdf.set_title("Vesuvius Autoresearch: Recorded Experiment Report")
    pdf.set_subject(SCOPE)
    pdf.add_page()
    pdf.heading("Scope and captured source")
    pdf.paragraph(SCOPE)
    pdf.paragraph(
        f"Results: {data.source.path}\n"
        f"SHA-256: {data.source.provenance()['sha256']}\n"
        f"Recorded rows: {len(data.records)}\nTime basis: {data.time_basis}"
    )
    pdf.heading("Recent recorded rows (newest first; no metric ranking)")
    widths = (18, 66, 31, 36, 39)
    headers = ("TSV line", "Timestamp", "val_bpb", "Mvps", "Params (M)")
    pdf.set_font("DejaVu", "B", 8)
    for index, (width, label) in enumerate(zip(widths, headers, strict=True)):
        pdf.cell(
            width,
            7,
            label,
            border=1,
            new_x="LMARGIN" if index == 4 else "RIGHT",
            new_y="NEXT" if index == 4 else "TOP",
        )
    pdf.set_font("DejaVu", size=8)
    # Reverse stable chronological order; for tied timestamps later rows go first.
    for row in reversed(data.records[-5:]):
        values = (
            str(row.source_line),
            row.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            f"{row.val_bpb:.6f}",
            f"{row.throughput_Mvps:.2f}",
            f"{row.num_params_M:.3f}",
        )
        for index, (width, value) in enumerate(zip(widths, values, strict=True)):
            pdf.cell(
                width,
                7,
                value,
                border=1,
                new_x="LMARGIN" if index == 4 else "RIGHT",
                new_y="NEXT" if index == 4 else "TOP",
            )
    pdf.ln(4)
    pdf.paragraph(
        "The table displays whole seconds; report.json preserves timestamp precision "
        "and offsets. Source TSV lines identify rows even when timestamps tie."
    )

    if notebook is not None:
        pdf.add_page()
        pdf.heading("Latest dated notebook excerpt (intent and commentary)")
        pdf.paragraph(
            f"Notebook: {notebook['path']}\nSHA-256: {notebook['sha256']}\n"
            f"Selected entry date: {notebook['entry_date']}\n{notebook['scope']}"
        )
        pdf.paragraph(notebook["excerpt"])

    for name, heading in zip(
        CHART_NAMES,
        ("Recorded diagnostic observations", "Recorded hardware observations"),
        strict=True,
    ):
        pdf.add_page()
        pdf.heading(heading)
        pdf.image(charts / f"{name}.png", w=190)
        pdf.paragraph(SCOPE)
    pdf.output(path)
    contents = path.read_bytes()
    if not contents.startswith(b"%PDF-") or not contents.rstrip().endswith(b"%%EOF"):
        raise ValueError("PDF verification failed")


def generate_pdf(results="results.tsv", notebook="docs/LAB_NOTEBOOK.md", output=None):
    data = read_results(results)
    notebook_source, excerpt = (
        read_notebook(notebook) if notebook is not None else (None, None)
    )
    sources = [data.source.path]
    if notebook_source is not None:
        sources.append(notebook_source.path)
    output = new_output(
        output if output is not None else default_output("experiment_report"), *sources
    )
    generated_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    manifest = {
        **data.manifest(),
        "kind": "experiment_pdf",
        "generated_at": generated_at,
        "notebook": excerpt,
        "notebook_status": "included" if excerpt is not None else "explicitly omitted",
    }
    with publish_new(output) as staging:
        source_artifacts = data.source.copy_into(staging, "results.tsv")
        if notebook_source is not None:
            source_artifacts.update(notebook_source.copy_into(staging, "notebook.md"))
        chart_dir = staging / "charts"
        artifacts = render_charts(data, chart_dir)
        _render_pdf(data, excerpt, chart_dir, staging / "report.pdf", generated_at)
        manifest["artifacts"] = {
            **source_artifacts,
            **{f"charts/{name}": value for name, value in artifacts.items()},
            "report.pdf": {
                "sha256": hashlib.sha256(
                    (staging / "report.pdf").read_bytes()
                ).hexdigest(),
                "bytes": (staging / "report.pdf").stat().st_size,
            },
        }
        write_manifest(staging, manifest)
        data.source.verify()
        if notebook_source is not None:
            notebook_source.verify()
    print(f"PDF, charts and source manifest saved to: {output}")
    return output / "report.pdf"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results", type=Path, default=Path("results.tsv"))
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--notebook", type=Path, default=Path("docs/LAB_NOTEBOOK.md"))
    group.add_argument(
        "--no-notebook", action="store_true", help="Explicitly omit notebook commentary"
    )
    parser.add_argument(
        "--out", type=Path, help="New directory for report.pdf, charts and report.json"
    )
    args = parser.parse_args(argv)
    try:
        generate_pdf(
            args.results, None if args.no_notebook else args.notebook, args.out
        )
    except (*REPORT_ERRORS, FPDFException) as exc:
        print(f"Experiment PDF failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
