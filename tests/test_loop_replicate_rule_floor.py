"""The replicate rule's SD floor (docs/preregistration/2026-10-31_loop_replicate_rule_sd_floor.md) and its record."""

import hashlib
import importlib.util
import json
import math
import re
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / "reports/loop_replicate_rule_sd_floor_2026-10-31.json"
REGISTRATION = ROOT / "docs/preregistration/2026-10-31_loop_replicate_rule_sd_floor.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


L = _load("loop_replicate_rule")
F = _load("loop_replicate_rule_floor")


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text())


def _d(rows, labels, j, i, m, min_others):
    """Cycle i's difference from the other tweaks of its epoch, among cycles that have ended by cycle j."""
    others = [rows[o][m] for o in range(j + 1) if labels[o] != labels[i] and rows[o]["epoch"] == rows[i]["epoch"]]  # fmt: skip
    return rows[i][m] - np.mean(others) if len(others) >= min_others else None


def _brute(rows, labels, measures, min_cycles, min_others):
    """The floored rule as the registration words it, recomputed from scratch at every cycle."""
    out = []
    for j in range(len(rows)):
        T = labels[j]
        mine = [i for i in range(j + 1) if labels[i] == T]
        ts = []
        for m in measures:
            d = [x for x in (_d(rows, labels, j, i, m, min_others) for i in mine) if x is not None]  # fmt: skip
            if len(mine) < min_cycles or len(d) < min_cycles:
                break
            field = [x for x in (_d(rows, labels, j, o, m, min_others) for o in range(j + 1) if labels[o] != T) if x is not None]  # fmt: skip
            sd = max(np.std(d, ddof=1), np.std(field, ddof=1)) if len(field) >= 2 else np.std(d, ddof=1)  # fmt: skip
            ts.append(np.mean(d) / (sd / math.sqrt(len(d))))
        else:
            out.append(min(ts))
            continue
        out.append(-math.inf)
    return np.array(out)


def _synthetic(n=150, seed=3, quiet=None):
    """Six tweaks, t0 lifted. `quiet` (if given) is a tweak with almost no spread, steadily above the field."""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n):
        tweak = f"t{rng.integers(6)}"
        lift = 0.004 if tweak == "t0" else 0.0
        sd = (0.00004, 0.0001) if tweak == quiet else (0.002, 0.006)
        if tweak == quiet:
            lift = 0.002
        rows.append(
            {
                "start": f"2026-10-18T{i // 60:02d}:{i % 60:02d}:00",
                "epoch": "abc"[i * 3 // n],
                "tweak": tweak,
                "val_f1": 0.266 + lift + rng.normal(0, sd[0]),
                "roc_auc": 0.58 + 2 * lift + rng.normal(0, sd[1]),
            }
        )
    return rows


@pytest.mark.parametrize("measures", list(L.MEASURES.values()))
@pytest.mark.parametrize("min_cycles", [3, 6])
@pytest.mark.parametrize("quiet", [None, "t3"])
def test_floored_scores_are_the_rule_as_written(measures, min_cycles, quiet):
    rows = _synthetic(quiet=quiet)
    labels = [r["tweak"] for r in rows]
    got = L.scores(rows, labels, measures, min_cycles, min_others=5, floor=True)
    want = _brute(rows, labels, measures, min_cycles, 5)
    assert np.isfinite(got).sum() > 20
    np.testing.assert_allclose(got, want, rtol=1e-9, atol=1e-12)


def test_the_floor_only_lowers_positive_scores_and_keeps_a_real_lift():
    rows = _synthetic(n=400, quiet="t3")
    labels = [r["tweak"] for r in rows]
    args = (rows, labels, L.MEASURES["val_f1_and_roc_auc"], 6, 10)
    live, floored = L.scores(*args), L.scores(*args, floor=True)
    up = live > 0
    assert up.sum() > 50 and np.all(floored[up] <= live[up] + 1e-12)
    lifted = np.array([t == "t0" for t in labels])
    assert floored[lifted].max() > L.REGISTERED["c"]


def test_a_steady_offset_without_spread_fires_only_without_the_floor():
    rows = _synthetic(n=250, quiet="t3")
    labels = [r["tweak"] for r in rows]
    args = (rows, labels, L.MEASURES["val_f1_and_roc_auc"], 6, 10)
    quiet = np.array([t == "t3" for t in labels])
    assert L.scores(*args)[quiet].max() > 10 * L.REGISTERED["c"]
    assert L.scores(*args, floor=True)[quiet].max() < L.REGISTERED["c"]


def test_the_live_rule_is_the_registered_one_with_the_floor():
    assert L.LIVE == {**L.REGISTERED, "sd_floor": True}
    assert F.RULE == L.LIVE


def test_the_record_is_its_sources(record):
    for name in ("discovery", "confirmation"):
        src = record["sources"][name]
        assert hashlib.sha256((ROOT / src["path"]).read_bytes()).hexdigest() == src["sha256"]  # fmt: skip
    assert record["rule"] == L.LIVE
    rows = record["rows"]["lr_1e-05_promotion"]
    assert len(rows) == 161
    assert record["windows"]["lr_1e-05_promotion"] == F.replay(rows)
    for name in ("discovery", "confirmation"):
        data = json.loads((ROOT / record["sources"][name]["path"]).read_text())
        assert record["windows"][name] == F.replay(sorted(data["rows"], key=lambda r: r["start"]))  # fmt: skip


def test_the_promotion_window_is_what_the_live_rule_read(record):
    rows = record["rows"]["lr_1e-05_promotion"]
    assert rows[-1]["start"] == F.PROMOTION and rows[-1]["tweak"] == "lr_1e-05"
    live = record["windows"]["lr_1e-05_promotion"]["live"]["first_promotion"]
    # the score the loop recorded when it promoted lr 1e-5 (cycles.jsonl, 2026-10-29 12:40:35): t 5.57
    assert live == {"start": F.PROMOTION, "tweak": "lr_1e-05", "tweak_cycles_so_far": 6, "score": 5.5696}  # fmt: skip


def test_the_floor_refuses_lr_1e_05_and_keeps_batchgeneratorsv2(record):
    w = record["windows"]
    assert w["lr_1e-05_promotion"]["floored"]["first_promotion"] is None
    assert w["lr_1e-05_promotion"]["floored"]["best"]["lr_1e-05"] < 1
    for name in ("discovery", "confirmation"):
        live, floored = w[name]["live"], w[name]["floored"]
        assert (
            floored["tweaks_fired"]
            == live["tweaks_fired"]
            == ["aug_mode_batchgeneratorsv2"]
        )
        keep = ("start", "tweak", "tweak_cycles_so_far")
        assert {k: floored["first_promotion"][k] for k in keep} == {k: live["first_promotion"][k] for k in keep}  # fmt: skip
    # the registered window test's first promotion (reports/loop_replicate_rule_window_corrected_2026-10-27.json)
    assert w["confirmation"]["live"]["first_promotion"]["score"] == 7.1689


def test_the_first_null_permutations_reproduce(record):
    discovery = json.loads((ROOT / F.DISCOVERY).read_text())
    got = F.nulls(discovery, permutations=4)
    for name in ("shuffled", "centred"):
        assert got[name]["maxima"] == record["nulls"][name]["maxima"][:4]
        stored = record["nulls"][name]
        assert stored["false_promotions"] == sum(
            m > L.LIVE["c"] for m in stored["maxima"]
        )
        assert (
            len(stored["maxima"]) == record["nulls"]["permutations"] == L.PERMUTATIONS
        )


def test_the_first_power_simulations_reproduce(record):
    discovery = json.loads((ROOT / F.DISCOVERY).read_text())
    got = L.power(discovery, simulations=6, reg=L.LIVE)
    for mine, stored in zip(got["scales"], record["power"]["scales"], strict=True):
        assert mine["trace"] == stored["trace"][:6]
        assert (
            sum(stored["outcomes"].values())
            == len(stored["trace"])
            == L.POWER_SIMULATIONS
        )


def test_the_registration_quotes_the_record(record):
    text = REGISTRATION.read_text()
    n = record["power"]["simulations"]
    live = json.loads((ROOT / "reports/loop_replicate_rule_window_power_2026-10-26.json").read_text())  # fmt: skip
    for mine, theirs in zip(record["power"]["scales"], live["scales"], strict=True):
        k = mine["outcomes"]["standing"]
        assert f"{k:,} of {n:,}" in text and mine["outcomes"]["other"] == 0, mine[
            "scale"
        ]
        if theirs["outcomes"]["standing"]:
            assert f"{theirs['outcomes']['standing']:,} of {n:,}" in text
    assert record["power"]["scales"][0]["fired_at_standing_cycle"]["6"] == 400
    assert live["scales"][0]["fired_at_standing_cycle"]["6"] == 451
    for name in ("shuffled", "centred"):
        assert f"{record['nulls'][name]['false_promotions']} in 1,000" in text
    w = record["windows"]
    assert f"{w['confirmation']['floored']['first_promotion']['score']:.2f}" in text
    assert f"{w['lr_1e-05_promotion']['floored']['best']['lr_1e-05']:.2f}" in text
    assert re.search(r"5\.57", text) and re.search(r"7\.17", text)
