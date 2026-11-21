"""Finding 133's choices from findings 131 and 132: the skip only on SKIP_ADOPTED, the denser snap unless
DENSE_READS_WORSE, finding 129's settings when a record is missing."""

import json
import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "repro/first_letters/eligible_band/run_after_controls.sh"


def _choices(tmp_path, v132=None, v131=None, densify_before="2"):
    work = tmp_path / "ctrl" / "work"
    work.mkdir(parents=True, exist_ok=True)
    for name, v in (("studio_fast.json", v132), ("dense_read.json", v131)):
        (work / name).unlink(missing_ok=True)
        if v == "garbled":
            (work / name).write_text("{not json")
        elif v is not None:
            (work / name).write_text(json.dumps({"verdict": v}))
    env = {
        "PATH": "/usr/bin:/bin",
        "FL_CONTROL_DIR": str(tmp_path / "ctrl"),
        "FL_DENSIFY": densify_before,
    }
    run = subprocess.run(
        ["bash", str(WRAPPER), "bash", "-c", 'echo "GOT ${STUDIO_SKIP_EMPTY} ${FL_DENSIFY-unset}"'],
        env=env, capture_output=True, text=True, check=True,
    )  # fmt: skip
    first, got = run.stdout.strip().split("\n")
    assert first.startswith("CONTROLS ")
    return got.split()[1:], first


@pytest.mark.parametrize(
    ("v132", "v131", "expected"),
    [
        ("SKIP_ADOPTED", "DENSE_READS_SAME", ["1", "2"]),
        ("SKIP_ADOPTED", "DENSE_READS_BETTER", ["1", "2"]),
        ("SKIP_NOT_FASTER", "DENSE_READS_SAME", ["0", "2"]),
        ("SKIP_DIFFERS", "DENSE_READS_WORSE", ["0", "unset"]),
        ("DOES_NOT_RUN", "DOES_NOT_RUN", ["0", "2"]),
        (None, None, ["0", "2"]),  # missing records: finding 129's settings
        ("garbled", "garbled", ["0", "2"]),
        ("SKIP_ADOPTED", "DENSE_READS_WORSE", ["1", "unset"]),
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
    ]
    assert _choices(tmp_path, None, "DENSE_READS_WORSE", densify_before="2")[0] == [
        "0",
        "unset",
    ]


def test_the_wrapper_is_executable_and_runs_its_command_last():
    assert os.access(WRAPPER, os.X_OK)
    text = WRAPPER.read_text()
    assert text.rstrip().endswith('exec "$@"')
    assert (
        '"verdict"' in text and "SKIP_ADOPTED" in text and "DENSE_READS_WORSE" in text
    )
