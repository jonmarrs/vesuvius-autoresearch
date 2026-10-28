"""A ranked batch must have distinct artifacts and preserve its inputs."""

import csv
import os
import shlex
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.inference import run_ranked_inference as runner
from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths


def candidate(**changes):
    return dict(
        local_uri="ct.zarr",
        z="1",
        y="2",
        x="3",
        width="8",
        height="8",
        patch_size="8",
        **changes,
    )


def write_rows(path, rows):
    with path.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]), delimiter="\t")
        writer.writeheader()
        writer.writerows(rows)


def plan(tmp_path, rows, **kwargs):
    return runner.plan_inference(
        rows,
        tmp_path / "ranked.tsv",
        kwargs.get("manifest", tmp_path / "commands.sh"),
        kwargs.get("prediction_dir", tmp_path / "predictions"),
        kwargs.get("checkpoint", tmp_path / "checkpoint.pt"),
    )


def test_two_scrolls_at_same_coordinates_refuse_before_any_job_or_manifest(
    tmp_path, monkeypatch, capsys
):
    rows = [candidate(), dict(candidate(), local_uri="other-scroll.zarr")]
    ranked, manifest = tmp_path / "ranked.tsv", tmp_path / "commands.sh"
    write_rows(ranked, rows)
    manifest.write_text("previous plan\n")
    monkeypatch.setattr(
        runner.subprocess, "run", lambda *a, **k: pytest.fail("must not launch")
    )
    with pytest.raises(SystemExit) as exc:
        runner.main(["--ranked", str(ranked), "--manifest", str(manifest), "--execute"])
    assert exc.value.code == 2
    assert "collision" in capsys.readouterr().err
    assert manifest.read_text() == "previous plan\n"


def test_distinct_stems_are_passed_to_predictor_and_manifest_is_shell_quoted(tmp_path):
    rows = [
        candidate(artifact_stem="scroll two"),
        dict(candidate(artifact_stem="scroll_three"), local_uri="other.zarr"),
    ]
    commands = plan(tmp_path, rows)
    output = tmp_path / "commands.sh"
    runner.write_manifest(commands, output)
    assert [shlex.split(line) for line in output.read_text().splitlines()] == commands
    assert [cmd[cmd.index("--artifact_stem") + 1] for cmd in commands] == [
        "scroll two",
        "scroll_three",
    ]


def test_derived_previews_cannot_collide_with_another_main_image(tmp_path):
    with pytest.raises(ValueError, match="collision"):
        plan(tmp_path, [candidate(artifact_stem="a"), candidate(artifact_stem="a_ink")])


@pytest.mark.parametrize("alias", ["direct", "symlink", "hardlink"])
@pytest.mark.parametrize("protected", ["ranked.tsv", "checkpoint.pt"])
def test_manifest_cannot_alias_input_files(tmp_path, protected, alias):
    original = tmp_path / protected
    original.write_bytes(b"preserve these bytes")
    output = original
    if alias != "direct":
        output = tmp_path / "commands.sh"
        if alias == "symlink":
            output.symlink_to(original)
        else:
            os.link(original, output)
    with pytest.raises(ValueError, match="collision"):
        plan(tmp_path, [candidate()], manifest=output)
    assert original.read_bytes() == b"preserve these bytes"


@pytest.mark.parametrize("target", ["checkpoint", "source", "output", "zarr_child"])
def test_collisions_include_inputs_and_export_directories(tmp_path, target):
    predictions = tmp_path / "predictions"
    checkpoint = (
        predictions / "a_ink.npy"
        if target == "checkpoint"
        else tmp_path / "checkpoint.pt"
    )
    uri = str(predictions) if target == "source" else "ct.zarr"
    manifest = (
        predictions / "a.png"
        if target == "output"
        else predictions / "a_ink.zarr/report.sh"
        if target == "zarr_child"
        else tmp_path / "commands.sh"
    )
    with pytest.raises(ValueError, match="collision"):
        plan(
            tmp_path,
            [dict(candidate(artifact_stem="a"), local_uri=uri)],
            manifest=manifest,
            checkpoint=checkpoint,
        )
    assert not predictions.exists()


def test_existing_output_hardlinks_and_symlinked_directories_are_checked(tmp_path):
    predictions = tmp_path / "predictions"
    predictions.mkdir()
    (predictions / "a_ink.npy").write_bytes(b"old array")
    os.link(predictions / "a_ink.npy", predictions / "b_ink.npy")
    with pytest.raises(ValueError, match="collision"):
        plan(tmp_path, [candidate(artifact_stem="a"), candidate(artifact_stem="b")])


def test_component_sort_keeps_nested_aliases_visible(tmp_path):
    # 'ct-other' must not hide the relationship between 'ct' and 'ct/nested'.
    with pytest.raises(ValueError, match="collision"):
        validate_plan_paths(
            [(tmp_path / "ct/nested/result", "output")],
            [(tmp_path / "ct", "source"), (tmp_path / "ct-other", "other source")],
        )


def test_failed_manifest_publication_keeps_old_contents_and_mode(tmp_path, monkeypatch):
    output = tmp_path / "commands.sh"
    output.write_text("previous\n")
    output.chmod(0o750)

    def fail(*args):
        raise OSError("simulated publish failure")

    monkeypatch.setattr(runner.os, "replace", fail)
    with pytest.raises(OSError, match="publish failure"):
        runner.write_manifest([["python", "predict.py"]], output)
    assert output.read_text() == "previous\n"
    assert stat.S_IMODE(output.stat().st_mode) == 0o750
    assert list(tmp_path.iterdir()) == [output]


def test_atomic_publication_preserves_existing_manifest_permissions(tmp_path):
    output = tmp_path / "commands.sh"
    output.write_text("old\n")
    output.chmod(0o750)
    runner.write_manifest([["python", "predict.py"]], output)
    assert output.read_text() == "python predict.py\n"
    assert stat.S_IMODE(output.stat().st_mode) == 0o750


def test_planning_cli_runs_without_site_packages_from_another_directory(tmp_path):
    table, manifest = tmp_path / "ranked.tsv", tmp_path / "commands.sh"
    write_rows(table, [candidate(artifact_stem="scroll_two")])
    result = subprocess.run(
        [
            sys.executable,
            "-S",
            str(Path(runner.__file__).resolve()),
            "--ranked",
            str(table),
            "--manifest",
            str(manifest),
            "--prediction-dir",
            str(tmp_path / "predictions"),
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert result.returncode == 0, result.stderr
    command = shlex.split(manifest.read_text())
    assert command[command.index("--artifact_stem") + 1] == "scroll_two"


@pytest.mark.parametrize("limit", [0, -1, True, 1.5])
def test_invalid_limit_fails_before_reading_table(tmp_path, limit):
    with pytest.raises(ValueError, match="positive integer"):
        runner.load_candidates(tmp_path / "missing.tsv", limit=limit)


def test_empty_selection_is_actionable_and_does_not_publish(tmp_path, capsys):
    table, output = tmp_path / "ranked.tsv", tmp_path / "plan.sh"
    write_rows(table, [dict(candidate(), local_uri="")])
    with pytest.raises(SystemExit) as exc:
        runner.main(["--ranked", str(table), "--manifest", str(output)])
    assert exc.value.code == 2
    assert "no eligible candidates" in capsys.readouterr().err
    assert not output.exists()


@pytest.mark.parametrize(
    "stem", ["../outside", "/outside", ".", "..", "a\nb", "a\x00b", "a\\b"]
)
def test_invalid_names_are_rejected(tmp_path, stem):
    with pytest.raises(ValueError, match="artifact_stem"):
        plan(tmp_path, [candidate(artifact_stem=stem)])


def test_namespaced_queue_survives_ranking_and_batch_planning(tmp_path, monkeypatch):
    from scripts import build_scroll23_search_queue as queue
    from scripts.rank_scroll23_candidates import rank_candidates

    monkeypatch.setattr(
        queue,
        "_local_uri",
        lambda short_id, division: str(tmp_path / short_id / division / "0"),
    )
    rows = queue.build_queue([0.5, 1.0], 2, 64, 7.91, namespaced_artifacts=True)
    assert len({row["artifact_stem"] for row in rows}) == len(rows)
    table, ranked = tmp_path / "queue.tsv", tmp_path / "ranked.tsv"
    write_rows(table, rows)
    ranked_rows = rank_candidates(
        table, ranked, prediction_dir=tmp_path / "predictions"
    )
    commands = runner.plan_inference(
        ranked_rows,
        ranked,
        tmp_path / "commands.sh",
        prediction_dir=tmp_path / "predictions",
        checkpoint=tmp_path / "model.pt",
    )
    assert len(commands) == len(rows)
    assert {cmd[cmd.index("--artifact_stem") + 1] for cmd in commands} == {
        row["artifact_stem"] for row in rows
    }
