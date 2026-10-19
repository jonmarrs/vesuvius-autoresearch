"""scripts/cycle_length_gain.py: val_f1 of 60- against 15-minute cycles on one incumbent."""

from __future__ import annotations

import math
import statistics
import sys
from pathlib import Path

import pytest
from scipy import stats

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import cycle_length_gain as clg  # noqa: E402


def _cycle(n, name, result, stamp, f1, batch=8):
    stats_line = f"val_f1: {f1!r}, loss: 0.5" if f1 is not None else "val_f1: N/A"
    return [
        f"## Cycle {n}: {name} ({result})",
        f"- **Timestamp**: {stamp}",
        f"- **Config**: lr: 0.0005, batch_size: {batch}, patch_size: 64",
        f"- **Stats**: {stats_line}",
        "",
    ]


def _shift(tmp_path, name, start, cycles):
    lines = [f"# {name}", f"- **Start Time**: {start}", ""]
    for c in cycles:
        lines += [c, ""] if isinstance(c, str) else _cycle(*c)
    (tmp_path / f"sprint_log_{name}.md").write_text("\n".join(lines))


@pytest.fixture
def logs(tmp_path):
    _shift(
        tmp_path,
        "2026-10-17_19-10-03_night_shift",
        "19:10:03",
        [
            (1, "old_code", "REVERTED", "20:13:05", 0.30),  # before --since
            (2, "a", "REVERTED", "21:15:00", 0.27),
            "## Resumed at 21:17:25 (the loop restarted; its cycles count from 1 again)",
            (1, "use_uamt_False", "REVERTED", "22:19:00", 0.25),
            (4, "b", "CRASHED", "23:20:00", None),
            (5, "c", "REVERTED", "00:21:00", 0.26),
        ],
    )
    _shift(
        tmp_path,
        "2026-10-18_07-35-03_day_shift",
        "07:35:03",
        [
            (1, "d", "REVERTED", "07:51:00", 0.26),
            (2, "batch_size_16", "REVERTED", "08:07:00", 0.28, 16),
            (3, "e", "REVERTED", "08:24:00", 0.27),
            (4, "f", "REVERTED", "08:40:00", 0.25),
        ],
    )
    _shift(
        tmp_path,
        "2026-10-18_19-10-03_night_shift",
        "19:10:03",
        [
            (1, "g", "REVERTED", "20:11:00", 0.28),
            (2, "h", "SUCCESS", "21:12:00", 0.29),  # the last cycle on this incumbent
            (3, "i", "REVERTED", "22:13:00", 0.20),  # starts from the new incumbent
        ],
    )
    return str(tmp_path / "sprint_log_*.md")


def test_arms_follow_the_shifts_and_stop_at_the_first_promotion(logs):
    r = clg.analyse(logs, since="2026-10-17T21:17:25")
    # Cycle "a" ended at 21:15:00 but started at 20:13:05, before --since.
    assert [(a["budget"], [c["cycle"] for c in a["cycles"]]) for a in r["arms"]] == [
        (3600, ["use_uamt_False", "b", "c"]),
        (900, ["d", "batch_size_16", "e", "f"]),
        (3600, ["g", "h"]),
    ]
    assert r["promotion"] == {"cycle": "h", "start": "2026-10-18T20:11:00"}


def test_each_arm_counts_scored_and_crashed(logs):
    arms = clg.analyse(logs, since="2026-10-17T21:17:25")["arms"]
    assert [(a["scored"], a["crashed"]) for a in arms] == [(2, 1), (4, 0), (2, 0)]
    assert arms[1]["mean"] == pytest.approx(0.265)
    assert arms[1]["sd"] == pytest.approx(statistics.stdev([0.26, 0.28, 0.27, 0.25]))


def test_each_long_arm_is_compared_with_the_short_arm_beside_it(logs):
    r = clg.analyse(logs, since="2026-10-17T21:17:25")
    (first, second) = r["comparisons"]["all"]
    assert (first["long"], first["short"], second["long"], second["short"]) == (
        0,
        1,
        2,
        1,
    )
    long, short = [0.25, 0.26], [0.26, 0.28, 0.27, 0.25]
    v1, v2 = statistics.variance(long) / 2, statistics.variance(short) / 4
    df = (v1 + v2) ** 2 / (v1**2 / 1 + v2**2 / 3)
    half = stats.t.ppf(0.975, df) * math.sqrt(v1 + v2)
    diff = statistics.mean(long) - statistics.mean(short)
    assert first["diff"] == pytest.approx(diff)
    assert first["df"] == pytest.approx(df)
    assert (first["lo"], first["hi"]) == pytest.approx((diff - half, diff + half))


def test_the_secondary_leaves_out_tweaks_that_change_the_steps_a_budget_buys(logs):
    r = clg.analyse(logs, since="2026-10-17T21:17:25")
    (first, _) = r["comparisons"]["steps_held"]
    # use_uamt_False and batch_size_16 are out: 0.26 against 0.26, 0.27, 0.25.
    assert (first["n_long"], first["n_short"]) == (1, 3)
    assert first["diff"] == pytest.approx(0.26 - 0.26)
    assert first["lo"] is None  # one cycle has no spread
    assert clg.STEP_TWEAKS.match("use_uamt_False") and clg.STEP_TWEAKS.match(
        "batch_size_16"
    )
    assert not clg.STEP_TWEAKS.match("lr_0.001")


def test_the_reading_is_fixed_in_advance():
    assert clg.reading(0.001, 0.004) == "higher"
    assert clg.reading(-0.002, 0.004) == "no measurable gain"
    assert clg.reading(-0.002, 0.012) == "inconclusive"
    assert clg.reading(-0.006, -0.001) == "lower"
    assert clg.reading(None, None) is None


def test_steps_come_from_the_run_log(logs, tmp_path):
    def run(steps, f1):
        return [
            "Starting Gated UNet-Transformer Loop (Budget: 900s)...",
            f"Step {steps:04d} | Loss: 0.5 | LR: 1e-05 | dt: 100ms | Remaining: 0s",
            "Evaluating metrics on validation protocol seeded-sample-400-v3+z1-27 ...",
            f"  val_f1:                {f1:.6f} (thr 0.100)",
        ]

    lines = run(1200, 0.26) + run(1300, 0.26) + run(1250, 0.27) + run(5100, 0.29)
    (tmp_path / "run.log").write_text("\n".join(lines) + "\n")
    r = clg.analyse(
        logs, since="2026-10-17T21:17:25", run_logs=[str(tmp_path / "run.log")]
    )
    steps = {c["cycle"]: c["steps"] for a in r["arms"] for c in a["cycles"]}
    # Two runs scored 0.26, so its cycles are not matched; none scored 0.25.
    assert (steps["e"], steps["h"]) == (1250, 5100)
    assert steps["c"] is steps["d"] is steps["use_uamt_False"] is steps["b"] is None
    assert [a["median_steps"] for a in r["arms"]] == [None, 1250, 5100]


def test_named_logs_give_the_same_arms_as_a_glob_over_them(logs, tmp_path):
    # The analysis names its sprint logs, so it can leave out a shift still running.
    named = [
        str(tmp_path / f"sprint_log_{n}.md")
        for n in ("2026-10-17_19-10-03_night_shift", "2026-10-18_07-35-03_day_shift")
    ]
    r = clg.analyse(named, since="2026-10-17T21:17:25")
    assert [[c["cycle"] for c in a["cycles"]] for a in r["arms"]] == [
        ["use_uamt_False", "b", "c"],
        ["d", "batch_size_16", "e", "f"],
    ]
    assert (
        r["comparisons"]["all"][0]
        == clg.analyse(logs, since="2026-10-17T21:17:25")["comparisons"]["all"][0]
    )


def test_an_out_of_memory_crash_is_counted(logs, tmp_path):
    # Logged "CRASHED (OOM)"; the arm counted it as no cycle at all.
    path = tmp_path / "sprint_log_2026-10-18_07-35-03_day_shift.md"
    text = path.read_text().replace(
        "## Cycle 2: batch_size_16 (REVERTED)",
        "## Cycle 2: batch_size_16 (CRASHED (OOM))",
    )
    path.write_text(text.replace("val_f1: 0.28, loss: 0.5", "val_f1: N/A"))
    arms = clg.analyse(logs, since="2026-10-17T21:17:25")["arms"]
    assert [c["cycle"] for c in arms[1]["cycles"]] == ["d", "batch_size_16", "e", "f"]
    assert (arms[1]["scored"], arms[1]["crashed"]) == (3, 1)


def test_a_log_named_twice_is_read_once(logs, tmp_path):
    day = str(tmp_path / "sprint_log_2026-10-18_07-35-03_day_shift.md")
    once = clg.analyse(logs, since="2026-10-17T21:17:25")
    assert clg.analyse([logs, day], since="2026-10-17T21:17:25") == once


def test_a_name_that_matches_no_log_is_an_error(logs, tmp_path):
    # Not an arm left out without a word.
    with pytest.raises(SystemExit, match="no sprint log matches"):
        clg.analyse([logs, str(tmp_path / "sprint_log_typo.md")], since="2026-10-17")
