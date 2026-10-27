"""Bind the steps-vs-ranking analysis (scripts/loop_steps_vs_ranking.py) to its source record and its report."""

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "reports/loop_tweak_replication_2026-10-25.json"
RECORD = ROOT / "reports/loop_steps_vs_ranking_2026-10-26.json"
REPORT = ROOT / "reports/loop_steps_vs_ranking_2026-10-26.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


S = _load("loop_steps_vs_ranking")
STANDING = S.STANDING


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text())


def test_the_record_regenerates_from_its_source(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    out = tmp_path / "steps.json"
    S.main(["--record", SOURCE, "--out", str(out)])
    actual, expected = json.loads(out.read_text()), json.loads(RECORD.read_text())

    def same(a, b):
        # BLAS/runtime versions can change the last bits of reductions and
        # least-squares coefficients. Identities, counts and p-values stay exact.
        assert type(a) is type(b)
        if isinstance(a, dict):
            assert a.keys() == b.keys()
            for key in a:
                if key == "permutation_p":
                    assert a[key] == b[key]
                else:
                    same(a[key], b[key])
        elif isinstance(a, list):
            assert len(a) == len(b)
            for x, y in zip(a, b):
                same(x, y)
        elif isinstance(a, float):
            assert a == pytest.approx(b, rel=1e-12, abs=1e-14)
        else:
            assert a == b

    same(actual, expected)


def test_the_source_ends_before_the_window(record):
    assert record["last_start"] < S.ltr.REGISTERED["since"]
    rows = json.loads((ROOT / SOURCE).read_text())["rows"]
    late = dict(rows[0], start=S.ltr.REGISTERED["since"])
    with pytest.raises(SystemExit, match="window"):
        S.analyse({"rows": [*rows, late]}, permutations=1, bootstraps=1)


def _rows(slope_auc, n=12, seed=3):
    """Tweaks whose step levels and AUC levels run against each other between tweaks, with slope_auc (per 100
    steps) inside each tweak: only the inside should be read."""
    rng = np.random.default_rng(seed)
    rows = []
    for k, level in enumerate((700, 1000, 1300, 1600, 4000)):
        for j in range(n):
            dev = rng.normal(0, 90)
            rows.append(
                {"tweak": f"t{k}", "epoch": "e", "start": f"2026-10-2{j % 4}T{10 + j % 9:02d}:00:00",
                 "steps": level + dev, "val_f1": 0.266 + rng.normal(0, 0.002),
                 "roc_auc": 0.58 + 0.03 * k + slope_auc * dev / 100 + rng.normal(0, 0.0005),
                 "ap_lift": 1.1 + rng.normal(0, 0.01)}
            )  # fmt: skip
    return rows


@pytest.mark.parametrize("planted", [-0.002, 0.0, 0.0015])
def test_the_slope_is_read_within_groups_only(planted):
    rows = _rows(planted)
    dev = S.deviations(rows)
    got = S.slope(dev, "roc_auc")
    assert (
        abs(got["per_100_steps"] - planted) < 4 * got["se"]
    )  # unbiased: mean z 0.06 over 300 seeds
    assert len({(d["tweak"], d["epoch"]) for d in dev}) == 5
    # Pooled without the groups, the tweaks' levels would be read as a slope.
    x = np.array([r["steps"] for r in rows]) / 100
    pooled = np.polyfit(x, [r["roc_auc"] for r in rows], 1)[0]
    assert abs(pooled - planted) > 20 * got["se"]


def test_the_step_gap_leaves_out_tweaks_whose_steps_are_another_size():
    rows = [{"tweak": STANDING, "epoch": "e", "steps": 900}]
    rows += [{"tweak": "a", "epoch": "e", "steps": s} for s in (1150, 1250)]
    rows += [{"tweak": "use_uamt_False", "epoch": "e", "steps": 4100}]
    rows += [{"tweak": "batch_size_16", "epoch": "e", "steps": 600}]
    assert S.step_gap(rows) == -300
    assert S.step_gap(rows, leave_out=()) == pytest.approx(
        900 - (1150 + 1250 + 4100 + 600) / 4
    )


def test_the_window_adjustment_is_cut_at_the_8th_standing_cycle(record):
    rows = []
    for j in range(60):
        standing = j % 6 == 2
        rows.append(
            {"start": f"2026-10-2{6 + j // 24}T{j % 24:02d}:00:00", "epoch": "139c6873",
             "tweak": STANDING if standing else f"t{j % 4}", "steps": 900 if standing else 1200,
             "val_f1": 0.27 if standing else 0.266, "roc_auc": 0.59 if standing else 0.58,
             "ap_lift": 1.15 if standing else 1.1}
        )  # fmt: skip
    cut = [j for j, r in enumerate(rows) if r["tweak"] == STANDING][7]
    for r in rows[cut + 1 :]:  # what the verdict drops must not count
        r["steps"], r["roc_auc"] = 99_999, 0.0
    got = S.window_adjustment({"rows": rows}, record)
    assert got["step_gap"] == pytest.approx(-300)
    for m, effect in (("val_f1", 0.004), ("roc_auc", 0.01), ("ap_lift", 0.05)):
        slope = record["measures"][m]["per_100_steps"]
        assert got[m]["effect"] == pytest.approx(effect)
        assert got[m]["from_its_steps"] == pytest.approx(-3 * slope)
        assert got[m]["beyond_its_steps"] == pytest.approx(effect + 3 * slope)


def _s(x, places):
    s = f"{x:+.{places}f}"
    return f"{0:.{places}f}" if float(s) == 0 else s.replace("-", "−")


def _pct(x):
    return f"{x:.0f}%".replace("-", "−")


NAMES = {"val_f1": "val_f1", "roc_auc": "ROC AUC", "ap_lift": "AP prevalence lift"}
BIN_LABELS = (
    "150 or more fewer",
    "50 to 150 fewer",
    "within 50",
    "50 to 150 more",
    "150 or more more",
)


def test_the_report_is_the_record(record):
    txt = REPORT.read_text()
    for m, v in record["measures"].items():
        k = 4 if m == "ap_lift" else 5
        cells = [
            _s(v["per_100_steps"], k),
            f"{_s(v['ci95'][0], k)} to {_s(v['ci95'][1], k)}",
            f"{v['permutation_p']:.3f}",
            f"{_s(v['day_bootstrap95'][0], k)} to {_s(v['day_bootstrap95'][1], k)}",
            _s(v["with_hours"], k),
            f"{_s(v['leave_one_tweak_out'][0], k)} to {_s(v['leave_one_tweak_out'][1], k)}",
            "{} of {}".format(*v["tweaks_with_negative_slope"]),
        ]
        assert f"| {NAMES[m]} | {' | '.join(cells)} |" in txt, m
    for label, b in zip(BIN_LABELS, record["bins"], strict=True):
        cells = [
            str(b["n"]),
            _s(b["steps"], 0),
            _s(b["val_f1"], 4),
            _s(b["roc_auc"], 4),
            _s(b["ap_lift"], 3),
        ]
        assert f"| {label} | {' | '.join(cells)} |" in txt, label
    st = record["standing"]
    for m in ("val_f1", "roc_auc", "ap_lift"):
        k = 3 if m == "ap_lift" else 4
        e, p = st["effects"][m], st["from_its_steps"][m]
        cells = [
            _s(e, k),
            f"{_s(p['predicted'], k)} ({_s(p['ci95'][0], k)} to {_s(p['ci95'][1], k)})",
            f"{_pct(100 * p['predicted'] / e)} ({_pct(100 * p['ci95'][0] / e)} to {_pct(100 * p['ci95'][1] / e)})",
            _s(e - p["predicted"], k),
        ]
        assert f"| {NAMES[m]} | {' | '.join(cells)} |" in txt, m
    flat = " ".join(txt.split())
    assert f"trained {-st['step_gap']:.0f} fewer steps" in flat
    assert f"({-st['step_gap_against_every_tweak']:.0f} fewer counting UAMT off" in flat
    assert f"{record['deviations']} cycles in {record['groups']} groups" in flat
    assert f"({record['permutations']:,} times)" in flat
    assert f"({_s(st['its_own_slope']['roc_auc'], 4)} AUC per 100 steps)" in flat
    assert f"gained {_s(record['bins'][0]['roc_auc'], 4)} AUC" in flat
    assert f"lost about {round(-record['bins'][0]['steps'], -1):.0f} steps" in flat
    assert f"its {-st['step_gap']:.0f} fewer steps" in flat
    # What is left still clears the confirmation's own thresholds, as the report says.
    reg = S.ltr.REGISTERED
    beyond = {
        m: st["effects"][m] - st["from_its_steps"][m]["predicted"]
        for m in st["effects"]
    }
    assert (
        beyond["roc_auc"] >= reg["P2_roc_auc"]
        and beyond["ap_lift"] >= reg["P3_ap_lift"]
    )
    assert "clears the confirmation's own thresholds" in flat


def test_the_reports_spread_and_cross_recipe_figures(record):
    source = json.loads((ROOT / SOURCE).read_text())
    dev = S.deviations(source["rows"])
    steps = np.array([d["steps"] for d in dev])
    flat = " ".join(REPORT.read_text().split())
    assert (
        f"SD {steps.std(ddof=1):.0f} steps; half lie within {np.median(abs(steps)):.0f}"
        in flat
    )
    e = source["effects"]["roc_auc"]
    assert f"scores {_s(e['use_uamt_False']['mean_diff'], 4)} AUC" in flat
    assert f"scores {_s(e['batch_size_16']['mean_diff'], 4)}." in flat
    days = {d["day"] for d in dev}
    assert f"(only {len(days)} days" in flat
