"""scripts/loop_tweak_replication.py: each loop tweak against its epoch's other cycles, on one incumbent, and the
registered confirmation (docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md)."""

from __future__ import annotations

import ast
import json
import re
import statistics
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import loop_tweak_replication as ltr  # noqa: E402

RECORD = ROOT / "reports/loop_tweak_replication_2026-10-25.json"
REPORT = ROOT / "reports/loop_tweak_replication_2026-10-25.md"
REGISTRATION = ROOT / "docs/preregistration/2026-10-25_loop_batchgeneratorsv2.md"
INC = 0.265762


def _cycle(n, name, result, stamp, f1, budget=900):
    stats_line = f"val_f1: {f1!r}, loss: 0.5" if f1 is not None else "val_f1: N/A"
    return [
        f"## Cycle {n}: {name} ({result})",
        f"- **Timestamp**: {stamp}",
        f"- **Config**: lr: 0.0005, batch_size: 8, time_budget: {budget}, patch_size: 64",
        f"- **Stats**: {stats_line}",
        "",
    ]


def _shift(tmp_path, name, start, cycles):
    lines = [f"# {name}", f"- **Start Time**: {start}", ""]
    for c in cycles:
        lines += _cycle(*c)
    (tmp_path / f"sprint_log_{name}.md").write_text("\n".join(lines))


def _run(f1, auc, lift, steps, incumbent=INC, thr=0.1, budget=900):
    return [
        f"{ltr.RUN_START}{budget}s)...",
        *(
            f"Step {s} | Loss: 0.5 | LR: 1e-4 | dt: 700ms | Remaining: 10s"
            for s in (10, steps)
        ),
        "avg_mean_ap:           0.5960",
        f"val_f1:                {f1:.6f} (thr {thr:.3f}; incumbent {incumbent:.6f}) ",
        f"ap_prevalence_lift:    {lift:.4f}",
        f"roc_auc:               {auc:.4f}  [selection: F1 gated by AP-lift]",
    ]


@pytest.fixture
def logs(tmp_path):
    _shift(
        tmp_path,
        "2026-10-24_07-48-24_day_shift",
        "07:48:24",
        [
            (1, "a", "REVERTED", "08:05:00", 0.2660),
            (2, "b", "REVERTED", "08:21:00", 0.2700),
            (3, "a", "REVERTED", "08:37:00", 0.2662),
            (
                4,
                "c",
                "REVERTED",
                "09:40:00",
                0.2665,
                3600,
            ),  # a 60-minute cycle: left out
            (5, "b", "REVERTED", "09:56:00", 0.2660),  # the same val_f1 as cycle 1
        ],
    )
    run_log = tmp_path / "run.log"
    run_log.write_text(
        "\n".join(
            _run(
                0.2660, 0.570, 1.10, 1200, incumbent=0.2493
            )  # another incumbent's run, same value
            + _run(0.2660, 0.571, 1.11, 1201)
            + _run(0.2700, 0.590, 1.20, 980)
            + _run(0.2662, 0.572, 1.12, 1202)
            + _run(0.2665, 0.575, 1.15, 4000, budget=3600)
            + _run(0.2660, 0.580, 1.16, 1203)
            + [
                "Starting Gated UNet-Transformer Loop (Budget: 900s)...",
                "Step 10 | x",
            ]  # unscored
        )
        + "\n"
    )
    return str(tmp_path / "sprint_log_*.md"), str(run_log)


def test_runs_reads_each_scored_run(logs):
    _, run_log = logs
    by = ltr.runs([run_log])
    assert sorted(by) == [0.266, 0.2662, 0.2665, 0.27]
    assert by[0.27] == [{"threshold": 0.1, "incumbent": INC, "ap_lift": 1.2, "roc_auc": 0.59, "mean_ap": 0.596, "steps": 980}]  # fmt: skip
    assert [r["incumbent"] for r in by[0.266]] == [0.2493, INC, INC]


def test_cycles_join_their_runs_in_time_order_on_this_incumbent(logs):
    sprint, run_log = logs
    rows, tally = ltr.cycles(
        [sprint], [run_log], "2026-10-24T07:48:24", "2026-10-25T00:00:00", INC
    )
    assert tally == {
        "cycles": 5,
        "unscored": 0,
        "other_budget": 1,
        "unmatched": 0,
        "promoted": None,
    }
    assert [(r["tweak"], r["val_f1"], r["roc_auc"], r["steps"]) for r in rows] == [
        ("a", 0.2660, 0.571, 1201),  # not the 0.2493 incumbent's run of the same value
        ("b", 0.2700, 0.590, 980),
        ("a", 0.2662, 0.572, 1202),
        ("b", 0.2660, 0.580, 1203),  # the value's second run on this incumbent
    ]
    assert {r["epoch"] for r in rows} == {"bf8a957c"}


def test_a_value_whose_runs_do_not_pair_off_is_left_unmatched(logs, tmp_path):
    sprint, run_log = logs
    text = Path(run_log).read_text()
    Path(run_log).write_text(text + "\n".join(_run(0.2660, 0.5, 1.0, 9)) + "\n")
    rows, tally = ltr.cycles(
        [sprint], [run_log], "2026-10-24T07:48:24", "2026-10-25T00:00:00", INC
    )
    assert tally["unmatched"] == 2
    assert [("roc_auc" in r) for r in rows] == [False, True, True, False]


def test_a_promotion_ends_a_window_or_refuses_it(tmp_path):
    _shift(
        tmp_path,
        "2026-10-24_07-48-24_day_shift",
        "07:48:24",
        [
            (1, "a", "REVERTED", "08:05:00", 0.26),
            (2, "b", "SUCCESS", "08:21:00", 0.28),
            (3, "c", "REVERTED", "08:37:00", 0.25),
        ],  # fmt: skip
    )
    run_log = tmp_path / "run.log"
    run_log.write_text(
        "\n".join(_run(0.26, 0.5, 1.0, 9) + _run(0.28, 0.6, 1.2, 9)) + "\n"
    )
    args = ([str(tmp_path / "sprint_log_*.md")], [str(run_log)], "2026-10-24T07:00:00", "2026-10-25T00:00:00", INC)  # fmt: skip
    with pytest.raises(SystemExit, match="promoted"):
        ltr.cycles(*args)
    rows, tally = ltr.cycles(*args, stop_at_promotion=True)
    assert [r["tweak"] for r in rows] == ["a", "b"]
    assert tally["promoted"] == {"tweak": "b", "start": "2026-10-24T08:05:00"}


def test_an_epoch_starts_at_its_merge():
    assert ltr.epoch_of("2026-10-23T21:01:48") == "42f29ba2"
    assert ltr.epoch_of("2026-10-23T21:01:49") == "bf8a957c"
    assert ltr.epoch_of("2026-10-17T14:01:57") == "1b7a304c"
    with pytest.raises(ValueError):
        ltr.epoch_of("2026-10-17T14:01:55")
    starts = [w for w, _, _ in ltr.EPOCHS]
    assert starts == sorted(starts)


def _rows(spec):
    """(epoch, tweak, val_f1[, auc, lift]) -> rows."""
    out = []
    for i, s in enumerate(spec):
        e, t, f1, *rest = s
        r = {
            "start": f"2026-10-2{i // 10}T{i % 10:02d}:00:00",
            "epoch": e,
            "tweak": t,
            "val_f1": f1,
        }
        if rest:
            r["roc_auc"], r["ap_lift"] = rest
        out.append(r)
    return out


def test_an_effect_is_measured_against_its_own_epochs_other_cycles():
    rows = _rows(
        [
            ("E1", "x", 0.30),
            ("E1", "y", 0.28),
            ("E1", "z", 0.26),
            ("E2", "x", 0.21),
            ("E2", "y", 0.20),
            ("E2", "z", 0.22),
        ]  # fmt: skip
    )
    e = ltr.effects(rows, "val_f1")
    # x: 0.30 - mean(0.28, 0.26) = +0.03; 0.21 - mean(0.20, 0.22) = 0.00
    assert e["x"]["n"] == 2 and e["x"]["mean_diff"] == pytest.approx(0.015)
    assert e["x"]["sd"] == pytest.approx(statistics.stdev([0.03, 0.0]))
    # Holm: adjusted p never below the raw p, and monotone in the raw order
    order = sorted(e, key=lambda k: e[k]["p"])
    assert all(e[k]["p_holm"] >= e[k]["p"] for k in e)
    assert [e[k]["p_holm"] for k in order] == sorted(e[k]["p_holm"] for k in order)


def _window(n_standing, others=70, f1=0.004, auc=0.012, lift=0.04, bar_hit=False):
    spec = []
    for i in range(others):
        spec.append(("E", f"t{i % 7}", 0.267 + 0.001 * ((i % 3) - 1), 0.578, 1.18))
    for i in range(n_standing):
        hit = 0.276 if bar_hit and i == 0 else 0.267 + f1 + 0.0005 * ((i % 3) - 1)
        spec.append(("E", "aug_mode_batchgeneratorsv2", hit, 0.578 + auc, 1.18 + lift))
    return _rows(spec)


@pytest.mark.parametrize(
    "kw,reading,preds",
    [
        ({}, "CONFIRMED", {"P1": True, "P2": True, "P3": True, "P4": True}),
        ({"auc": 0.001}, "F1_ONLY", {"P1": True, "P2": False, "P3": True, "P4": True}),
        (
            {"f1": 0.001, "lift": 0.01},
            "NOT_REPLICATED",
            {"P1": False, "P2": True, "P3": False, "P4": True},
        ),
        (
            {"bar_hit": True},
            "CONFIRMED",
            {"P1": True, "P2": True, "P3": True, "P4": False},
        ),
    ],
)
def test_the_registered_reading(kw, reading, preds):
    v = ltr.registered_verdict(
        _window(8, **kw), {"unmatched": 0, "promoted": None}, INC
    )
    assert (v["status"], v["reading"], v["predictions"]) == ("OK", reading, preds)


def test_a_short_window_or_an_unmatched_run_gives_no_reading():
    tally = {"unmatched": 0, "promoted": None}
    for rows in (_window(5), _window(8, others=59)):
        v = ltr.registered_verdict(rows, tally, INC)
        assert (
            v["status"] == "INCOMPLETE"
            and v["reading"] is None
            and "predictions" not in v
        )
    v = ltr.registered_verdict(_window(8), {"unmatched": 1, "promoted": None}, INC)
    assert (
        v["status"] == "UNMATCHED_RUNS"
        and v["reading"] is None
        and "predictions" not in v
    )


def test_the_window_ends_with_the_eighth_standing_cycle():
    rows = _window(8) + _rows([("E", "t0", 0.20, 0.50, 1.0)] * 30 + [("E", "aug_mode_batchgeneratorsv2", 0.20, 0.5, 1.0)] * 4)  # fmt: skip
    for i, r in enumerate(rows):  # in time order
        r["start"] = f"2026-10-26T{i // 60:02d}:{i % 60:02d}:00"
    v = ltr.registered_verdict(rows, {"unmatched": 0, "promoted": None}, INC)
    assert (v["n_standing"], v["n_others"], v["reading"]) == (8, 70, "CONFIRMED")


def test_the_tolerance_is_train_pys():
    tree = ast.parse((ROOT / "scripts/training/train.py").read_text())
    value = next(
        n.value.value
        for n in tree.body
        if isinstance(n, ast.Assign)
        and getattr(n.targets[0], "id", None) == "F1_NOISE_TOLERANCE"
    )
    assert value == ltr.TOLERANCE


def test_the_registration_states_the_scripts_rule():
    txt = " ".join(REGISTRATION.read_text().split())
    reg = ltr.REGISTERED
    assert "from 2026-10-25 16:00 PDT" in txt and reg["since"] == "2026-10-25T16:00:00"
    assert f"the end of the {reg['cut_at']}th `{reg['standing']}` cycle" in txt
    assert "2026-10-29 16:00:00 PDT" in txt and reg["deadline"] == "2026-10-29T16:00:00"
    assert (
        f"fewer than {reg['min_standing']} standing cycles, or fewer than {reg['min_others']} others"
        in txt
    )
    assert f"**P1, val_f1 effect ≥ +{reg['P1_val_f1']:.4f}.**" in txt
    assert f"**P2, ROC AUC effect ≥ +{reg['P2_roc_auc']:.4f}.**" in txt
    assert f"**P3, AP prevalence lift effect ≥ +{reg['P3_ap_lift']:.3f}.**" in txt


def test_the_record_recomputes_from_its_rows():
    d = json.loads(RECORD.read_text())
    rows = d["rows"]
    assert d["tally"] == {
        "cycles": 580,
        "unscored": 0,
        "other_budget": 34,
        "unmatched": 0,
        "promoted": None,
    }
    assert len(rows) == 546 and all(r.get("roc_auc") is not None for r in rows)
    assert {r["incumbent"] for r in rows} == {d["incumbent"]} == {INC}
    assert all(ltr.epoch_of(r["start"]) == r["epoch"] for r in rows)
    for m in ltr.MEASURES:
        assert ltr.effects(rows, m) == d["effects"][m]
    assert ltr.summary(rows, "aug_mode_batchgeneratorsv2", INC) == d["standing"]
    assert d["epochs"] == [{"from": w, "sha": s, "change": c} for w, s, c in ltr.EPOCHS]


def test_the_registration_quotes_the_record():
    d = json.loads(RECORD.read_text())
    e = {
        m: d["effects"][m]["aug_mode_batchgeneratorsv2"]
        for m in ("val_f1", "roc_auc", "ap_lift")
    }
    txt = " ".join(REGISTRATION.read_text().split())
    n = e["val_f1"]["n"]
    assert f"on all {n} of the loop's cycles that ran it" in txt
    assert (
        f"its val_f1 is +{e['val_f1']['mean_diff']:.4f} higher, its ROC AUC +{e['roc_auc']['mean_diff']:.4f} and its "
        f"AP prevalence lift +{e['ap_lift']['mean_diff']:.3f}." in txt
    )
    assert (
        f"differences from its epoch's other cycles have SD {e['val_f1']['sd']:.4f} (val_f1), "
        f"{e['roc_auc']['sd']:.4f} (AUC) and {e['ap_lift']['sd']:.3f} (AP lift), n = {n}."
        in txt
    )
    assert f"{n} of its {len(d['rows'])} 15-minute cycles" in txt
    s = d["standing"]
    assert (
        f"0 of {n}, and a normal approximation gives {100 * s['p_clear_one_cycle_normal']:.1f}% per cycle"
        in txt
    )
    assert s["cleared_bar"] == 0
    assert (
        f"trains about {s['steps_median']:,.0f} steps in 15 minutes, against {s['steps_median_others']:,.0f} for the "
        "others" in txt
    )
    for k, key in (("val_f1", "P1"), ("roc_auc", "P2"), ("ap_lift", "P3")):
        se = e[k]["sd"] / 8**0.5
        quoted = re.search(rf"\*\*{key},[^*]+\*\* Exploratory \+[0-9.]+(?:;|,) (?:with n = 8 its )?standard error (?:is )?about ([0-9]+\.[0-9]*[0-9])", txt)  # fmt: skip
        assert quoted, key
        assert abs(float(quoted.group(1)) - se) <= 0.5 * 10 ** -(
            len(quoted.group(1).split(".")[1])
        ), (key, se)


def _p(p):
    return f"{p:.0e}" if p < 0.001 else f"{p:.1g}"


def _s(x, places):
    return f"{x:+.{places}f}".replace("-", "−")


def test_the_report_is_the_record():
    import numpy as np

    d = json.loads(RECORD.read_text())
    e, rows, s = d["effects"], d["rows"], d["standing"]
    txt = REPORT.read_text()
    flat = " ".join(txt.split())
    bg = "aug_mode_batchgeneratorsv2"
    for t in (bg, "use_uamt_False", "loss_ink_bce_0.2"):
        cells = " | ".join(
            f"{_s(e[m][t]['mean_diff'], k)} (p {_p(e[m][t]['p_holm'])})"
            for m, k in (("val_f1", 4), ("roc_auc", 4), ("ap_lift", 3))  # fmt: skip
        )
        assert f"| `{t}` | {e['val_f1'][t]['n']} | {cells} |" in txt, t
    up = {
        m: {k for k, v in e[m].items() if v["p_holm"] < 0.05 and v["mean_diff"] > 0}
        for m in e
    }
    assert up["roc_auc"] | up["ap_lift"] == {bg}
    assert up["val_f1"] == {bg, "use_uamt_False", "loss_ink_bce_0.2"}
    moved = {k for k, v in e["mean_ap"].items() if v["p_holm"] < 0.05}
    assert (
        f"It moves with {len(moved)} of the {len(e['mean_ap'])} tweaks at Holm p < 0.05, in both directions"
        in flat
    )
    assert any(e["mean_ap"][k]["mean_diff"] > 0 for k in moved) and any(e["mean_ap"][k]["mean_diff"] < 0 for k in moved)  # fmt: skip

    mine = [r for r in rows if r["tweak"] == bg]
    rest = [r for r in rows if r["tweak"] != bg]

    def m(rs, k):
        return statistics.mean(r[k] for r in rs)

    assert (
        f"Its {len(mine)} cycles average val_f1 {m(mine, 'val_f1'):.4f} (SD {s['val_f1_sd']:.4f}), against "
        f"{m(rest, 'val_f1'):.4f} for the rest." in flat
    )
    assert (
        f"Its AUC averages {m(mine, 'roc_auc'):.3f}, against {m(rest, 'roc_auc'):.3f}, and its AP lift "
        f"{m(mine, 'ap_lift'):.3f}, against {m(rest, 'ap_lift'):.3f}." in flat
    )
    pe = s["per_epoch"]
    assert all(
        v["val_f1_mean"] > v["val_f1_others"]
        and v["roc_auc_mean"] > v["roc_auc_others"]
        for v in pe.values()
    )
    assert f"higher in each of the {['', 'one', 'two', 'three', 'four', 'five', 'six', 'seven'][len(pe)]} code epochs it ran in" in flat  # fmt: skip
    assert (
        f"The window holds {['', '', '', '', '', '', '', 'seven', 'eight'][len(d['epochs'])]} code epochs"
        in flat
    )
    n = [v["n"] for v in e["val_f1"].values()]
    assert flat.count(f"{min(n)} to {max(n)} times") == 2 and len(n) == 26
    t = d["tally"]
    assert (
        f"Of the {t['cycles']} cycles, {t['other_budget']} ran for 60 minutes (the nights up to 10-20) and are left "
        f"out. The other {len(rows)} ran 15 minutes, and all are matched." in flat
    )
    # the bar, and the margin over predicting ink everywhere (finding 88's 0.2451 on this sample)
    assert (
        f"The bar is {s['bar']:.6f}" in flat
        and f"None of the {len(rows)} cycles reached it" in flat
    )
    top = max(rows, key=lambda r: r["val_f1"])
    assert (
        top["tweak"] == bg
        and f"The highest was {top['val_f1']:.4f}, a batchgeneratorsv2 cycle." in flat
    )
    assert (
        f"clears the bar with probability {100 * s['p_clear_one_cycle_normal']:.1f}%"
        in flat
    )
    assert f"the incumbent is {INC - 0.2451:.3f} above it. batchgeneratorsv2 adds {e['val_f1'][bg]['mean_diff']:.3f}" in flat  # fmt: skip
    assert (
        0.18 < e["val_f1"][bg]["mean_diff"] / (INC - 0.2451) < 0.23
    )  # "about a fifth"
    # the step count
    med = {k: statistics.median(r["steps"] for r in rows if r["tweak"] == k) for k in ("batch_size_16", "use_uamt_False")}  # fmt: skip
    assert (
        f"a median of {s['steps_median']:,.0f}, against {s['steps_median_others']:,.0f} for the others"
        in flat
    )
    assert f"`batch_size_16` trains a median of {med['batch_size_16']:,.0f} steps, and its val_f1 is not higher ({_s(e['val_f1']['batch_size_16']['mean_diff'], 4)})" in flat  # fmt: skip
    assert f"which trains {med['use_uamt_False']:,.0f} steps" in flat
    ot = [r for r in rest if r["tweak"] != "use_uamt_False"]
    r = np.corrcoef([x["steps"] for x in ot], [x["val_f1"] for x in ot])[0, 1]
    assert f"the correlation is {_s(r, 2)} over {len(ot)} cycles" in flat


def test_the_registered_command_reads_both_run_logs():
    """The loop renames run.log to run.log.old past 10 MB, so the window's runs can span both; the exploratory record
    read both, and amendment 1 makes the registered command do the same."""
    loop = (ROOT / "run_autoresearch_loop.py").read_text()
    assert (
        'os.rename("run.log", "run.log.old")' in loop
        and 'os.remove("run.log.old")' in loop
    )
    assert [Path(p).name for p in json.loads(RECORD.read_text())["sources"]["run_logs"]] == ["run.log.old", "run.log"]  # fmt: skip
    txt = REGISTRATION.read_text()
    commands = re.findall(
        r"^ {4}python3 scripts/loop_tweak_replication\.py --registered .*\n.*$",
        txt,
        re.M,
    )
    assert len(commands) == 2  # the original, and amendment 1's, which replaces it
    assert "--run-log run.log --out" in commands[0]
    assert "--run-log run.log.old run.log --out" in commands[1]
    assert (
        "**Amendment 1 (2026-10-26, during the window, before any analysis of it;"
        in txt
    )
    assert "joined to the run logs as in the exploratory report" in " ".join(
        txt.split()
    )
