"""scripts/epoch_boundary_overhead.py: cycle overhead against passes over the catalogue."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import epoch_boundary_overhead as ebo  # noqa: E402


def _run(budget, last_step, remaining, f1=None, protocol="seeded-sample-400-v3+z1-27"):
    lines = [f"Starting Gated UNet-Transformer Loop (Budget: {budget}s)..."]
    lines += [
        f"Step {s:04d} | Loss: 0.5 | LR: 1e-05 | dt: 100ms | Remaining: {remaining}s"
        for s in (0, last_step)
    ]
    if f1 is not None:
        lines += [
            f"Evaluating metrics on validation protocol {protocol} (a fixed sample)...",
            f"  val_f1:                {f1:.6f} (thr 0.100)",
        ]
    return lines


def _cycle(n, name, result, stamp, batch, f1):
    stats = f"val_f1: {f1!r}, loss: 0.5" if f1 is not None else "val_f1: N/A"
    return [
        f"## Cycle {n}: {name} ({result})",
        f"- **Timestamp**: {stamp}",
        f"- **Config**: lr: 0.0005, batch_size: {batch}, patch_size: 64",
        f"- **Stats**: {stats}",
        "",
    ]


@pytest.fixture
def logs(tmp_path):
    run_log = _run(3600, 900, 0)  # before v3, never scored: not a killed v3 run
    run_log += _run(900, 2000, 0, f1=0.261291123)  # 2000 * 4 // 7345 = 1 boundary
    run_log += _run(900, 7400, 0, f1=0.27032418)  # 4 boundaries
    run_log += _run(900, 2500, 0, f1=0.25)  # scored twice below: ambiguous
    run_log += _run(900, 2500, 0, f1=0.25)
    run_log += _run(3600, 10400, 0, f1=0.2675046)  # 5 boundaries
    run_log += _run(3600, 28970, 89)  # killed: 15 boundaries
    (tmp_path / "run.log").write_text("\n".join(run_log) + "\n")
    day = ["# Day Shift Sprint", "- **Start Time**: 07:30:00", ""]
    day += _cycle(
        1, "lr_1e-05", "REVERTED", "07:47:00", 4, 0.261291123
    )  # 1020 s: 120 s over
    day += _cycle(
        2, "use_uamt_False", "REVERTED", "08:05:00", 4, 0.27032418
    )  # 1080 s: 180
    day += _cycle(3, "dup", "REVERTED", "08:22:00", 4, 0.25)
    day += _cycle(
        4, "paused", "REVERTED", "09:40:00", 4, 0.261291123
    )  # stretched: 3780 s over
    night = ["# Night Shift Sprint", "- **Start Time**: 23:00:00", ""]
    night += _cycle(
        1, "loss_fiber_bce_0.1", "REVERTED", "00:03:20", 4, 0.2675046
    )  # past midnight: 200
    night += _cycle(2, "use_uamt_False", "CRASHED", "01:08:38", 4, None)
    (tmp_path / "sprint_log_2026-10-16_07-30-03_day_shift.md").write_text(
        "\n".join(day)
    )
    (tmp_path / "sprint_log_2026-10-16_19-15-03_night_shift.md").write_text(
        "\n".join(night)
    )
    return str(tmp_path / "run.log"), str(tmp_path / "sprint_log_*.md")


def test_cycles_are_matched_by_val_f1_and_counted_in_passes(logs):
    r = ebo.analyse(*logs)
    rows = {
        row["cycle"]: (row["steps"], row["boundaries"], row["overhead_s"])
        for row in r["rows"]
    }
    # The ambiguous val_f1 and the stretched interval are left out.
    assert rows == {
        "lr_1e-05": (2000, 1, 120),
        "use_uamt_False": (7400, 4, 180),
        "loss_fiber_bce_0.1": (10400, 5, 200),
    }


def test_the_fit(logs):
    f = ebo.analyse(*logs)["fit"]
    assert f["n"] == 3  # on one line: 100 s + 20 s a boundary
    assert f["per_boundary_s"] == pytest.approx(20.0)
    assert f["intercept_s"] == pytest.approx(100.0)
    assert f["residual_sd_s"] == pytest.approx(0.0, abs=1e-9)


def test_the_killed_run_is_paired_with_its_crashed_cycle(logs):
    (k,) = ebo.analyse(*logs)["killed"]
    assert (k["cycle"], k["steps"], k["remaining_s"], k["boundaries"]) == (
        "use_uamt_False",
        28970,
        89,
        15,
    )
    assert k["predicted_overhead_s"] == pytest.approx(100.0 + 20.0 * 15)


def test_unpaired_killed_runs_are_not_guessed(logs, tmp_path):
    night = tmp_path / "sprint_log_2026-10-16_19-15-03_night_shift.md"
    night.write_text(night.read_text().replace("(CRASHED)", "(REVERTED)"))
    assert ebo.analyse(*logs)["killed"] == []


def test_a_restart_restarts_the_clock(tmp_path):
    # The loop writes "## Resumed at" when it restarts inside a shift; the next
    # cycle's interval starts there, not at the last cycle before the stop.
    night = ["# Night Shift Sprint", "- **Start Time**: 19:10:03", ""]
    night += _cycle(1, "a", "REVERTED", "20:13:05", 8, 0.26)  # 3782 s: 182 over
    night += [
        "## Resumed at 20:14:20 (the loop restarted; its cycles count from 1 again)",
        "",
        "- **VRAM cap 1.5 excludes**: batch_size=24 (2.00)",
        "",
    ]
    night += _cycle(1, "b", "REVERTED", "21:15:57", 8, 0.27)  # 3697 s: 97, not 172
    path = tmp_path / "sprint_log_2026-10-17_19-10-03_night_shift.md"
    path.write_text("\n".join(night))
    got = [(c["cycle"], c["overhead_s"]) for c in ebo.cycles(str(path))]
    assert got == [("a", 182), ("b", 97)]
