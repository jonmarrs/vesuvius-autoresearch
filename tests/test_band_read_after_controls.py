"""Finding 133's choices from findings 131, 132 and 134: the skip only on SKIP_ADOPTED, the denser snap unless
DENSE_READS_WORSE, three snap passes only on finding 134's three_passes with the denser snap on, and finding 129's
settings when a record is missing."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "repro/first_letters/eligible_band/run_after_controls.sh"


def _choices(tmp_path, v132=None, v131=None, densify_before="2", c134=None):
    work = tmp_path / "ctrl" / "work"
    work.mkdir(parents=True, exist_ok=True)
    for name, key, v in (("studio_fast.json", "verdict", v132), ("dense_read.json", "verdict", v131),
                         ("snap_passes.json", "consequence", c134)):  # fmt: skip
        (work / name).unlink(missing_ok=True)
        if v == "garbled":
            (work / name).write_text("{not json")
        elif v is not None:
            extra = {} if key == "verdict" else {"verdict": "SNAP3_READS_SAME"}
            (work / name).write_text(json.dumps({key: v, **extra}))
    env = {
        "PATH": "/usr/bin:/bin",
        "FL_CONTROL_DIR": str(tmp_path / "ctrl"),
        "FL_DENSIFY": densify_before,
    }
    run = subprocess.run(
        ["bash", str(WRAPPER), "bash", "-c", 'echo "GOT ${STUDIO_SKIP_EMPTY} ${FL_DENSIFY-unset} ${FL_SNAP_PASSES}"'],
        env=env, capture_output=True, text=True, check=True,
    )  # fmt: skip
    first, got = run.stdout.strip().split("\n")
    assert first.startswith("CONTROLS ")
    return got.split()[1:], first


@pytest.mark.parametrize(
    ("v132", "v131", "expected"),
    [
        ("SKIP_ADOPTED", "DENSE_READS_SAME", ["1", "2", "1"]),
        ("SKIP_ADOPTED", "DENSE_READS_BETTER", ["1", "2", "1"]),
        ("SKIP_NOT_FASTER", "DENSE_READS_SAME", ["0", "2", "1"]),
        ("SKIP_DIFFERS", "DENSE_READS_WORSE", ["0", "unset", "1"]),
        ("DOES_NOT_RUN", "DOES_NOT_RUN", ["0", "2", "1"]),
        (None, None, ["0", "2", "1"]),  # missing records: finding 129's settings
        ("garbled", "garbled", ["0", "2", "1"]),
        ("SKIP_ADOPTED", "DENSE_READS_WORSE", ["1", "unset", "1"]),
    ],
)
def test_the_choices_follow_the_registered_rule(tmp_path, v132, v131, expected):
    got, first = _choices(tmp_path, v132, v131)
    assert got == expected
    shown = {None: "missing", "garbled": "missing"}
    assert (
        f"finding_132={shown.get(v132, v132)}" in first
        and f"finding_131={shown.get(v131, v131)}" in first
    )


def test_the_callers_densify_is_overridden_by_the_rule(tmp_path):
    assert _choices(tmp_path, None, "DENSE_READS_SAME", densify_before="3")[0] == [
        "0",
        "2",
        "1",
    ]
    assert _choices(tmp_path, None, "DENSE_READS_WORSE", densify_before="2")[0] == [
        "0",
        "unset",
        "1",
    ]


def test_the_wrapper_is_executable_and_runs_its_command_last():
    assert os.access(WRAPPER, os.X_OK)
    text = WRAPPER.read_text()
    assert text.rstrip().endswith('exec "$@"')
    for word in (
        "verdict)",
        "consequence)",
        "SKIP_ADOPTED",
        "DENSE_READS_WORSE",
        "three_passes",
    ):
        assert word in text


@pytest.mark.parametrize(
    ("c134", "v131", "expected_passes"),
    [
        ("three_passes", "DENSE_READS_SAME", "3"),
        (
            "three_passes",
            None,
            "3",
        ),  # finding 131 missing: the denser snap stays on, so three passes apply
        (
            "three_passes",
            "DENSE_READS_WORSE",
            "1",
        ),  # no denser snap: finding 134 did not test this
        ("one_pass", "DENSE_READS_SAME", "1"),
        ("garbled", "DENSE_READS_SAME", "1"),
        (None, "DENSE_READS_SAME", "1"),
    ],
)
def test_three_snap_passes_only_on_finding_134s_consequence_with_the_denser_snap(
    tmp_path, c134, v131, expected_passes
):
    got, first = _choices(tmp_path, None, v131, c134=c134)
    assert got[2] == expected_passes
    shown = {None: "missing", "garbled": "missing"}
    assert (
        f"finding_134={shown.get(c134, c134)}" in first
        and f"FL_SNAP_PASSES={expected_passes}" in first
    )


def _wrapped(env, *command):
    return subprocess.run(
        ["bash", str(WRAPPER), *command],
        env={"PATH": "/usr/bin:/bin", **env},
        capture_output=True,
        text=True,
    )


def test_without_a_command_the_wrapper_stops_before_it_reads_a_record(tmp_path):
    run = _wrapped({"FL_CONTROL_DIR": str(tmp_path / "ctrl")})
    assert run.returncode == 2
    assert "usage: run_after_controls.sh COMMAND..." in run.stderr
    assert run.stdout == ""


def test_the_records_are_read_under_fl_root_unless_fl_control_dir_is_given(tmp_path):
    root = tmp_path / "root"
    work = root / "pherc0211_control" / "work"
    work.mkdir(parents=True)
    (work / "studio_fast.json").write_text(json.dumps({"verdict": "SKIP_ADOPTED"}))
    command = ("bash", "-c", 'echo "GOT ${STUDIO_SKIP_EMPTY}"')
    run = _wrapped({"FL_ROOT": str(root)}, *command)
    assert run.returncode == 0
    assert "finding_132=SKIP_ADOPTED" in run.stdout and "GOT 1" in run.stdout.split(
        "\n"
    )
    run = _wrapped(
        {"FL_ROOT": str(root), "FL_CONTROL_DIR": str(tmp_path / "elsewhere")}, *command
    )
    assert run.returncode == 0
    assert "finding_132=missing" in run.stdout and "GOT 0" in run.stdout.split("\n")


@pytest.mark.parametrize(
    ("name", "record", "shown"),
    [
        ("studio_fast.json", {"consequence": "SKIP_ADOPTED"}, "finding_132=missing"),
        ("dense_read.json", {"verdicts": "DENSE_READS_WORSE"}, "finding_131=missing"),
        (
            "snap_passes.json",
            {"verdict": "three_passes"},
            "finding_134=missing",
        ),  # the consequence is read
    ],
)
def test_a_record_without_its_key_counts_as_missing(tmp_path, name, record, shown):
    work = tmp_path / "ctrl" / "work"
    work.mkdir(parents=True)
    (work / name).write_text(json.dumps(record))
    command = (
        "bash",
        "-c",
        'echo "GOT ${STUDIO_SKIP_EMPTY} ${FL_DENSIFY-unset} ${FL_SNAP_PASSES}"',
    )
    run = _wrapped({"FL_CONTROL_DIR": str(tmp_path / "ctrl")}, *command)
    assert run.returncode == 0
    first, got = run.stdout.strip().split("\n")
    assert shown in first
    assert got.split()[1:] == ["0", "2", "1"]
