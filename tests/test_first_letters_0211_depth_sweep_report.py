"""The finding-135 report states its record's numbers and the verdict its registered rules give."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_0211_depth_sweep.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_0211_depth_sweep.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


ds = _load(
    "depth_sweep_for_report",
    ROOT / "repro/first_letters/pherc0211_control/depth_sweep.py",
)


def _signed(x: float) -> str:
    return f"+{x}" if x > 0 else str(x).replace("-", "−")


def _d(shift: int) -> str:  # a shift as the report writes it
    return "0" if shift == 0 else _signed(shift)


def _ratio(a: float, b: float) -> str:  # a fraction of r(0), as the report writes it
    return f"{a / b:.2f}"


def _curve(by_dir: dict) -> dict:
    return {int(k[1:]): v for k, v in by_dir.items()}


R = {arm: _curve(c) for arm, c in RECORD["registered"]["r"].items()}
H = _curve(RECORD["pherc343"]["r"])


def test_the_record_is_finding_135s_and_names_no_home_path():
    assert RECORD["finding"] == 135 and RECORD["registration_commit"] == "fe6336af"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    assert RECORD["f124_reproduced"] is True
    assert RECORD["f124_r_on_its_own_cells"] == ds.F124_R
    assert RECORD["pherc343"]["f127_reproduced"] is True and H[0] == ds.F127_R
    assert RECORD["shifts"] == list(ds.SHIFTS)
    assert sorted(R) == sorted(ds.ARMS) and all(
        sorted(c) == sorted(ds.SHIFTS) for c in R.values()
    )


def test_the_verdict_follows_the_registered_rules():
    verdict, best, gains = ds.verdict(R, RECORD["cell_share"], True)
    assert verdict == RECORD["verdict"] == "DEPTH_ZERO_BEST"
    assert best == RECORD["registered"]["best_shift"] == 0
    assert gains == RECORD["registered"]["gain_over_zero"]
    assert all(max(c, key=c.get) == 0 for c in R.values())  # each arm's own best too
    assert f"**Verdict `{verdict}`**, as predicted" in REPORT
    assert "**So the band reads keep layers 41 to 26**" in REPORT
    assert all(s > ds.f118.MIN_CELL_SHARE for s in RECORD["cell_share"].values())
    cosines = [c for a in RECORD["arms"].values() for c in a["normal_cosine_median"]]
    assert max(cosines) < 0
    assert (
        f"(median cosines {_signed(max(cosines))} to {_signed(min(cosines))})" in FLAT
    )


def test_the_registered_table_is_the_records():
    for arm in ds.ARMS:
        share = RECORD["cell_share"][arm]
        assert f"{RECORD['cells'][arm]:,}" in FLAT and f"(share {share})" in FLAT
        # every shift reaches the cells D = 0 reaches: the arm's own cells
        assert all(
            n["cells"] == RECORD["cells"][arm]
            for n in RECORD["described"]["each_shift"][arm].values()
        )
    assert f"of the winner's {RECORD['mask_cells']:,} mask cells" in FLAT
    for d in ds.SHIFTS:
        e, n = R["e2e"][d], R["dense2s3"][d]
        de = " " if d == 0 else f" {_signed(round(e - R['e2e'][0], 4))} "
        dn = " " if d == 0 else f" {_signed(round(n - R['dense2s3'][0], 4))} "
        row = f"| {_d(d)} | {e} |{de}| {n} |{dn}| {round(e + n, 4)} |"
        assert row in REPORT, row


def test_the_predictions_are_scored_from_the_record():
    near = {
        arm: max(abs(round(R[arm][d] - R[arm][0], 4)) for d in (-2, -1, 1, 2))
        for arm in ds.ARMS
    }
    assert max(near.values()) < 0.05  # prediction 2
    worst = max(ds.ARMS, key=near.get)
    worst_d = max((-2, -1, 1, 2), key=lambda d: abs(R[worst][d] - R[worst][0]))
    assert (
        f"The largest change is {_signed(round(R[worst][worst_d] - R[worst][0], 4))}, `{worst}` at {_d(worst_d)}"
        in FLAT
    )
    best343 = RECORD["pherc343"]["best_shift"]
    assert best343 in (-1, 0, 1) and f"held ({_d(best343)})" in FLAT  # prediction 4
    assert (
        RECORD["repeat_w035"]["identical"] is True
        and RECORD["repeat_w035"]["max_abs_difference"] == 0.0
    )  # prediction 5
    assert "The repeat is identical: held." in FLAT


def test_the_tolerance_and_the_half_widths_are_the_records():
    def change(arm, d):
        return abs(round(R[arm][d] - R[arm][0], 4))

    one = max(change(a, d) for a in ds.ARMS for d in (-1, 1))
    two = max(change(a, d) for a in ds.ARMS for d in (-2, -1, 1, 2))
    assert (
        f"Over ±1 layer, r stays within {one} of r(0) in both arms; over ±2, within {two}"
        in FLAT
    )
    inward = sorted(change(a, -4) for a in ds.ARMS)
    outward = sorted(change(a, 4) for a in ds.ARMS)
    assert (
        f"Four layers costs {inward[0]} to {inward[1]} inward and {outward[0]} to {outward[1]} outward"
        in FLAT
    )
    halves = RECORD["described"]["half_widths"]
    for arm in ds.ARMS:
        assert ds.half_widths(R[arm]) == halves[arm]
    assert ds.half_widths(H) == RECORD["pherc343"]["half_widths"]
    rows = {"e2e": "`e2e`", "dense2s3": "`dense2s3`"}
    for name, curve, half in (
        *((rows[a], R[a], halves[a]) for a in ds.ARMS),
        ("PHerc. 343 (described)", H, RECORD["pherc343"]["half_widths"]),
    ):
        cells = " | ".join(
            "beyond 8" if half[side] is None else str(half[side])
            for side in ("inward", "outward")
        )
        ratios = f"{_ratio(curve[-8], curve[0])} | {_ratio(curve[8], curve[0])}"
        assert f"| {name} | {cells} | {ratios} |" in REPORT, name
    six = [_ratio(R[a][6], R[a][0]) for a in ds.ARMS] + [_ratio(H[6], H[0])]
    minus = [_ratio(R[a][-6], R[a][0]) for a in ds.ARMS] + [_ratio(H[-6], H[0])]
    assert all(
        float(p) < float(m) for p, m in zip(six, minus, strict=True)
    )  # faster outward, both places
    assert (
        f"At +6, r is {six[0]} and {six[1]} of r(0) at PHerc. 211 and {six[2]} at PHerc. 343"
        in FLAT
    )
    assert f"at −6 it is {minus[0]}, {minus[1]} and {minus[2]}" in FLAT
    assert (
        f"reads {abs(round(R['e2e'][-1] - R['e2e'][0], 4))} (`e2e`) and "
        f"{abs(round(R['dense2s3'][-1] - R['dense2s3'][0], 4))} (`dense2s3`) below D = 0"
        in FLAT
    )


def test_the_winding_and_343_tables_are_the_records():
    by = RECORD["described"]["by_winding"]
    for w in RECORD["windings"]:
        cells = []
        for arm in ds.ARMS:
            c = _curve(by[arm][w]["r"])
            best = max(ds.SHIFTS, key=lambda d: (c[d], -abs(d), d))
            cells.append(
                "0"
                if best == 0
                else f"{_d(best)} ({_signed(round(c[best] - c[0], 4))})"
            )
        row = f"| {w} | {by['e2e'][w]['cells']:,} | {cells[0]} | {cells[1]} |"
        assert row in REPORT, row
    fewest = min(RECORD["windings"], key=lambda w: by["e2e"][w]["cells"])
    assert f"Only {fewest}, the winding with fewest cells" in FLAT
    row = " | ".join(str(H[d]) for d in ds.SHIFTS)
    assert f"| r | {row} |" in REPORT
    assert f"on its {RECORD['pherc343']['cells']:,} cells" in FLAT
    best343 = RECORD["pherc343"]["best_shift"]
    assert (
        f"Its best shift is {_d(best343)}, by {_signed(round(H[best343] - H[0], 4))}"
        in FLAT
    )
    at4 = f"{_ratio(H[-4], H[0])} and {_ratio(H[4], H[0])}"
    four = sorted(
        (_ratio(R[a][d], R[a][0]) for a in ds.ARMS for d in (-4, 4)), key=float
    )
    assert (
        f"At ±4 the read there keeps {at4} of r(0), against {four[0]} to {four[-1]} at PHerc. 211"
        in FLAT
    )


def test_the_controls_are_the_records():
    es = RECORD["described"]["each_shift"]
    gaps = {
        arm: min(
            es[arm][k]["r"] - es[arm][k]["control_slid"]["largest_absolute"]
            for k in es[arm]
        )
        for arm in ds.ARMS
    }
    assert all(g > 0 for g in gaps.values())
    arm = min(gaps, key=gaps.get)
    assert f"The smallest gap is {round(gaps[arm], 4)} (`{arm}`)" in FLAT
    slid = _curve(
        {k: v["control_slid"]["largest_absolute"] for k, v in es["e2e"].items()}
    )
    upto2 = [slid[d] for d in ds.SHIFTS if d <= 2]
    assert (
        f"between {min(upto2)} and {max(upto2)} from −8 to +2 and falls to {slid[8]} at +8"
        in FLAT
    )
    wrong = [es[a]["d+0"]["control_wrong_side"] for a in ds.ARMS]
    assert f"{_signed(wrong[0])} (`e2e`) and {_signed(wrong[1])} (`dense2s3`)" in FLAT
    t = RECORD["described"]["transfer_distance_voxels"]
    assert (
        f"{t['e2e']['p50']} and {t['e2e']['p95']} voxels (`e2e`) and "
        f"{t['dense2s3']['p50']} and {t['dense2s3']['p95']} (`dense2s3`)" in FLAT
    )


def test_the_costs_are_the_records():
    s = RECORD["steps"]
    assert RECORD["seconds"] == sum(g["seconds"] for g in s.values())
    h, rest = divmod(RECORD["seconds"], 3600)
    m, sec = divmod(rest, 60)
    assert f"{h} h {m} min {sec} s in all" in FLAT
    assert f"peaked at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    for step, label in (("check", "check"), ("sweep211", "PHerc. 211, 80 maps with their planes"),
                        ("sweep343", "PHerc. 343, 10 maps with their planes"), ("repeat", "repeat"),
                        ("compare", "compare, both places")):  # fmt: skip
        assert f"| {label} | {s[step]['seconds']} s |" in REPORT, step
    assert f"about {round(s['sweep211']['seconds'] / 80)} s with its planes" in FLAT
    assert f"PHerc. 343 about {round(s['sweep343']['seconds'] / 10)} s" in FLAT


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_0211_depth_sweep.md" in STRATEGY
        and "finding 135" in STRATEGY
    )
    assert f"they give r {R['e2e'][0]} and {R['dense2s3'][0]} at D = 0" in STRATEGY
    two = max(abs(round(R[a][d] - R[a][0], 4)) for a in ds.ARMS for d in (-2, -1, 1, 2))
    assert f"±2 layers r changes by at most {two}" in STRATEGY
