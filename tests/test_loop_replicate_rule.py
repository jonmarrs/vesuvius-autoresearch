"""Bind the replicate-rule replay (scripts/loop_replicate_rule.py) to its source record and its report."""

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
