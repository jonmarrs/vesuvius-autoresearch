"""Bind the host-load analysis (scripts/loop_host_load.py) to its sources, its report and #250's correction."""

import ast
import datetime as dt
import hashlib
import importlib.util
import json
import shutil
import time
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = "reports/loop_tweak_replication_2026-10-25.json"
LOAD = "reports/loop_host_load_cycles_2026-10-26.json"
RECORD = ROOT / "reports/loop_host_load_2026-10-26.json"
REPORT = ROOT / "reports/loop_host_load_2026-10-26.md"


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


H = _load("loop_host_load")
STANDING = H.STANDING


@pytest.fixture(scope="module")
def record():
    return json.loads(RECORD.read_text())


def _same(a, b):
    """Equal, but for the last bits of floats, which BLAS and runtime versions can change (#251)."""
    assert type(a) is type(b)
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for key in a:
            _same(a[key], b[key])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            _same(x, y)
    elif isinstance(a, float):
        assert a == pytest.approx(b, rel=1e-12, abs=1e-14)
    else:
        assert a == b


def test_the_record_regenerates_from_its_sources(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    out = tmp_path / "load.json"
    H.main(["analyse", "--record", SOURCE, "--load", LOAD, "--out", str(out)])
    _same(json.loads(out.read_text()), json.loads(RECORD.read_text()))


_TABLE = json.loads((ROOT / LOAD).read_text())


@pytest.mark.skipif(
    shutil.which("sadf") is None
    or not all((ROOT / s["path"]).exists() for s in _TABLE["sysstat"]),
    reason="the host's sysstat files (local_data/sysstat) are absent",
)
def test_the_load_table_regenerates_from_the_hosts_sysstat_files(tmp_path, monkeypatch):  # fmt: skip
    monkeypatch.chdir(ROOT)
    for s in _TABLE["sysstat"]:
        assert hashlib.sha256(Path(s["path"]).read_bytes()).hexdigest() == s["sha256"]
    out = tmp_path / "cycles.json"
    paths = [s["path"] for s in _TABLE["sysstat"]]
    H.main(["cycles", "--record", SOURCE, "--sysstat", *paths, "--out", str(out)])
    _same(json.loads(out.read_text()), _TABLE)


def test_the_load_table_covers_the_record_but_10_17_and_midnight():
    rows = json.loads((ROOT / SOURCE).read_text())["rows"]
    got = {c["start"] for c in _TABLE["cycles"]} | set(_TABLE["uncovered"])
    assert got == {r["start"] for r in rows}
    late = [s for s in _TABLE["uncovered"] if not s.startswith("2026-10-17")]
    assert all(s[11:13] == "23" for s in late), late


def _ts(s):
    return (dt.datetime.fromisoformat(s) - dt.datetime(1970, 1, 1)).total_seconds()


def test_sadf_output_is_read_by_its_header():
    text = "\n".join([
        "# hostname;interval;timestamp;CPU;%user;%nice;%system;%iowait;%steal;%idle",
        "host;600;2026-10-20 00:10:01;-1;33.28;1.50;2.91;0.05;1.21;61.05",
        "host;600;2026-10-20 00:10:01;0;33.28;1.50;2.91;0.05;1.21;61.05",
        "host;-1;2026-10-20 00:15:00;LINUX-RESTART",
        "",
    ])  # fmt: skip
    assert H.parse_sadf(text) == [(_ts("2026-10-20 00:10:01"), 600, 1.5, 61.05)]


def test_a_cycles_load_is_weighted_by_time_and_needs_its_span_covered():
    t0 = "2026-10-20T10:00:00"
    table = [
        (_ts(t0) + 600, 600, 10.0, 50.0),
        (_ts(t0) + 1200, 600, 0.0, 70.0),
    ]  # [t0, t0+600) at idle 50, [t0+600, t0+1200) at idle 70
    # 300 s at idle 50, then 600 s at idle 70, then 90 s unsampled
    got = H.cycle_load("2026-10-20T10:05:00", table)
    assert got["busy"] == pytest.approx(100 - (300 * 50 + 600 * 70) / 900)
    assert got["nice"] == pytest.approx(300 * 10 / 900)
    assert H.cycle_load("2026-10-20T10:10:00", table) is None  # 600 of 990 s covered


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="time.tzset is POSIX only")
def test_load_matching_does_not_use_the_runners_daylight_saving_transition(monkeypatch):
    """Both inputs are the source host's wall clock, including on a runner whose clocks changed on October 25."""
    text = "\n".join([
        "# hostname;interval;timestamp;CPU;%nice;%idle",
        "host;600;2026-10-25 02:05:00;-1;10;50",
        "host;600;2026-10-25 02:15:00;-1;0;70",
    ])  # fmt: skip
    got = []
    try:
        for tz in ("UTC0", "GMT0BST,M3.5.0/1,M10.5.0"):
            monkeypatch.setenv("TZ", tz)
            time.tzset()
            got.append(H.cycle_load("2026-10-25T01:55:00", H.parse_sadf(text)))
    finally:
        monkeypatch.undo()
        time.tzset()
    assert got[0] == got[1]
    assert got[0]["busy"] == pytest.approx((600 * 50 + 390 * 30) / 990)
    assert got[0]["nice"] == pytest.approx(600 * 10 / 990)


def test_input_hashes_describe_the_bytes_actually_parsed(tmp_path, monkeypatch):
    source, load, out = (
        tmp_path / name for name in ("source.json", "load.json", "out.json")
    )
    original = {
        source: b'{"marker": "source before"}',
        load: b'{"marker": "load before"}',
    }
    for path, raw in original.items():
        path.write_bytes(raw)
    read_bytes = Path.read_bytes

    def rewritten_after_read(path):
        raw = read_bytes(path)
        if path in original:
            path.write_text('{"marker": "after"}')
        return raw

    def analyse_markers(record, table):
        return {"parsed_source": record["marker"], "parsed_load": table["marker"]}

    monkeypatch.setattr(Path, "read_bytes", rewritten_after_read)
    monkeypatch.setattr(H, "analyse", analyse_markers)
    H.main(["analyse", "--record", str(source), "--load", str(load), "--out", str(out)])
    result = json.loads(out.read_text())
    assert result["source"]["sha256"] == hashlib.sha256(original[source]).hexdigest()
    assert result["load"]["sha256"] == hashlib.sha256(original[load]).hexdigest()
    assert result["parsed_source"] == "source before"
    assert result["parsed_load"] == "load before"


def _rows(rng, direct=0.0, other=0.0, n=40):
    """Five tweaks; within each, busy costs 6 steps a point, and AUC rises 0.0008 per 100 fewer steps. `direct` adds
    AUC per point of busy beside the steps; `other` adds AUC per step of a step spread load does not cause."""
    rows, load = [], {"cycles": []}
    for k, level in enumerate((900, 1100, 1250, 1300, 1400)):
        for j in range(n):
            busy, u = rng.normal(0, 10), rng.normal(0, 50)
            steps = level - 6 * busy + u
            start = (dt.datetime(2026, 10, 18) + dt.timedelta(minutes=3 * (k * n + j))).isoformat()  # fmt: skip
            auc = 0.58 + 0.02 * k - 0.0008 * (steps - level) / 100 + direct * busy + other * u  # fmt: skip
            rows.append({"start": start, "tweak": f"t{k}", "epoch": "e", "steps": steps,
                         "roc_auc": auc + rng.normal(0, 0.0003), "val_f1": 0.266 + rng.normal(0, 0.002),
                         "ap_lift": 1.1 + rng.normal(0, 0.01)})  # fmt: skip
            load["cycles"].append({"start": start, "tweak": f"t{k}", "busy": 50 + busy, "nice": rng.uniform(0, 5)})  # fmt: skip
    return {"rows": rows}, load


def test_the_instrument_reads_loads_part_of_the_steps_and_the_check_beside_it_has_power():  # fmt: skip
    rng = np.random.default_rng(0)
    clean = H.analyse(*_rows(rng, n=100), bootstraps=20)  # first stage SE about 0.22
    assert clean["first_stage"]["steps_per_busy_point"] == pytest.approx(-6, abs=0.8)
    auc = clean["measures"]["roc_auc"]
    assert auc["instrumented"] == pytest.approx(-0.0008, abs=0.0002)
    assert abs(auc["beside"]["per_busy_point"]) < 3 * auc["beside"]["per_busy_point_se"]
    # A spread of the steps that load does not cause, and that moves AUC by itself, bends the plain fit only.
    confounded = H.analyse(*_rows(rng, other=-0.00006, n=200), bootstraps=20)["measures"]["roc_auc"]  # fmt: skip
    # The instrumented slope's SE is about 0.00016 here.
    assert confounded["instrumented"] == pytest.approx(-0.0008, abs=0.0005)
    assert confounded["per_100_steps"] < -0.0025  # about -0.0033 expected
    # Load acting beside its steps is seen.
    direct = H.analyse(*_rows(rng, direct=0.0002), bootstraps=20)["measures"]["roc_auc"]  # fmt: skip
    assert direct["beside"]["per_busy_point"] == pytest.approx(0.0002, abs=0.00005)
    assert (
        direct["beside"]["per_busy_point"] > 4 * direct["beside"]["per_busy_point_se"]
    )


def test_the_analysis_refuses_the_window_and_a_load_table_from_another_record():
    record, load = json.loads((ROOT / SOURCE).read_text()), _TABLE
    late = dict(record["rows"][0], start=H.ltr.REGISTERED["since"])
    with pytest.raises(SystemExit, match="window"):
        H.analyse({"rows": [*record["rows"], late]}, load, bootstraps=1)
    other = {"cycles": [dict(load["cycles"][0], tweak="not_it"), *load["cycles"][1:]]}
    with pytest.raises(SystemExit, match="tweak"):
        H.analyse(record, other, bootstraps=1)


@pytest.mark.parametrize("standing_count", [8, 10])
def test_the_window_is_cut_at_the_8th_standing_cycle_and_counts_side_jobs(
    standing_count,
):
    rows, cycles = [], []
    for j in range(6 * standing_count):
        standing = j % 6 == 2
        start = (dt.datetime(2026, 10, 26) + dt.timedelta(minutes=17 * j)).isoformat()
        rows.append({"start": start, "epoch": "139c6873", "tweak": STANDING if standing else f"t{j % 4}"})  # fmt: skip
        side = j in (2, 8, 13)  # two standing cycles and one other
        cycles.append({"start": start, "tweak": rows[-1]["tweak"], "busy": 70.0 if side else 50.0 + (5 if standing else 0),  # fmt: skip
                       "nice": 25.0 if side else 1.0})  # fmt: skip
    cut = [j for j, r in enumerate(rows) if r["tweak"] == STANDING][7]
    for c in cycles[cut + 1 :]:  # what the verdict drops must not count
        c["nice"], c["busy"] = 99.0, 99.0
    got = H.window({"rows": rows}, {"cycles": cycles})
    assert got["cycles"] == cut + 1 and got["without_load"] == 0
    assert got["standing_with_side_job"] == [2, 8]
    assert got["others_with_side_job"] == [1, cut + 1 - 8]
    assert sum(v[0] for v in got["by_tweak"].values()) == 3
    others = [c["busy"] for c in cycles[: cut + 1] if c["tweak"] != STANDING]
    mine = [c["busy"] for c in cycles[: cut + 1] if c["tweak"] == STANDING]
    assert got["busy_gap"]["mean"] == pytest.approx(np.mean(mine) - np.mean(others))


def test_batchgeneratorsv2_augments_inside_the_training_step_not_in_the_loader():
    """The report's correction to #250: every call of apply_augmentations is in train() or its helpers, none in a
    dataset class, and train() moves the batch to the device before it augments it."""
    src = (ROOT / "scripts/training/train.py").read_text()
    tree = ast.parse(src)
    callers = set()
    for node in tree.body:
        for sub in ast.walk(node):
            if isinstance(sub, ast.Call) and getattr(sub.func, "id", None) == "apply_augmentations":  # fmt: skip
                callers.add((type(node).__name__, node.name))
    assert callers == {("FunctionDef", n) for n in ("train", "uamt_views", "preflight_smoke")}  # fmt: skip
    train = next(n for n in tree.body if getattr(n, "name", None) == "train")
    body = ast.get_source_segment(src, train)
    assert body.index("x_raw = x_raw.to(device)") < body.index("= apply_augmentations(")
    old = "loses steps because its augmentation starves the CPU-bound loader"
    assert old not in (ROOT / "reports/loop_steps_vs_ranking_2026-10-26.md").read_text()
    assert "starves" not in (ROOT / "scripts/loop_steps_vs_ranking.py").read_text()


def _s(x, places):
    s = f"{x:+.{places}f}"
    return f"{0:.{places}f}" if float(s) == 0 else s.replace("-", "−")


NAMES = {"val_f1": "val_f1", "roc_auc": "ROC AUC", "ap_lift": "AP prevalence lift"}


def test_the_report_is_the_record(record):
    flat = " ".join(REPORT.read_text().split())
    for m, v in record["measures"].items():
        k = 4 if m == "ap_lift" else 5
        g, d = v["instrumented_groups95"], v["instrumented_days95"]
        cells = [_s(v["per_100_steps"], k), _s(v["instrumented"], k), f"{_s(g[0], k)} to {_s(g[1], k)}",
                 f"{_s(d[0], k)} to {_s(d[1], k)}", _s(v["left_by_load"], k)]  # fmt: skip
        assert f"| {NAMES[m]} | {' | '.join(cells)} |" in flat, m
        b = v["beside"]
        lo, hi = b["per_busy_sd95"]
        cells = [f"{_s(b['per_busy_sd'], k)} ({_s(lo, k)} to {_s(hi, k)})", _s(b["through_steps_per_busy_sd"], k)]  # fmt: skip
        assert f"| {NAMES[m]} | {' | '.join(cells)} |" in flat, m
    f = record["first_stage"]
    assert f"each point of busy costs {-f['steps_per_busy_point']:.1f} steps (SE {f['se']:.2f}; F {f['F']:.0f})" in flat  # fmt: skip
    assert (
        f"busy alone explains {100 * f['within_r2']:.0f}% of the steps' spread" in flat
    )
    wn = f["with_nice"]
    assert f"nice 0 costs {-wn['busy']:.1f} steps and a point at nice 19 about {-(wn['busy'] + wn['nice']):.1f}" in flat  # fmt: skip
    assert (
        f"Of the {record['cycles']} cycles, {record['with_load']} have a load" in flat
    )
    assert f"{record['deviations']} cycles in {record['groups']} groups over {record['days']} days" in flat  # fmt: skip
    assert f"(SD of the steps {record['steps_sd']:.0f}, of busy {record['busy_sd']:.1f} points)" in flat  # fmt: skip
    assert f"({record['bootstraps']:,} times)" in flat
    st = record["standing"]
    assert (
        f"−{-st['busy_gap']['mean']:.1f} points (SE {st['busy_gap']['se']:.1f})" in flat
    )
    uamt = st["busy_gap_by_other_step_costs"]["use_uamt_False"]
    assert f"+{uamt['mean']:.1f} points busier (SE {uamt['se']:.1f})" in flat
    assert (
        st["busy_gap"]["mean"] + 2.1 * st["busy_gap"]["se"]
        < uamt["mean"] - 2.1 * uamt["se"]
    )


def test_the_reports_cross_record_figures():
    flat = " ".join(REPORT.read_text().split())
    rows = json.loads((ROOT / SOURCE).read_text())["rows"]
    uamt = H.svr.step_gap(rows, standing="use_uamt_False", leave_out=())
    assert f"trains about {round(uamt, -2):,.0f} more steps" in flat
    early = [s for s in _TABLE["uncovered"] if s.startswith("2026-10-17")]
    assert f"the {len(early)} on 10-17" in flat
    assert f"and {len(_TABLE['uncovered']) - len(early)} span 23:50 to 00:00" in flat
    svr = json.loads(
        (ROOT / "reports/loop_steps_vs_ranking_2026-10-26.json").read_text()
    )
    sub = json.loads(RECORD.read_text())["measures"]["roc_auc"]["per_100_steps"]
    assert (
        f"against {_s(sub, 5)}; #250's 454 cycles gave {_s(svr['measures']['roc_auc']['per_100_steps'], 5)})"
        in flat
    )
    assert svr["deviations"] == 454
