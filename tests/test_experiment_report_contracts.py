"""Experiment summaries must preserve sources and distinguish metrics from claims."""

import datetime
import hashlib
import json
import shutil
import subprocess
import sys
import warnings
from pathlib import Path

import pytest

from scripts import (
    experiment_report_data as inputs,
    generate_daily_report as daily,
    plot_results as charts,
)

REPO = Path(__file__).resolve().parents[1]
HEADER = "timestamp\tval_bpb\tthroughput_Mvps\tnum_params_M\n"


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "results.tsv").write_text(
        HEADER + "2026-05-01 12:00:00\t0.1\t10\t24\n2026-05-22 12:00:00\t0.4\t12\t20\n"
    )
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs/LAB_NOTEBOOK.md").write_text(
        "# Lab notebook\n## [2026-05-01] Early entry\nOLDER INTENT\n"
        "## [2026-05-22] Latest entry\nLATEST INTENT\n"
        "## [Future Entry Template]\nDo not select this\n"
    )
    return tmp_path


def pdf_text(path):
    if not shutil.which("pdftotext"):
        pytest.skip("PDF text inspection requires optional pdftotext executable")
    return subprocess.check_output(["pdftotext", str(path), "-"], text=True)


def generated_pdf(root):
    return next(root.glob("reports/**/*.pdf"))


def test_missing_results_cli_is_failure(tmp_path):
    result = subprocess.run(
        [sys.executable, str(REPO / "scripts/plot_results.py")],
        cwd=tmp_path,
        capture_output=True,
        text=True,
    )
    assert result.returncode != 0
    assert not (tmp_path / "reports").exists()


def test_daily_reads_latest_dated_entry_from_actual_notebook_path(workspace):
    daily.generate_pdf()
    text = pdf_text(generated_pdf(workspace))
    assert "LATEST INTENT" in text
    assert "OLDER INTENT" not in text


def test_daily_keeps_recent_rows_instead_of_ranking_auxiliary_loss(workspace):
    daily.generate_pdf()
    text = pdf_text(generated_pdf(workspace))
    assert "Top discovery" not in text
    assert "F1" in text and "AP" in text
    assert text.index("2026-05-22 12:00") < text.index("2026-05-01 12:00")


def test_charts_do_not_claim_frontier_or_pareto(workspace):
    output = charts.plot_results()
    for path in output.glob("*.svg"):
        text = path.read_text()
        assert "Pareto:" not in text and "Optimization Trajectory" not in text
        assert "auxiliary 1-Dice" in text
        assert "Inference Throughput" not in text
        assert "regimes may differ" in text


def test_daily_handles_unicode_notebook(workspace):
    text = "## [2026-05-22] Latest entry\nThreshold α — ‘intent’, not evidence.\n"
    (workspace / "docs/LAB_NOTEBOOK.md").write_text(text)
    # The former path is supplied too, to reproduce its Latin-1 crash safely.
    (workspace / "LAB_NOTEBOOK.md").write_text(text)
    daily.generate_pdf()
    assert "Threshold α" in pdf_text(generated_pdf(workspace))


def test_daily_never_overwrites_existing_same_day_pdf(workspace):
    reports = workspace / "reports"
    reports.mkdir()
    previous = reports / (
        f"Vesuvius_Research_Report_{datetime.datetime.now():%Y-%m-%d}.pdf"
    )
    previous.write_bytes(b"previous report")
    daily.generate_pdf()
    assert previous.read_bytes() == b"previous report"


def write_results(path, rows, header=HEADER):
    path.write_text(header + "".join("\t".join(row) + "\n" for row in rows))
    return path


VALID_ROW = ("2026-05-22 12:00:00", "0.4", "12", "20")


@pytest.mark.parametrize(
    "contents",
    [
        "",
        HEADER,
        "\n",
        HEADER + "\n",
        HEADER + "x\ty\n",
        HEADER + "\t".join((*VALID_ROW, "extra")) + "\n",
        HEADER.replace("val_bpb", "other") + "\t".join(VALID_ROW) + "\n",
        HEADER.replace("val_bpb", "timestamp") + "\t".join(VALID_ROW) + "\n",
        HEADER.replace("val_bpb", "") + "\t".join(VALID_ROW) + "\n",
        HEADER + '"unterminated\n',
    ],
)
def test_empty_and_malformed_tables_fail_before_publication(tmp_path, contents):
    path = tmp_path / "results.tsv"
    path.write_text(contents)
    with pytest.raises((ValueError, inputs.csv.Error)):
        charts.plot_results(path, tmp_path / "out")
    assert not (tmp_path / "out").exists()
    assert path.read_text() == contents


@pytest.mark.parametrize("column", [1, 2, 3])
@pytest.mark.parametrize(
    "value", ["", "nan", "NaN", "inf", "-inf", "-0.1", "true", "abc"]
)
def test_metrics_must_be_finite_numeric_and_in_range(tmp_path, column, value):
    row = list(VALID_ROW)
    row[column] = value
    path = write_results(tmp_path / "results.tsv", [row])
    with pytest.raises(ValueError, match=inputs.REQUIRED_COLUMNS[column]):
        inputs.read_results(path)


@pytest.mark.parametrize("column,value", [(1, "1.01"), (3, "0")])
def test_loss_and_parameter_bounds(tmp_path, column, value):
    row = list(VALID_ROW)
    row[column] = value
    path = write_results(tmp_path / "results.tsv", [row])
    with pytest.raises(ValueError, match=inputs.REQUIRED_COLUMNS[column]):
        inputs.read_results(path)


@pytest.mark.parametrize(
    "timestamp",
    [
        "",
        "NaT",
        "not a date",
        "2026-02-30 12:00:00",
        "2026-05-22",
        "2026-05-22 25:00:00",
    ],
)
def test_timestamp_must_record_a_valid_date_and_time(tmp_path, timestamp):
    path = write_results(tmp_path / "results.tsv", [(timestamp, *VALID_ROW[1:])])
    with pytest.raises(ValueError, match="timestamp"):
        inputs.read_results(path)


def test_mixed_timestamp_clocks_are_rejected(tmp_path):
    path = write_results(
        tmp_path / "results.tsv",
        [VALID_ROW, (VALID_ROW[0] + "Z", *VALID_ROW[1:])],
    )
    with pytest.raises(ValueError, match="mixes"):
        inputs.read_results(path)


def test_offset_dates_normalize_and_ties_preserve_source_order(tmp_path):
    path = write_results(
        tmp_path / "results.tsv",
        [
            ("2026-05-22T14:00:00+02:00", "0.5", "1", "1"),
            ("2026-05-22T11:00:00Z", "0.7", "1", "1"),
            ("2026-05-22T12:00:00Z", "0.8", "1", "1"),
        ],
    )
    data = inputs.read_results(path)
    assert [row.source_line for row in data.records] == [3, 2, 4]
    assert data.records[1].recorded_timestamp == "2026-05-22T14:00:00+02:00"
    assert all(
        row.timestamp.utcoffset() == datetime.timedelta(0) for row in data.records
    )
    assert data.time_basis.startswith("UTC")


def test_actual_frozen_config_last_schema_remains_readable(tmp_path):
    columns = (
        "timestamp",
        "val_bpb",
        "avg_skel_dist",
        "avg_centerline_dice",
        "avg_cc_diff",
        "avg_crit_comp",
        "train_loss",
        "throughput_Mvps",
        "num_params_M",
        "peak_vram_mb",
        "config",
    )
    config = '{"learning_rate": 0.001, "comment": "quoted config"}'
    row = (VALID_ROW[0], "0.4", "0", "0", "0", "0", "0.2", "12", "20", "4000", config)
    path = write_results(tmp_path / "results.tsv", [row], "\t".join(columns) + "\n")
    original = path.read_bytes()
    data = inputs.read_results(path)
    assert data.columns == columns
    assert data.records[0].throughput_Mvps == 12
    assert path.read_bytes() == original


@pytest.mark.parametrize("kind", ["bytes", "rows"])
def test_input_budgets_are_checked(tmp_path, monkeypatch, kind):
    path = write_results(tmp_path / "results.tsv", [VALID_ROW, VALID_ROW])
    if kind == "bytes":
        monkeypatch.setattr(inputs, "MAX_RESULTS_BYTES", 20)
    else:
        monkeypatch.setattr(inputs, "MAX_ROWS", 1)
    with pytest.raises(ValueError, match="exceeds"):
        inputs.read_results(path)


def test_invalid_utf8_and_directories_are_not_result_inputs(tmp_path):
    path = tmp_path / "invalid.tsv"
    path.write_bytes(b"\xff")
    with pytest.raises(ValueError):
        inputs.read_results(path)
    with pytest.raises(ValueError, match="regular file"):
        inputs.read_results(tmp_path)


@pytest.mark.parametrize("kind", ["no dated entry", "invalid date", "oversized"])
def test_notebook_invalid_inputs_fail(tmp_path, monkeypatch, kind):
    path = tmp_path / "notes.md"
    if kind == "no dated entry":
        path.write_text("# Undated notebook\n## [Future Entry Template]\n")
    elif kind == "invalid date":
        path.write_text("## [2026-02-30] Invalid date\n")
    else:
        monkeypatch.setattr(inputs, "MAX_NOTEBOOK_BYTES", 20)
        path.write_text("## [2026-05-22] Entry\n" * 5)
    with pytest.raises(ValueError):
        inputs.read_notebook(path)


def test_notebook_selection_is_by_date_not_file_order_and_truncation_is_explicit(
    tmp_path,
):
    path = tmp_path / "notes.md"
    path.write_text(
        "## [2026-05-22] Latest first\nwrong tie\n"
        "## [2026-05-22] Latest second\n"
        + "x" * 3000
        + "\n## [2026-05-01] Older last\nOLD\n"
    )
    source, note = inputs.read_notebook(path)
    assert note["entry_heading"] == "## [2026-05-22] Latest second"
    assert note["truncated"] is True
    assert "[Excerpt truncated]" in note["excerpt"]
    assert "OLD" not in note["excerpt"]
    assert note["sha256"] == hashlib.sha256(source.data).hexdigest()


def verify_bundle(output):
    manifest = json.loads((output / "report.json").read_text())
    assert manifest["row_count"] == len(manifest["records"])
    for name, record in manifest["artifacts"].items():
        contents = (output / name).read_bytes()
        assert record["sha256"] == hashlib.sha256(contents).hexdigest()
        assert record["bytes"] == len(contents)
    return manifest


def test_zero_loss_plots_linearly_and_bundle_has_exact_source_hash(workspace):
    from PIL import Image

    path = workspace / "results.tsv"
    write_results(path, [(VALID_ROW[0], "0", "0", "20")])
    original = path.read_bytes()
    with warnings.catch_warnings():
        warnings.simplefilter("error", RuntimeWarning)
        output = charts.plot_results(path, workspace / "zero")
    manifest = verify_bundle(output)
    assert manifest["results"]["sha256"] == hashlib.sha256(original).hexdigest()
    assert manifest["records"][0]["val_bpb"] == 0
    assert "timezone not recorded" in manifest["time_basis"]
    assert set(manifest["artifacts"]) == {
        "sources/results.tsv",
        *{
            f"{name}.{extension}"
            for name in charts.CHART_NAMES
            for extension in ("png", "svg")
        },
    }
    with Image.open(output / "recorded_diagnostics.png") as image:
        assert json.loads(image.info["Description"])["results"] == manifest["results"]
    assert path.read_bytes() == original


def test_pdf_and_charts_share_snapshot_and_ignore_legacy_assets(workspace):
    legacy = workspace / "reports/figures"
    legacy.mkdir(parents=True)
    (legacy / "research_frontier.png").write_bytes(b"not an image")
    (legacy / "hardware_efficiency.png").write_bytes(b"not an image")
    samples = legacy / "training_samples"
    samples.mkdir()
    (samples / "zzzz.png").write_bytes(b"not an image")
    before = {
        path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()
    }
    pdf = daily.generate_pdf(output=workspace / "report")
    manifest = verify_bundle(pdf.parent)
    assert (
        manifest["results"]["sha256"]
        == hashlib.sha256(before[workspace / "results.tsv"]).hexdigest()
    )
    assert manifest["notebook"]["entry_date"] == "2026-05-22"
    assert manifest["generated_at"].endswith("+00:00")
    assert set(manifest["artifacts"]) == {
        "report.pdf",
        "sources/results.tsv",
        "sources/notebook.md",
        *{
            f"charts/{name}.{extension}"
            for name in charts.CHART_NAMES
            for extension in ("png", "svg")
        },
    }
    for path, contents in before.items():
        assert path.read_bytes() == contents
    text = pdf_text(pdf)
    assert manifest["results"]["sha256"] in text
    assert "Notebook intent" in text
    assert "Training Data Samples" not in text


@pytest.mark.parametrize(
    "kind", ["directory", "file", "source", "ancestor", "symlink", "broken symlink"]
)
def test_output_must_be_new_and_separate_from_inputs(workspace, kind):
    output = workspace / "occupied"
    if kind == "directory":
        output.mkdir()
        (output / "keep").write_text("previous")
    elif kind == "file":
        output.write_text("previous")
    elif kind == "source":
        output = workspace / "results.tsv"
    elif kind == "ancestor":
        output = workspace
    elif kind == "symlink":
        output.symlink_to(workspace / "results.tsv")
    else:
        output.symlink_to(workspace / "missing")
    before = {
        path: path.read_bytes() for path in workspace.rglob("*") if path.is_file()
    }
    with pytest.raises(ValueError, match="exists|overlap"):
        charts.plot_results(output=output)
    for path, contents in before.items():
        assert path.read_bytes() == contents


@pytest.mark.parametrize(
    "kind", ["results", "notebook", "render", "manifest", "pdf", "destination"]
)
def test_failed_or_changed_builds_never_publish_partial_bundle(
    workspace, monkeypatch, kind
):
    output = workspace / "report"
    original_render = daily.render_charts

    def render(data, staging):
        if kind == "render":
            staging.mkdir()
            (staging / "partial.png").write_bytes(b"partial")
            raise RuntimeError("injected render failure")
        result = original_render(data, staging)
        if kind == "results":
            (workspace / "results.tsv").write_text(HEADER + "\t".join(VALID_ROW) + "\n")
        elif kind == "notebook":
            (workspace / "docs/LAB_NOTEBOOK.md").write_text("## [2026-06-01] Changed\n")
        elif kind == "destination":
            output.mkdir()
            (output / "keep").write_text("another writer")
        return result

    monkeypatch.setattr(daily, "render_charts", render)
    if kind == "manifest":
        monkeypatch.setattr(
            charts, "write_json", lambda path, data: path.write_text("{}")
        )
    if kind == "pdf":
        monkeypatch.setattr(
            daily.VesuviusReport,
            "output",
            lambda self, path: path.write_bytes(b"broken"),
        )
    with pytest.raises((ValueError, RuntimeError)):
        daily.generate_pdf(output=output)
    if kind == "destination":
        assert [path.name for path in output.iterdir()] == ["keep"]
        assert (output / "keep").read_text() == "another writer"
    else:
        assert not output.exists()
    assert not list(workspace.glob(".report-*"))


@pytest.mark.parametrize("bbox", [None, "tight"])
def test_rendering_preserves_global_matplotlib_state(workspace, monkeypatch, bbox):
    import matplotlib as mpl
    import matplotlib.pyplot as plt

    figure = plt.figure()
    monkeypatch.setitem(mpl.rcParams, "savefig.bbox", bbox)
    figures = plt.get_fignums()
    state = dict(mpl.rcParams)
    try:
        charts.plot_results(output=workspace / "charts")
        assert plt.get_fignums() == figures
        assert dict(mpl.rcParams) == state
    finally:
        plt.close(figure)


@pytest.mark.parametrize("script", ["plot_results.py", "generate_daily_report.py"])
def test_cli_outside_checkout_uses_explicit_inputs_and_new_destination(
    workspace, script, tmp_path
):
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    command = [
        sys.executable,
        str(REPO / "scripts" / script),
        "--results",
        str(workspace / "results.tsv"),
        "--out",
        str(elsewhere / "bundle"),
    ]
    if script == "generate_daily_report.py":
        command.append("--no-notebook")
    result = subprocess.run(command, cwd=elsewhere, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    manifest = verify_bundle(elsewhere / "bundle")
    assert manifest["results"]["path"] == str(workspace / "results.tsv")
    if script == "generate_daily_report.py":
        assert manifest["notebook_status"] == "explicitly omitted"
        assert manifest["notebook"] is None
    repeated = subprocess.run(command, cwd=elsewhere, capture_output=True, text=True)
    assert repeated.returncode == 1
    assert "already exists" in repeated.stderr


def test_missing_notebook_is_an_error_unless_explicitly_omitted(workspace):
    (workspace / "docs/LAB_NOTEBOOK.md").unlink()
    with pytest.raises(ValueError, match="regular file"):
        daily.generate_pdf(output=workspace / "out")
    assert not (workspace / "out").exists()
    assert daily.generate_pdf(
        notebook=None, output=workspace / "without-notebook"
    ).exists()


def test_unsupported_notebook_glyph_fails_instead_of_silently_dropping_text(workspace):
    (workspace / "docs/LAB_NOTEBOOK.md").write_text(
        "## [2026-05-22] Note\n\U0001fae0\n"
    )
    with pytest.raises(ValueError, match="font does not support"):
        daily.generate_pdf(output=workspace / "out")
    assert not (workspace / "out").exists()
