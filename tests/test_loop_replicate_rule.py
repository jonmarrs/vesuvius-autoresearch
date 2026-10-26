"""Bind the replicate-rule replay (scripts/loop_replicate_rule.py) to its source record and its report."""

import datetime as dt
import hashlib
import importlib.util
import json
import math
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "reports/loop_tweak_replication_2026-10-25.json"
RECORD = ROOT / "reports/loop_replicate_rule_2026-10-26.json"
REPORT = ROOT / "reports/loop_replicate_rule_2026-10-26.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = _load("loop_replicate_rule")


def _brute(rows, labels, measures, min_cycles, min_others):
    """The rule as written in the docstring, recomputed from scratch at every cycle."""
    out = []
    for j in range(len(rows)):
        T = labels[j]
        mine = [i for i in range(j + 1) if labels[i] == T]
        if len(mine) < min_cycles:
            out.append(-math.inf)
            continue
        ts = []
        for m in measures:
            d = []
            for i in mine:
                others = [
                    rows[o][m]
                    for o in range(j + 1)
                    if labels[o] != T and rows[o]["epoch"] == rows[i]["epoch"]
                ]
                if len(others) >= min_others:
                    d.append(rows[i][m] - np.mean(others))
            if len(d) < min_cycles:
                break
            ts.append(np.mean(d) / (np.std(d, ddof=1) / math.sqrt(len(d))))
        else:
            out.append(min(ts))
            continue
        out.append(-math.inf)
    return np.array(out)


def _synthetic(n=150, seed=3):
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        tweak = f"t{rng.integers(6)}"
        lift = 0.004 if tweak == "t0" else 0.0
        rows.append(
            {
                "start": f"2026-10-18T{i // 60:02d}:{i % 60:02d}:00",
                "epoch": "abc"[i * 3 // n],
                "tweak": tweak,
                "val_f1": 0.266 + lift + rng.normal(0, 0.002),
                "roc_auc": 0.58 + 2 * lift + rng.normal(0, 0.006),
            }
        )
    return rows


@pytest.mark.parametrize("measures", list(L.MEASURES.values()))
@pytest.mark.parametrize("min_cycles", [3, 6])
def test_scores_are_the_rule_as_written(measures, min_cycles):
    rows = _synthetic()
    labels = [r["tweak"] for r in rows]
    got = L.scores(rows, labels, measures, min_cycles, min_others=5)
    want = _brute(rows, labels, measures, min_cycles, 5)
    assert np.isfinite(got).sum() > 20
    np.testing.assert_allclose(got, want, rtol=1e-9, atol=1e-12)


def test_it_reads_no_cycle_of_the_registered_window():
    replication = _load("loop_tweak_replication")
    assert replication.REGISTERED["since"] == L.WINDOW_START
    record = json.loads(SOURCE.read_text())
    late = dict(record["rows"][-1], start=L.WINDOW_START)
    with pytest.raises(AssertionError, match="before the confirmation window"):
        L.analyse({"rows": record["rows"] + [late]}, permutations=2)


def test_the_shuffle_keeps_each_epochs_tweaks():
    rows = json.loads(SOURCE.read_text())["rows"]
    labels = L.shuffled(rows, np.random.default_rng(0))
    assert labels != [r["tweak"] for r in rows]
    for epoch in {r["epoch"] for r in rows}:
        before = sorted(r["tweak"] for r in rows if r["epoch"] == epoch)
        after = sorted(
            t for t, r in zip(labels, rows, strict=True) if r["epoch"] == epoch
        )
        assert before == after


def test_centring_takes_out_the_tweak_effects():
    rows = sorted(json.loads(SOURCE.read_text())["rows"], key=lambda r: r["start"])
    labels = [r["tweak"] for r in rows]
    measures = L.MEASURES["val_f1_and_roc_auc"]
    raw = L.scores(rows, labels, measures, 6)
    flat = L.scores(L.centred(rows, measures), labels, measures, 6)
    standing = [j for j, t in enumerate(labels) if t == "aug_mode_batchgeneratorsv2"]
    assert raw[standing].max() > 4 and flat[standing].max() < 1.5
    assert [r["start"] for r in L.centred(rows, measures)] == [r["start"] for r in rows]


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text())


def test_the_record_is_its_source(record):
    assert record["source"]["sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    source = json.loads(SOURCE.read_text())
    assert record["cycles"] == len(source["rows"]) == 546
    assert record["permutations"] == L.PERMUTATIONS and record["seed"] == L.SEED
    assert record["target_rate"] == L.TARGET


def test_the_null_counts_are_the_stored_maxima(record):
    for g in record["grid"]:
        key = f"{g['measures']}/min_cycles_{g['min_cycles']}"
        maxima = record["null_maxima"][key]
        assert (
            len(maxima["shuffled"]) == len(maxima["centred"]) == record["permutations"]
        )
        assert g["false_promotions"] == sum(m > g["c"] for m in maxima["shuffled"])
        assert g["centred_false_promotions"] == sum(
            m > g["c"] for m in maxima["centred"]
        )
        assert g["ci95"] == L.clopper_pearson(
            g["false_promotions"], record["permutations"]
        )
    for key, c in record["smallest_c_at_target"].items():
        name, min_cycles = key.split("/min_cycles_")
        rows = [
            g
            for g in record["grid"]
            if g["measures"] == name and g["min_cycles"] == int(min_cycles)
        ]
        ok = [
            g["c"]
            for g in rows
            if max(g["rate"], g["centred_rate"]) <= record["target_rate"]
        ]
        assert c == (min(ok) if ok else None)


def test_the_first_permutations_reproduce(record):
    """Recompute the first 25 of the stored permutations (the same seeded draws) and the real sequence."""
    rows = sorted(json.loads(SOURCE.read_text())["rows"], key=lambda r: r["start"])
    labels = [r["tweak"] for r in rows]
    rng = np.random.default_rng(record["seed"])
    nulls = [L.shuffled(rows, rng) for _ in range(25)]
    for name, measures in L.MEASURES.items():
        flat = L.centred(rows, measures)
        for min_cycles in L.MIN_CYCLES:
            stored = record["null_maxima"][f"{name}/min_cycles_{min_cycles}"]
            assert [
                float(L.scores(rows, n, measures, min_cycles).max()) for n in nulls
            ] == stored["shuffled"][:25]
            assert [
                float(L.scores(flat, n, measures, min_cycles).max()) for n in nulls
            ] == stored["centred"][:25]
            actual = L.scores(rows, labels, measures, min_cycles)
            for g in record["grid"]:
                if g["measures"] != name or g["min_cycles"] != min_cycles:
                    continue
                fired = [j for j, s in enumerate(actual) if s > g["c"]]
                assert g["tweaks_that_would_fire"] == sorted({labels[j] for j in fired})
                first = g["first_promotion"]
                assert (first or {}).get("cycle") == (fired[0] + 1 if fired else None)
                if first:
                    assert (
                        first["start"] == rows[fired[0]]["start"]
                        and first["tweak"] == labels[fired[0]]
                    )


def _row(record, measures, min_cycles, c):
    (row,) = [
        g
        for g in record["grid"]
        if g["measures"] == measures and g["min_cycles"] == min_cycles and g["c"] == c
    ]
    return row


def test_the_report_is_the_record(record):
    import datetime as dt

    text = " ".join(REPORT.read_text().split())
    source = json.loads(SOURCE.read_text())
    assert (
        f"The {record['cycles']} cycles of `reports/loop_tweak_replication_2026-10-25.json`"
        in text
    )
    assert f"{record['tweaks']} tweaks in {record['epochs']} code epochs" in text
    assert f"shuffled {record['permutations']:,} times" in text
    assert f"at most {record['target_rate']:.0%} of windows" in text

    table = {
        "val_f1_and_roc_auc/min_cycles_6": "val_f1 and AUC, ≥ 6 cycles",
        "val_f1_and_roc_auc/min_cycles_8": "val_f1 and AUC, ≥ 8 cycles",
        "val_f1_only/min_cycles_6": "val_f1 alone, ≥ 6 cycles",
    }
    for key, label in table.items():
        name, min_cycles = key.split("/min_cycles_")
        c = record["smallest_c_at_target"][key]
        g = _row(record, name, int(min_cycles), c)
        first = g["first_promotion"]
        when = first["start"][:16].replace("T", " ")
        assert (
            f"| {label} | {c} | {g['false_promotions']}, {g['centred_false_promotions']} | "
            f"batchgeneratorsv2, cycle {first['cycle']}, {when} |"
        ) in text

    c = record["smallest_c_at_target"]["val_f1_and_roc_auc/min_cycles_6"]
    g = _row(record, "val_f1_and_roc_auc", 6, c)
    first = g["first_promotion"]
    assert g["tweaks_that_would_fire"] == ["aug_mode_batchgeneratorsv2"]
    assert (
        f"At c = {c} it would have promoted at batchgeneratorsv2's {first['tweak_cycles_so_far']}th cycle"
        in text
    )
    start = dt.datetime.fromisoformat(first["start"])
    assert (
        start - dt.datetime.fromisoformat(source["since"])
    ).days == 3 and "3 days after the incumbent" in text
    before = (
        dt.datetime.fromisoformat(source["until"]) - start
    ).total_seconds() / 86400
    assert 4.5 < before < 5 and "nearly 5 days before the replication report" in text
    assert f"val_f1 {first['val_f1']:.4f} and AUC {first['roc_auc']:.3f}" in text
    assert (
        f"It was {first['val_f1'] - source['incumbent']:.4f} above the stored incumbent"
        in text
    )
    assert (
        f"the current rule's bar of {source['incumbent'] + source['tolerance']:.4f}"
        in text
    )
    peaks = list(g["largest_score_by_tweak"].items())
    assert (
        peaks[0][0] == "aug_mode_batchgeneratorsv2"
        and f"score peaks at {peaks[0][1]:.1f}" in text
    )
    assert f"The next tweak's peak is {peaks[1][1]:.2f} (`{peaks[1][0]}`)" in text
    assert g["false_promotions"] == g["centred_false_promotions"] == 1
    assert (
        f"Both nulls promoted in 1 window of 1,000 (95% interval up to {g['ci95'][1]:.2%})"
        in text
    )

    low = _row(record, "val_f1_and_roc_auc", 6, 3.0)
    assert (
        f"At c = 3 it promotes in {low['false_promotions']} and {low['centred_false_promotions']} windows"
        in text
    )

    c1 = record["smallest_c_at_target"]["val_f1_only/min_cycles_6"]
    alone = _row(record, "val_f1_only", 6, c1)
    assert f"On val_f1 alone the same rate needs c = {c1}" in text
    assert "use_uamt_False" in alone["tweaks_that_would_fire"]
    assert (
        f"whose val_f1 t peaks at {alone['largest_score_by_tweak']['use_uamt_False']:.1f}"
        in text
    )

    assert source["tally"]["promoted"] is None
    assert (
        max(r["val_f1"] for r in source["rows"])
        <= source["incumbent"] + source["tolerance"]
    )
    assert "The current rule promoted nothing in these 546 cycles" in text


# The registered window test (docs/preregistration/2026-10-26_loop_replicate_rule_window.md).

R = _load("loop_tweak_replication")
POWER = ROOT / "reports/loop_replicate_rule_window_power_2026-10-26.json"
REGISTRATION = ROOT / "docs/preregistration/2026-10-26_loop_replicate_rule_window.md"
STANDING = "aug_mode_batchgeneratorsv2"


def _window(n=240, seed=5, lift=None, only_after=None):
    """Window cycles: the standing tweak every 20th from the 8th, the rest t0..t9. lift: tweak -> (val_f1, AUC)."""
    rng = np.random.default_rng(seed)
    lift = lift or {}
    rows = []
    for j in range(n):
        tweak = STANDING if j % 20 == 7 else f"t{rng.integers(10)}"
        if only_after and tweak == only_after[0] and j <= only_after[1]:
            tweak = "t0"
        f1, auc = lift.get(tweak, (0.0, 0.0))
        rows.append(
            {
                "start": f"2026-10-{25 + (16 * 60 + 15 * j) // 1440}T"
                f"{(16 * 60 + 15 * j) % 1440 // 60:02d}:{(15 * j) % 60:02d}:00",
                "epoch": "139c6873",
                "tweak": tweak,
                "val_f1": 0.266 + f1 + rng.normal(0, 0.002),
                "roc_auc": 0.58 + auc + rng.normal(0, 0.006),
            }
        )
    return rows


def _confirmation(rows, reading="CONFIRMED", status="OK", **registered):
    return {
        "registered": dict(R.REGISTERED, **registered),
        "verdict": {"status": status, "reading": reading if status == "OK" else None},
        "rows": rows,
    }


def test_the_window_rule_is_the_one_chosen_before_the_window(record):
    reg = L.REGISTERED
    key = f"{reg['measures']}/min_cycles_{reg['min_cycles']}"
    assert key == "val_f1_and_roc_auc/min_cycles_6"
    assert reg["c"] == record["smallest_c_at_target"][key] == 4.5
    assert reg["min_others"] == L.MIN_OTHERS
    assert reg["since"] == L.WINDOW_START == R.REGISTERED["since"]
    assert reg["standing"] == R.REGISTERED["standing"] == STANDING
    assert {k: R.REGISTERED[k] for k in L.CONFIRMATION} == L.CONFIRMATION


def test_a_standing_tweak_that_beats_the_rest_is_taken():
    rows = _window(lift={STANDING: (0.008, 0.03)})
    got = L.window_test(_confirmation(rows), permutations=0)
    assert got["outcome"] == "standing" and got["reading"] == "TAKES_CONFIRMED_GAIN"
    assert got["first_promotion"]["tweak"] == STANDING
    assert got["first_promotion"]["tweak_cycles_so_far"] >= L.REGISTERED["min_cycles"]
    unconfirmed = L.window_test(_confirmation(rows, "F1_ONLY"), permutations=0)
    assert unconfirmed["reading"] == "PROMOTES_UNCONFIRMED"


def test_a_window_without_an_effect_promotes_nothing():
    rows = _window()
    got = L.window_test(_confirmation(rows, "NOT_REPLICATED"), permutations=0)
    assert got["outcome"] == "none" and got["first_promotion"] is None
    assert got["reading"] == "ABSTAINS"
    missed = L.window_test(_confirmation(rows), permutations=0)
    assert missed["reading"] == "MISSES_CONFIRMED_GAIN"
    # the standing tweak's score at each of its cycles, as the rule saw it
    assert [s["tweak_cycles_so_far"] for s in got["standing_cycles"]] == list(
        range(1, 9)
    )


def test_another_tweak_promoted_first_is_read_as_such():
    rows = _window(lift={"t3": (0.01, 0.04), STANDING: (0.008, 0.03)})
    for reading in ("CONFIRMED", "NOT_REPLICATED"):
        got = L.window_test(_confirmation(rows, reading), permutations=0)
        assert got["outcome"] == "other" and got["first_promotion"]["tweak"] == "t3"
        assert got["reading"] == "PROMOTES_ANOTHER_TWEAK"


@pytest.mark.parametrize("status", ["INCOMPLETE", "UNMATCHED_RUNS"])
def test_no_reading_when_the_confirmation_gives_none(status):
    rows = _window(lift={STANDING: (0.008, 0.03)})
    got = L.window_test(_confirmation(rows, status=status), permutations=0)
    assert got["status"] == status and got["reading"] is None
    assert "outcome" not in got and "first_promotion" not in got


@pytest.mark.parametrize(
    "registered",
    [{"since": "2026-10-25T15:00:00"}, {"standing": "use_uamt_False"}, {"cut_at": 9}],
)
def test_it_refuses_another_window(registered):
    with pytest.raises(SystemExit, match="registered"):
        L.window_test(_confirmation(_window(), **registered), permutations=0)


def test_it_refuses_a_cycle_before_the_window():
    rows = _window()
    rows[0] = dict(rows[0], start="2026-10-25T15:45:00")
    with pytest.raises(SystemExit, match="before the window"):
        L.window_test(_confirmation(rows), permutations=0)


def test_cycles_after_the_8th_standing_cycle_are_dropped():
    rows = _window(lift={"t9": (0.02, 0.08)}, only_after=("t9", 7 + 20 * 7))
    cut = [j for j, r in enumerate(rows) if r["tweak"] == STANDING][7]
    assert sum(r["tweak"] == "t9" for r in rows[cut + 1 :]) >= 6
    got = L.window_test(_confirmation(rows), permutations=0)
    assert got["cycles"] == cut + 1 and got["last_start"] == rows[cut]["start"]
    assert got["outcome"] == "none"


def test_the_window_null_is_reported_and_changes_no_reading():
    rows = _window(lift={STANDING: (0.008, 0.03)})
    got = L.window_test(_confirmation(rows), permutations=20, seed=1)
    assert got["reading"] == "TAKES_CONFIRMED_GAIN"
    null = got["null"]
    assert len(null["shuffled"]) == len(null["centred"]) == 20
    c = L.REGISTERED["c"]
    assert null["false_promotions"] == sum(m > c for m in null["shuffled"])
    assert null["centred_false_promotions"] == sum(m > c for m in null["centred"])


def _loop_logs(tmp_path, n_standing, n=100):
    """The loop's logs for a window: a shift from 15:45, so its first cycle starts before the window, the standing
    tweak every 10th cycle while it lasts, and the runs split over run.log.old and run.log, as a rotation leaves them."""
    sprint = ["# day shift", "- **Start Time**: 15:45:00", ""]
    runs = []
    for j in range(n):
        standing = j % 10 == 4 and j // 10 < n_standing
        tweak = STANDING if standing else f"t{j % 5}"
        f1 = round(0.26 + 0.0001 * (j * 37 % 17) + 1e-6 * j + 0.006 * standing, 6)
        auc = 0.58 + 0.001 * (j * 11 % 7) + 0.03 * standing
        end = dt.datetime(2026, 10, 25, 15, 45) + dt.timedelta(minutes=15 * (j + 1))
        sprint += [
            f"## Cycle {j + 1}: {tweak} (REVERTED)",
            f"- **Timestamp**: {end:%H:%M:%S}",
            "- **Config**: lr: 0.0005, batch_size: 8, time_budget: 900, patch_size: 64",
            f"- **Stats**: val_f1: {f1!r}, loss: 0.5",
            "",
        ]
        runs.append(
            [
                f"{R.RUN_START}900s)...",
                "Step 1000 | Loss: 0.5 | LR: 1e-4 | dt: 700ms | Remaining: 10s",
                "avg_mean_ap:           0.5960",
                f"val_f1:                {f1:.6f} (thr 0.100; incumbent 0.265762) ",
                "ap_prevalence_lift:    1.1500",
                f"roc_auc:               {auc:.4f}  [selection: F1 gated by AP-lift]",
            ]
        )
    (tmp_path / "sprint_log_2026-10-25_15-45-00_day_shift.md").write_text(
        "\n".join(sprint)
    )
    for name, part in (("run.log.old", runs[: n // 2]), ("run.log", runs[n // 2 :])):
        (tmp_path / name).write_text("\n".join(ln for run in part for ln in run) + "\n")


@pytest.mark.parametrize(
    "n_standing, status, reading",
    [(10, "OK", "TAKES_CONFIRMED_GAIN"), (5, "INCOMPLETE", None)],
)
def test_the_window_test_reads_what_the_registered_confirmation_writes(
    tmp_path, n_standing, status, reading
):
    """Amendment 1's command on the loop's own log formats, then --window on its output, as the readout will run
    them: the two scripts agree on the output's shape before any window cycle is read."""
    _loop_logs(tmp_path, n_standing)
    confirmation, out = tmp_path / "confirmation.json", tmp_path / "window.json"
    R.main(
        ["--registered", "--since", "2026-10-25T16:00:00", "--until", "2026-10-29T16:00:00",
         "--sprint-logs", str(tmp_path / "sprint_log_2026-10-2*.md"),
         "--run-log", str(tmp_path / "run.log.old"), str(tmp_path / "run.log"),
         "--out", str(confirmation)]
    )  # fmt: skip
    L.main(["--window", str(confirmation), "--out", str(out)])
    got = json.loads(out.read_text())
    digest = hashlib.sha256(confirmation.read_bytes()).hexdigest()
    assert got["source"]["sha256"] == digest
    assert got["status"] == got["confirmation"]["status"] == status
    assert got["reading"] == reading
    if reading is None:
        assert "first_promotion" not in got
        return
    assert got["confirmation"]["reading"] == "CONFIRMED"
    # the shift's first cycle started at 15:45, before the window
    assert got["first_start"] == "2026-10-25T16:00:00"
    assert got["first_promotion"]["tweak"] == STANDING
    assert got["first_promotion"]["tweak_cycles_so_far"] >= L.REGISTERED["min_cycles"]
    assert len(got["standing_cycles"]) == L.CONFIRMATION["cut_at"]
    assert len(got["null"]["shuffled"]) == L.PERMUTATIONS


@pytest.fixture(scope="module")
def power():
    return json.loads(POWER.read_text())


def test_the_power_record_is_its_source(power):
    source = json.loads(SOURCE.read_text())
    assert power["source"]["sha256"] == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    rows = source["rows"]
    hours = (
        np.datetime64(max(r["start"] for r in rows))
        - np.datetime64(min(r["start"] for r in rows))
    ) / np.timedelta64(1, "h")
    assert power["cap_cycles"] == round(len(rows) / hours * 96) == L.cap_cycles(rows)
    assert power["registered"] == L.REGISTERED
    assert power["confirmation"] == L.CONFIRMATION
    assert power["simulations"] == L.POWER_SIMULATIONS and power["seed"] == L.SEED
    for scale in power["scales"]:
        n = scale["outcomes"]
        assert sum(n.values()) == power["simulations"]
        assert sum(scale["fired_at_standing_cycle"].values()) == n["standing"]


def test_the_first_power_simulations_reproduce(power):
    record = json.loads(SOURCE.read_text())
    again = L.power(record, simulations=40)
    for got, stored in zip(again["scales"], power["scales"], strict=True):
        assert got["scale"] == stored["scale"]
        assert got["trace"] == stored["trace"][:40]


def test_the_registration_is_the_power_record(power):
    text = " ".join(REGISTRATION.read_text().split())
    by = {s["scale"]: s for s in power["scales"]}
    sims = power["simulations"]
    for scale, label in (
        (1.0, "the exploratory effect"),
        (0.5, "half of it"),
        (0.0, "none"),
    ):
        n = by[scale]["outcomes"]
        assert (
            f"| {label} | {n['standing'] / sims:.0%} | {n['other'] / sims:.1%} | "
            f"{n['none'] / sims:.0%} | {n['incomplete'] / sims:.1%} |"
        ) in text
    assert f"{power['cap_cycles']} cycles" in text
    assert f"{sims:,} simulated windows" in text


def test_the_registrations_simulation_and_horizon_figures_are_the_record(power):
    text = " ".join(REGISTRATION.read_text().split())
    source = json.loads(SOURCE.read_text())
    rows = source["rows"]
    n_standing = sum(r["tweak"] == STANDING for r in rows)
    assert f"({n_standing} in {len(rows)})" in text
    assert f"its own {n_standing} cycles' noise" in text
    assert f"the other {len(rows) - n_standing} cycles" in text
    effect = power["standing_effect"]
    assert f"(val_f1 {effect['val_f1']:+.4f}, AUC {effect['roc_auc']:+.4f})" in text
    window = {s["scale"]: s for s in power["scales"]}
    assert (
        window[0.0]["outcomes"]["other"] == 1
        and window[0.0]["outcomes"]["standing"] == 0
    )
    assert (
        f"1 false promotion in {power['simulations']:,} windows like this one" in text
    )

    horizon = power["horizon"]
    assert (
        horizon["cut_at"] == L.HORIZON["cut_at"] == 20 and horizon["cap_cycles"] is None
    )
    assert horizon["simulations"] == L.HORIZON["simulations"]
    by = {s["scale"]: s for s in horizon["scales"]}

    def by_cycle(scale, k):
        fired = by[scale]["fired_at_standing_cycle"]
        return sum(v for n, v in fired.items() if int(n) <= k) / horizon["simulations"]

    assert (
        f"by the 9th cycle in {by_cycle(1.0, 9):.0%} of windows and by the 12th in {by_cycle(1.0, 12):.0%}"
        in text
    )
    assert (
        by_cycle(1.0, 8) < 0.5 <= by_cycle(1.0, 9) and "in about 9 replicates" in text
    )
    assert (
        f"At half the effect it takes it by the 20th in {by_cycle(0.5, 20):.1%}" in text
    )
    assert by[0.0]["outcomes"]["other"] == 1
    assert (
        f"1 in {horizon['simulations']:,} run on to the standing tweak's 20th cycle"
        in text
    )
    days = (
        np.datetime64(source["until"]) - np.datetime64(source["since"])
    ) / np.timedelta64(1, "D")
    assert (
        f"the {n_standing / days:.1f} cycles a day" in text
        and 2.5 < 9 / (n_standing / days) < 3
    )


def test_the_first_horizon_simulations_reproduce(power):
    record = json.loads(SOURCE.read_text())
    again = L.power(record, simulations=20, cut_at=L.HORIZON["cut_at"], deadline=False)
    for got, stored in zip(again["scales"], power["horizon"]["scales"], strict=True):
        assert got["trace"] == stored["trace"][:20]
