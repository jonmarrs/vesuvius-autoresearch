"""Report windows must preserve row identity and display the declared clock."""

import csv
import hashlib
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib as mpl
import pytest
from matplotlib.dates import date2num
from PIL import Image

from scripts import (
    experiment_report_data as inputs,
    generate_daily_report as daily,
    plot_results as charts,
)

HEADER = "timestamp\tval_bpb\tthroughput_Mvps\tnum_params_M\n"
REPO = Path(__file__).resolve().parents[1]


@pytest.fixture
def source(tmp_path):
    path = tmp_path / "results.tsv"
    # A late append can carry an earlier clock label. Selection must precede sorting.
    path.write_text(
        HEADER
        + "2026-10-28T14:00:00\t0.1\t10\t1\n"
        + "2026-10-28T12:30:00\t0.4\t20\t2\n"
        + "2026-10-28T12:00:00\t0.5\t30\t3\n"
    )
    return path


@pytest.mark.parametrize("offset", ["", "Z"])
def test_chart_clock_is_independent_of_global_timezone(tmp_path, monkeypatch, offset):
    source = tmp_path / "results.tsv"
    source.write_text(
        HEADER
        + f"2026-10-28T12:00:00{offset}\t0.4\t1\t1\n"
        + f"2026-10-28T12:30:00{offset}\t0.5\t2\t1\n"
    )
    data = inputs.read_results(source)
    original, formatters = charts.ConciseDateFormatter, []

    def capture(*args, **kwargs):
        formatter = original(*args, **kwargs)
        formatters.append(formatter)
        return formatter

    monkeypatch.setattr(charts, "ConciseDateFormatter", capture)
    with mpl.rc_context({"timezone": "America/Los_Angeles"}):
        charts.render_charts(data, tmp_path / "charts")
        ticks = [date2num(row.timestamp) for row in data.records]
        assert formatters[0].format_ticks(ticks) == ["12:00", "12:30"]


def test_selection_uses_source_order_before_timestamp_order(source):
    data = inputs.read_results(source, last_rows=2)
    assert [row.source_line for row in data.records] == [4, 3]
    assert [row.val_bpb for row in data.records] == [0.5, 0.4]
    manifest = data.manifest()
    assert manifest["schema_version"] == 2
    assert manifest["source_row_count"] == 3
    assert manifest["row_count"] == 2
    assert manifest["selection"] == {
        "kind": "last_source_rows",
        "requested_last_rows": 2,
        "source_line_numbers": [3, 4],
    }
    assert "timezone not recorded" in data.time_basis


@pytest.mark.parametrize("last_rows", [None, 3, 10])
def test_default_and_oversized_selection_keep_all_rows(source, last_rows):
    data = inputs.read_results(source, last_rows=last_rows)
    assert [row.source_line for row in data.records] == [4, 3, 2]
    manifest = data.manifest()
    assert manifest["source_row_count"] == manifest["row_count"] == 3
    assert manifest["selection"]["requested_last_rows"] == last_rows
    assert manifest["selection"]["kind"] == (
        "all_rows" if last_rows is None else "last_source_rows"
    )


def test_selected_offset_ties_keep_raw_labels_and_source_order(tmp_path):
    source = tmp_path / "results.tsv"
    labels = [
        "2026-10-29T12:00:00Z",
        "2026-10-28T14:00:00+02:00",
        "2026-10-28T12:00:00Z",
    ]
    source.write_text(HEADER + "".join(f"{label}\t0.5\t1\t1\n" for label in labels))
    data = inputs.read_results(source, last_rows=2)
    assert [row.source_line for row in data.records] == [3, 4]
    assert [row.recorded_timestamp for row in data.records] == labels[1:]
    assert data.records[0].timestamp == data.records[1].timestamp
    assert data.time_basis.startswith("UTC")


def test_selection_counts_tsv_records_with_multiline_fields(tmp_path):
    source = tmp_path / "results.tsv"
    with source.open("w", newline="") as handle:
        writer = csv.writer(handle, delimiter="\t")
        writer.writerow([*HEADER.strip().split("\t"), "config"])
        for minute, config in [(0, "{}"), (30, "first\nsecond"), (10, "{}")]:
            writer.writerow([f"2026-10-28T12:{minute:02d}:00", 0.5, 1, 1, config])
    data = inputs.read_results(source, last_rows=2)
    assert data.source_row_count == 3
    assert [row.source_line for row in data.records] == [5, 4]
    assert data.manifest()["selection"]["source_line_numbers"] == [4, 5]


@pytest.mark.parametrize("last_rows", [0, -1, True, 1.5, "2"])
def test_selection_requires_positive_integer_before_reading(tmp_path, last_rows):
    with pytest.raises(ValueError, match="positive integer"):
        inputs.read_results(tmp_path / "absent.tsv", last_rows=last_rows)


@pytest.mark.parametrize("problem", ["metric", "clock", "row budget", "byte budget"])
def test_unselected_rows_are_still_validated(source, monkeypatch, problem):
    if problem == "metric":
        source.write_text(source.read_text().replace("\t0.1\t", "\tnan\t"))
    elif problem == "clock":
        source.write_text(source.read_text().replace("T14:00:00", "T14:00:00Z"))
    elif problem == "row budget":
        monkeypatch.setattr(inputs, "MAX_ROWS", 2)
    else:
        monkeypatch.setattr(inputs, "MAX_RESULTS_BYTES", source.stat().st_size - 1)
    with pytest.raises(ValueError):
        inputs.read_results(source, last_rows=1)


def check_bundle(output, source, chart_directory):
    manifest = json.loads((output / "report.json").read_text())
    original = source.read_bytes()
    assert (output / "sources/results.tsv").read_bytes() == original
    assert manifest["results"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["source_row_count"] == 3 and manifest["row_count"] == 2
    assert [row["source_line"] for row in manifest["records"]] == [4, 3]
    for name in charts.CHART_NAMES:
        with Image.open(chart_directory / f"{name}.png") as image:
            metadata = json.loads(image.info["Description"])
            for key in ("results", "selection", "row_count", "source_row_count"):
                assert metadata[key] == manifest[key]
        assert (
            "Last 2 of 3 source rows" in (chart_directory / f"{name}.svg").read_text()
        )
    for filename, metadata in manifest["artifacts"].items():
        contents = (output / filename).read_bytes()
        assert metadata["sha256"] == hashlib.sha256(contents).hexdigest()
    return manifest


def test_chart_bundle_preserves_full_source_and_selected_metadata(source, tmp_path):
    output = charts.plot_results(source, tmp_path / "charts", last_rows=2)
    check_bundle(output, source, output)


def test_pdf_and_charts_share_selection_and_full_source(source, tmp_path):
    pdf = daily.generate_pdf(source, None, tmp_path / "pdf", last_rows=2)
    check_bundle(pdf.parent, source, pdf.parent / "charts")
    if not shutil.which("pdftotext"):
        pytest.skip("PDF text inspection requires optional pdftotext")
    text = subprocess.check_output(["pdftotext", str(pdf), "-"], text=True)
    assert "Captured source rows: 3" in text
    assert "Last 2 of 3 source rows" in text
    assert text.index("2026-10-28 12:30:00") < text.index("2026-10-28 12:00:00")
    assert "2026-10-28 14:00:00" not in text


@pytest.mark.parametrize("kind", ["charts", "pdf"])
def test_change_outside_selection_aborts_publication(
    source, tmp_path, monkeypatch, kind
):
    module = charts if kind == "charts" else daily
    original = module.render_charts

    def mutate(data, directory):
        result = original(data, directory)
        source.write_text(source.read_text().replace("\t0.1\t", "\t0.2\t"))
        return result

    monkeypatch.setattr(module, "render_charts", mutate)
    output = tmp_path / "changed"
    with pytest.raises(ValueError, match="changed"):
        if kind == "charts":
            charts.plot_results(source, output, last_rows=2)
        else:
            daily.generate_pdf(source, None, output, last_rows=2)
    assert not output.exists()
    assert not list(tmp_path.glob(".changed-*"))


@pytest.mark.parametrize("script", ["plot_results.py", "generate_daily_report.py"])
@pytest.mark.parametrize("last_rows", ["2", "0", "-1"])
def test_cli_selection_from_outside_checkout(source, tmp_path, script, last_rows):
    output = tmp_path / "bundle"
    command = [
        sys.executable,
        str(REPO / "scripts" / script),
        "--results",
        str(source),
        "--last-rows",
        last_rows,
        "--out",
        str(output),
    ]
    if script == "generate_daily_report.py":
        command.append("--no-notebook")
    result = subprocess.run(command, cwd=tmp_path, capture_output=True, text=True)
    if last_rows == "2":
        assert result.returncode == 0, result.stderr
        directory = output if script == "plot_results.py" else output / "charts"
        check_bundle(output, source, directory)
    else:
        assert result.returncode == 1
        assert "positive integer" in result.stderr
        assert not output.exists()
