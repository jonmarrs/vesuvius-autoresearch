"""The finding-132 report states its record's numbers and the verdict its registered rule gives them."""

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/studio_skip_empty_windows.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/studio_skip_empty_windows.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())
INPUTS = (("pherc0211", "PHerc. 211"), ("w062", "w062"), ("w065", "w065"))


def _same(pair: dict, lines: dict) -> bool:
    return (
        pair["r"] >= lines["r"]
        and pair["abs_difference"]["p99"] <= lines["p99"]
        and pair["share_same_side_of_half"] >= lines["same_side"]
    )


def test_the_record_is_finding_132s_and_every_step_exited_zero():
    assert RECORD["finding"] == 132 and RECORD["registration_commit"] == "9b99cf7e"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert (
        all(g["exit"] == 0 for g in RECORD["steps"].values())
        and len(RECORD["steps"]) == 4
    )


def test_the_verdict_follows_the_registered_rule():
    lines, pairs = RECORD["lines"], RECORD["pairs"]
    assert (lines["r"], lines["p99"], lines["same_side"], lines["faster"]) == (
        0.9999,
        0.002,
        0.9995,
        0.8,
    )
    assert all(_same(pairs[f"full_{k}"], lines) for k, _ in INPUTS)  # else DOES_NOT_RUN
    assert all(_same(pairs[f"skip_{k}"], lines) for k, _ in INPUTS)  # else SKIP_DIFFERS
    runs = RECORD["runs"]
    for w in ("w062", "w065"):
        ratio = round(runs[f"skip_{w}"]["seconds"] / runs[f"full_{w}"]["seconds"], 4)
        assert ratio == RECORD["time_ratio_skip_over_full"][w] <= lines["faster"]
    assert RECORD["verdict"] == "SKIP_ADOPTED"
    assert f"**Verdict `{RECORD['verdict']}`**, as predicted" in REPORT
    r = RECORD["time_ratio_skip_over_full"]
    assert f"in {r['w062']} and {r['w065']} of the full loop's time" in FLAT
    assert all(0.55 <= v <= 0.65 for v in r.values())  # prediction 2
    assert f"held ({r['w062']} and {r['w065']})" in FLAT


def test_the_tables_are_the_records():
    pairs, runs = RECORD["pairs"], RECORD["runs"]
    for key, label in INPUTS:
        for run in ("full", "skip"):
            p = pairs[f"{run}_{key}"]
            ident = "yes" if p["exact_over_the_ct"] else "no"
            assert (run == "full") == p["exact_over_the_ct"]
            assert (
                f"| {label} | {run} | {p['pixels']:,} | {p['r']} | {p['abs_difference']['p99']} "
                f"| {p['abs_difference']['max']} | {p['share_same_side_of_half']} | {ident} |"
            ) in REPORT, (key, run)
        full, skip = runs[f"full_{key}"], runs[f"skip_{key}"]
        assert (
            full["run"] == full["windows"] == skip["windows"]
            and skip["run"] < full["run"]
        )
        ratio = round(skip["seconds"] / full["seconds"], 4)
        assert (
            f"| {label} | {full['windows']:,} | {skip['run']:,} | {full['seconds']} | {skip['seconds']} | {ratio} |"
            in REPORT
        )
    worst = max(pairs[f"skip_{k}"]["abs_difference"]["max"] for k, _ in INPUTS)
    assert f"by at most {worst}" in FLAT and f"within {worst}" in STRATEGY


def test_the_window_shares_and_costs_are_the_records():
    runs = RECORD["runs"]
    kept = [
        round(runs[f"skip_{w}"]["run"] / runs[f"skip_{w}"]["windows"], 4)
        for w in ("w062", "w065")
    ]
    assert f"(to {kept[0]} and {kept[1]} of them)" in FLAT
    empty = [f"{round(100 * (1 - k), 1):g}%" for k in kept]
    assert f"these two had {empty[0]} and {empty[1]}" in FLAT
    m, s = divmod(RECORD["seconds"], 60)
    assert f"{m} min {s} s in all" in FLAT
    assert f"peaked at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT


def test_the_strategy_carries_the_finding():
    assert (
        "reports/studio_skip_empty_windows.md" in STRATEGY and "finding 132" in STRATEGY
    )
