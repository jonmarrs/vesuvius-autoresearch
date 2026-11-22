"""The finding-136 report states its record's numbers and the verdict its registered rules give."""

import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPORT = (ROOT / "reports/first_letters_343_studio_own.md").read_text()
FLAT = " ".join(REPORT.split())
RECORD = json.loads((ROOT / "reports/first_letters_343_studio_own.json").read_text())
STRATEGY = " ".join((ROOT / "docs/RESEARCH_STRATEGY.md").read_text().split())


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


own = _load(
    "studio_343_own_for_report",
    ROOT / "repro/first_letters/pherc343/studio_343_own.py",
)


def _signed(x: float) -> str:
    return f"+{x}" if x > 0 else str(x).replace("-", "−")


def test_the_record_is_finding_136s_and_names_no_home_path():
    assert RECORD["finding"] == 136 and RECORD["registration_commit"] == "d5f3330e"
    assert (ROOT / RECORD["registration"]).exists()
    assert "/home/" not in json.dumps(RECORD)
    assert all(g["exit"] == 0 for g in RECORD["steps"].values())
    assert RECORD["f127_reproduced"] is True and RECORD["f127_r_again"] == own.F127_R
    assert f"(r {own.F127_R} for Studio on the published surface against `u`)" in FLAT


def test_the_verdict_follows_the_registered_rules():
    cosines = [o["normal_cosine_median"] for o in RECORD["ours"]]
    verdict = own.verdict(RECORD["registered"], RECORD["cell_share"], True, cosines)
    assert verdict == RECORD["verdict"] == "STUDIO_343_OWN_CLOSE"
    assert f"**Verdict `{verdict}`**, as predicted" in REPORT
    assert min(cosines) > 0
    assert f"(median cosines {cosines[0]} and {cosines[1]})" in FLAT
    reg = RECORD["registered"]
    assert f"r is {reg['r']}, above the 0.70 line" in FLAT
    assert all(
        reg["r"] >= own.RATIO * abs(c)
        for c in (reg["control_wrong_side"], reg["control_slid"]["largest_absolute"])
    )


def test_the_registered_table_is_the_records():
    reg = RECORD["registered"]
    assert (
        f"On the {RECORD['cells']:,} of the published area's "
        f"{RECORD['area_cells_covered_by_the_published_render']:,} covered cells that our windings reach "
        f"(share {RECORD['cell_share']})" in FLAT
    )
    assert (
        f"| r, Studio on our windings carried, against Studio on the published surface | {reg['r']} |"
        in REPORT
    )
    assert f"| reversed planes (control) | {reg['control_wrong_side']} |" in REPORT
    slid = reg["control_slid"]
    assert (
        f"| slid 64 pixels (control), largest of four | {slid['largest_absolute']} |"
        in REPORT
    )
    assert (
        f"Up and down it gives {_signed(slid['up'])} and {_signed(slid['down'])}; "
        f"right and left, {slid['right']} and {slid['left']}" in FLAT
    )
    f127 = RECORD["described"]["f127_numbers_again"]
    assert f"(r {f127['r']} for Studio" in FLAT
    assert (
        f"as in finding 127 ({f127['control_slid']['largest_absolute']} there)" in FLAT
    )
    own_rev = RECORD["described"][
        "published_surface_reversed_planes_against_its_forward"
    ]
    assert (
        f"give {own_rev} against its own forward map, about what our reversed planes give "
        f"({reg['control_wrong_side']})" in FLAT
    )


def test_the_predictions_are_scored_from_the_record():
    r = RECORD["registered"]["r"]
    assert 0.75 <= r <= 0.90 and f"held, at the top ({r})" in FLAT  # prediction 2
    u = RECORD["described"]["against_u"]
    ours, pub = u["ours_carried"]["r"], u["published_surface"]["r"]
    assert (
        abs(ours - pub) <= 0.10 and f"held ({ours} against {pub})" in FLAT
    )  # prediction 3
    by = RECORD["described"]["by_winding"]
    assert all(v["r"] >= 0.70 for v in by.values())  # prediction 4
    assert f"held ({by['w047']['r']} and {by['w048']['r']})" in FLAT


def test_the_described_tables_are_the_records():
    by = RECORD["described"]["by_winding"]
    for w, v in by.items():
        assert f"| {w} | {v['cells']:,} | {v['r']} |" in REPORT, w
    assert [by[w]["cells"] for w in ("w047", "w048")] == [
        o["cells_given"] for o in RECORD["ours"]
    ]
    u = RECORD["described"]["against_u"]
    assert f"on the {u['cells']:,} reading-frame cells both maps cover" in FLAT
    for label, key in (
        ("Studio on our windings, carried", "ours_carried"),
        ("Studio on the published surface", "published_surface"),
    ):
        n = u[key]
        row = f"| {label} | {n['r']} | {n['control_wrong_side']} | {n['control_slid']['largest_absolute']} |"
        assert row in REPORT, label
    cost = round(u["published_surface"]["r"] - u["ours_carried"]["r"], 4)
    assert f"our geometry costs Studio {cost} in r" in FLAT
    c = RECORD["described"]["carried"]
    assert f"r with the background in {c['r_with_background']}" in FLAT
    assert (
        f"ink overlap {c['overlap']}, against a slid overlap of {c['control_overlap_slid']['largest']}"
        in FLAT
    )
    t = RECORD["described"]["transfer_distance_voxels"]
    assert f"The transfer distances are {t['p50']} and {t['p95']} voxels" in FLAT
    assert f"The transfer here is closer ({t['p50']} voxels at the median" in FLAT
    assert (
        f"reaches more of the surface ({round(RECORD['cell_share'], 2)} of the area"
        in FLAT
    )


def test_the_costs_are_the_records():
    s = RECORD["steps"]
    assert RECORD["seconds"] == sum(g["seconds"] for g in s.values())
    m, sec = divmod(RECORD["seconds"], 60)
    assert f"{m} min {sec} s in all" in FLAT
    assert f"peaked at {RECORD['gpu_peak_mib_all_processes']:,} MiB" in FLAT
    for step, label in (("check", "check"), ("planes", "planes, two windings in both orders"),
                        ("infer", "Studio, four maps"), ("compare", "compare")):  # fmt: skip
        assert f"| {label} | {s[step]['seconds']} s |" in REPORT, step


def test_the_strategy_carries_the_finding():
    assert (
        "reports/first_letters_343_studio_own.md" in STRATEGY
        and "finding 136" in STRATEGY
    )
    u = RECORD["described"]["against_u"]
    assert (
        f"give r {RECORD['registered']['r']} against Studio's map of that surface"
        in STRATEGY
    )
    assert (
        f"they give {u['ours_carried']['r']}, where Studio on the published surface gives "
        f"{u['published_surface']['r']}" in STRATEGY
    )
