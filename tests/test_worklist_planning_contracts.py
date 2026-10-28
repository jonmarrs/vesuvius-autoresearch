"""Captured geometry plans must preserve their inputs and candidate identities."""

import csv
import hashlib
import json
import os
import shlex
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import (
    build_lasagna_fiber_worklist as worklist,
    execute_lasagna_pipeline as pipeline,
    run_villa_prize_evidence_chain as evidence,
)
from scripts.inference import run_ranked_inference as ranked


@pytest.fixture
def workspace(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    rows = [
        {
            "artifact_stem": "first",
            "local_uri": "ct.zarr",
            "x": "0",
            "y": "0",
            "z": "0",
            "width": "64",
            "height": "64",
            "submittable_window": "true",
            "ct_occupied_status": "true",
            "review_score": "1",
        },
    ]
    rows += [
        dict(rows[0], artifact_stem="filtered", submittable_window="false"),
        dict(rows[0], artifact_stem="priority", x="64", review_score="2"),
    ]
    source = tmp_path / "ranked.tsv"
    with source.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)
    (tmp_path / "ct.zarr").mkdir()
    (tmp_path / "best_model.pt").write_bytes(b"preserve checkpoint")

    def run(*args):
        monkeypatch.setattr(sys, "argv", ["worklist", "--ranked", str(source), *args])
        return worklist.main()

    return tmp_path, source, run


@pytest.mark.parametrize(
    "target", ["ranked", "checkpoint", "each_other", "inside_volume"]
)
def test_legacy_output_aliases_fail_without_modifying_inputs(workspace, target):
    root, source, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    if target == "ranked":
        output = source
    elif target == "checkpoint":
        output = root / "best_model.pt"
    elif target == "each_other":
        tsv = output
    else:
        output = root / "ct.zarr" / "plan.json"
    before = {p: p.read_bytes() for p in root.rglob("*") if p.is_file()}
    with pytest.raises((ValueError, SystemExit)):
        run("--out", str(output), "--tsv", str(tsv))
    for path, contents in before.items():
        assert path.read_bytes() == contents
    assert not tsv.exists()


@pytest.mark.parametrize(
    "text",
    [
        "a\ta\n1\t2\n",
        "a\t\n1\t2\n",
        "a\tb\n1\n",
        "a\tb\n1\t2\t3\n",
        'a\tb\n"unterminated\n',
    ],
)
def test_ambiguous_candidate_tables_are_rejected(tmp_path, text):
    source = tmp_path / "ranked.tsv"
    source.write_text(text)
    with pytest.raises((ValueError, csv.Error)):
        ranked.load_candidates(source, limit=1, require_local=False)


@pytest.mark.parametrize("kind", ["bytes", "rows"])
def test_selection_cannot_bypass_full_table_budgets(workspace, monkeypatch, kind):
    _, source, _ = workspace
    if kind == "bytes":
        monkeypatch.setattr(ranked, "MAX_CANDIDATE_BYTES", source.stat().st_size - 1)
    else:
        monkeypatch.setattr(ranked, "MAX_CANDIDATE_ROWS", 2)
    with pytest.raises(ValueError, match="exceeds"):
        ranked.load_candidates(source, limit=1)


def test_bundle_pins_full_source_and_explains_selection(workspace, monkeypatch):
    root, source, run = workspace
    original = source.read_bytes()
    run("--bundle-dir", str(root / "bundle"), "--limit", "1")
    report = json.loads((root / "bundle/worklist.json").read_text())
    assert (root / "bundle/sources/ranked.tsv").read_bytes() == original
    digest = hashlib.sha256(original).hexdigest()
    assert report["source"]["sha256"] == digest
    assert report["selection"]["source_rows"] == 3
    assert report["selection"]["eligible_rows"] == 2
    assert report["selection"]["selected_rows"] == 1
    item = report["candidates"][0]
    assert item["candidate_index"] == 2 and item["artifact_stem"] == "priority"
    assert sum(item["priority_components"].values()) == pytest.approx(
        item["priority_score"]
    )
    command = shlex.split(item["evidence_command"])
    assert command[0] == str(Path(sys.executable).absolute())
    assert command[command.index("--ranked-sha256") + 1] == digest
    assert command[command.index("--ranked") + 1] == str(
        root / "bundle/sources/ranked.tsv"
    )
    assert command[command.index("--input-base-dir") + 1] == str(root)
    assert command[command.index("--checkpoint") + 1] == str(root / "best_model.pt")
    assert Path(item["local_uri"]).is_absolute()
    assert "heuristic" in (root / "bundle/README.md").read_text()
    source.write_text("changed after publication")
    elsewhere = root / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    selected = evidence.select_candidate(
        command[command.index("--ranked") + 1],
        2,
        expected_sha256=digest,
        input_base_dir=root,
    )
    assert selected["local_uri"] == str(root / "ct.zarr")

    # Exercise the actual generated command's CLI flags without running inference.
    cli = [*command, "--preflight", "--preflight-report", str(root / "preflight.json")]
    env = dict(os.environ)
    repo = Path(__file__).resolve().parents[1]
    env["PYTHONPATH"] = os.pathsep.join(
        [str(repo), str(repo / "src"), env.get("PYTHONPATH", "")]
    )
    env["CUDA_VISIBLE_DEVICES"] = ""
    result = subprocess.run(cli, cwd=elsewhere, env=env, capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    preflight = json.loads((root / "preflight.json").read_text())
    assert preflight["candidate"]["local_uri"] == str(root / "ct.zarr")
    assert not Path(item["output_dir"]).exists()


def test_legacy_pair_restores_both_previous_files_on_publish_failure(
    workspace, monkeypatch
):
    root, _, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    rename = Path.rename

    def fail(source, destination):
        if source.name == "new" and Path(destination) == tsv:
            raise OSError("injected TSV publication failure")
        return rename(source, destination)

    monkeypatch.setattr(Path, "rename", fail)
    with pytest.raises((OSError, SystemExit)):
        run("--out", str(output), "--tsv", str(tsv))
    assert output.read_text() == "old json"
    assert tsv.read_text() == "old tsv"
    assert not list(root.glob(".plan.*-*"))


def test_hash_mismatch_is_checked_before_evidence_output_changes(workspace):
    root, source, _ = workspace
    out = root / "evidence"
    with pytest.raises(ValueError, match="changed"):
        evidence.build_evidence_chain(source, out, ranked_sha256="0" * 64)
    assert not out.exists()


@pytest.mark.parametrize("mode", ["bundle", "legacy"])
def test_source_drift_during_render_aborts_publication(workspace, monkeypatch, mode):
    root, source, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    original = worklist._write_tsv

    def mutate(*args, **kwargs):
        result = original(*args, **kwargs)
        source.write_bytes(source.read_bytes().replace(b"priority", b"rewritten"))
        return result

    monkeypatch.setattr(worklist, "_write_tsv", mutate)
    args = (
        ["--bundle-dir", str(root / "bundle")]
        if mode == "bundle"
        else ["--out", str(output), "--tsv", str(tsv)]
    )
    with pytest.raises(ValueError, match="changed"):
        run(*args)
    assert not (root / "bundle").exists()
    assert output.read_text() == "old json" and tsv.read_text() == "old tsv"


@pytest.mark.parametrize("mode", ["symlink", "hardlink", "artifact_inside_input"])
def test_planned_paths_cannot_alias_inputs(workspace, mode):
    root, source, run = workspace
    output = root / "plan.json"
    if mode == "symlink":
        output.symlink_to(source)
    elif mode == "hardlink":
        os.link(source, output)
    args = ["--out", str(output), "--tsv", str(root / "plan.tsv")]
    if mode == "artifact_inside_input":
        args += ["--output-root", str(root / "ct.zarr")]
    before = source.read_bytes()
    with pytest.raises(ValueError):
        run(*args)
    assert source.read_bytes() == before
    assert not (root / "plan.tsv").exists()


def test_no_eligible_candidates_preserves_previous_legacy_worklist(workspace):
    root, source, run = workspace
    source.write_text(source.read_text().replace("true", "false"))
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    with pytest.raises(ValueError, match="no eligible"):
        run("--out", str(output), "--tsv", str(tsv))
    assert output.read_text() == "old json" and tsv.read_text() == "old tsv"


def test_legacy_pair_success_preserves_modes_and_matches_tsv(workspace):
    root, source, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    output.chmod(0o640)
    tsv.chmod(0o664)
    run("--out", str(output), "--tsv", str(tsv))
    report = json.loads(output.read_text())
    with tsv.open() as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    assert [int(row["candidate_index"]) for row in rows] == [
        item["candidate_index"] for item in report["candidates"]
    ]
    assert {row["ranked_sha256"] for row in rows} == {
        hashlib.sha256(source.read_bytes()).hexdigest()
    }
    assert output.stat().st_mode & 0o777 == 0o640
    assert tsv.stat().st_mode & 0o777 == 0o664


def test_bom_quoted_fields_and_blank_lines_keep_source_candidate_order(tmp_path):
    source = tmp_path / "ranked.tsv"
    source.write_bytes(
        b'\xef\xbb\xbfa\tb\nfirst\t"line one\nline two"\n\nsecond\tlast\n'
    )
    rows = ranked.load_candidates(source, require_local=False)
    assert rows == [
        {"a": "first", "b": "line one\nline two"},
        {"a": "second", "b": "last"},
    ]


def test_pipeline_report_protects_captured_inputs_even_if_ranked_table_differs(
    workspace,
):
    root, source, _ = workspace
    captured_input = root / "captured.zarr"
    captured_input.mkdir()
    args = SimpleNamespace(
        ranked=source,
        checkpoint=root / "best_model.pt",
        report=captured_input / "report.json",
    )
    with pytest.raises(ValueError, match="collision"):
        pipeline._validate_report_path(args, [{"local_uri": str(captured_input)}])
    assert not args.report.exists()


def test_failed_rollback_retains_recoverable_backups(workspace, monkeypatch):
    root, _, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    rename, replace = Path.rename, Path.replace

    def fail_publish(path, destination):
        if path.name == "new" and Path(destination) == tsv:
            raise OSError("publish failed")
        return rename(path, destination)

    def fail_restore(path, destination):
        if path.name == "previous":
            raise OSError("restore failed")
        return replace(path, destination)

    monkeypatch.setattr(Path, "rename", fail_publish)
    monkeypatch.setattr(Path, "replace", fail_restore)
    with pytest.raises(RuntimeError, match="recover retained files"):
        run("--out", str(output), "--tsv", str(tsv))
    assert {p.read_text() for p in root.glob(".plan.*-*/previous")} == {
        "old json",
        "old tsv",
    }


def test_interrupt_after_first_new_file_rename_removes_partial_pair(
    workspace, monkeypatch
):
    root, _, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    rename = Path.rename

    def interrupted(path, destination):
        result = rename(path, destination)
        if path.name == "new" and Path(destination) == output:
            raise KeyboardInterrupt
        return result

    monkeypatch.setattr(Path, "rename", interrupted)
    with pytest.raises(KeyboardInterrupt):
        run("--out", str(output), "--tsv", str(tsv))
    assert not output.exists() and not tsv.exists()


def test_interrupt_during_rollback_keeps_old_backups(workspace, monkeypatch):
    root, _, run = workspace
    output, tsv = root / "plan.json", root / "plan.tsv"
    output.write_text("old json")
    tsv.write_text("old tsv")
    rename = Path.rename

    def fail_publish(path, destination):
        if path.name == "new" and Path(destination) == tsv:
            raise OSError("publish failed")
        return rename(path, destination)

    def interrupt_restore(*args):
        raise KeyboardInterrupt

    monkeypatch.setattr(Path, "rename", fail_publish)
    monkeypatch.setattr(Path, "replace", interrupt_restore)
    with pytest.raises(KeyboardInterrupt):
        run("--out", str(output), "--tsv", str(tsv))
    assert {p.read_text() for p in root.glob(".plan.*-*/previous")} == {
        "old json",
        "old tsv",
    }
