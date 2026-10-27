"""The audit of the registered confirmation's join (scripts/loop_confirmation_audit.py), its record and its report."""

import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INC = 0.265762


def _load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


A = _load("loop_confirmation_audit")
ltr = A.ltr


def _run(kind, n, tweak, f1, auc=0.58, steps=900):
    return [
        f"--- {kind} SHIFT CYCLE {n}: {tweak} ---",
        "--- PREFLIGHT SMOKE CHECK ---",
        "Starting Gated UNet-Transformer Loop (Budget: 900s)...",
        "Step 0000 | Loss: 0.4 | LR: 0.00e+00 | dt: 600ms | Remaining: 899s",
        f"Step {steps:04d} | Loss: 0.4 | LR: 1.00e-05 | dt: 600ms | Remaining: 1s",
        f"val_f1: {f1} (thr 0.5; incumbent {INC})",
        f"roc_auc: {auc}",
        "ap_prevalence_lift: 1.2",
        "avg_mean_ap: 0.3",
    ]


def _logs(tmp_path, window, before=(), after=()):
    """A night-shift sprint log of the window's cycles (tweak, val_f1, auc), from 2026-10-25 19:10:02, 17 minutes
    apart; run.log.old holds `before` runs (kind, n, tweak, val_f1, auc) and run.log the window's, then `after`."""
    lines = ["# Night Shift Sprint - 2026-10-25", "- **Start Time**: 19:10:02", ""]
    old, new = [], []
    for kind, n, tweak, f1, auc in before:
        old += _run(kind, n, tweak, f1, auc)
    for n, (tweak, f1, auc) in enumerate(window, 1):
        minute = 10 + 17 * n
        lines += [
            f"## Cycle {n}: {tweak} (REVERTED)",
            f"- **Timestamp**: {19 + minute // 60:02d}:{minute % 60:02d}:02",
            "- **Config**: batch_size: 8, time_budget: 900",
            f"- **Stats**: val_f1: {f1}, loss: 0.5",
            "",
        ]
        new += _run("NIGHT", n, tweak, f1, auc)
    for kind, n, tweak, f1, auc in after:
        new += _run(kind, n, tweak, f1, auc)
    (tmp_path / "sprint_logs").mkdir()
    (tmp_path / "sprint_logs/sprint_log_2026-10-25_19-10-02_night_shift.md").write_text(
        "\n".join(lines) + "\n"
    )
    (tmp_path / "run.log.old").write_text("\n".join(old) + "\n")
    (tmp_path / "run.log").write_text("\n".join(new) + "\n")
    rows, tally = ltr.cycles(
        [str(tmp_path / "sprint_logs/sprint_log_2026-10-2*.md")],
        [str(tmp_path / "run.log.old"), str(tmp_path / "run.log")],
        "2026-10-25T16:00:00", "2026-10-29T16:00:00", INC, stop_at_promotion=True,
    )  # fmt: skip
    return {"incumbent": INC, "tally": tally, "rows": rows}


def _audit(tmp_path, confirmation):
    logs = [str(tmp_path / "run.log.old"), str(tmp_path / "run.log")]
    numbers = A.numbered_cycles(
        [str(tmp_path / "sprint_logs/sprint_log_2026-10-2*.md")]
    )
    return A.audit(confirmation, A.headed_runs(logs), numbers)


def test_the_headed_runs_are_the_registered_runs_with_their_headers(tmp_path):
    _logs(
        tmp_path,
        [("a", 0.2661, 0.58), ("b", 0.2662, 0.59)],
        before=[("DAY", 13, "c", 0.2661, 0.50)],
    )
    logs = [str(tmp_path / "run.log.old"), str(tmp_path / "run.log")]
    got = A.headed_runs(logs)
    assert {k: [rec for rec, _ in v] for k, v in got.items()} == ltr.runs(logs)
    assert [h for _, h in got[0.2661]] == [("DAY", 13, "c"), ("NIGHT", 1, "a")]


def test_a_value_that_recurs_before_the_window_is_given_the_run_its_header_names(
    tmp_path,
):
    """The registered join leaves cycle 1 unmatched: its value has two runs (one before the window) and one claim."""
    conf = _logs(
        tmp_path,
        [("a", 0.2661, 0.58), ("b", 0.2662, 0.59)],
        before=[("DAY", 13, "c", 0.2661, 0.50)],
    )
    assert conf["tally"]["unmatched"] == 1 and "roc_auc" not in conf["rows"][0]
    got = _audit(tmp_path, conf)
    assert got["registered_matches"] == {"checked": 1, "header_agrees": 1}
    (entry,) = got["unmatched"]
    assert entry["resolved"] and entry["sprint_log"] == ["NIGHT", 1, "a"]
    assert entry["candidates"] == [["DAY", 13, "c"], ["NIGHT", 1, "a"]]
    assert got["rows"][0]["roc_auc"] == 0.58 and got["still_unmatched"] == 0


def test_a_value_whose_runs_both_carry_the_cycles_header_stays_unmatched(tmp_path):
    conf = _logs(
        tmp_path, [("a", 0.2661, 0.58)], before=[("NIGHT", 1, "a", 0.2661, 0.50)]
    )
    got = _audit(tmp_path, conf)
    assert not got["unmatched"][0]["resolved"] and got["still_unmatched"] == 1
    assert "roc_auc" not in got["rows"][0]


def test_a_run_after_the_window_with_the_cycles_value_and_another_header_does_not_take_it(
    tmp_path,
):
    conf = _logs(
        tmp_path, [("a", 0.2661, 0.58)], after=[("NIGHT", 2, "b", 0.2661, 0.50)]
    )
    assert conf["tally"]["unmatched"] == 1
    got = _audit(tmp_path, conf)
    assert got["unmatched"][0]["resolved"] and got["rows"][0]["roc_auc"] == 0.58


def test_a_registered_match_to_another_cycles_run_is_flagged(tmp_path):
    """Cycle 1's own run is missing and one run before the window has its value: the counts agree, so the registered
    join takes that run. Its header names another cycle."""
    conf = _logs(
        tmp_path,
        [("a", 0.2661, 0.58), ("b", 0.2662, 0.59)],
        before=[("DAY", 13, "c", 0.2663, 0.50)],
    )
    text = (
        (tmp_path / "run.log").read_text().replace("val_f1: 0.2661 ", "val_f1: 0.2663 ")
    )
    (tmp_path / "run.log").write_text(text)
    (tmp_path / "run.log.old").write_text(
        (tmp_path / "run.log.old").read_text().replace("0.2663", "0.2661")
    )
    conf = {"incumbent": INC, **dict(zip(("rows", "tally"), ltr.cycles(
        [str(tmp_path / "sprint_logs/sprint_log_2026-10-2*.md")],
        [str(tmp_path / "run.log.old"), str(tmp_path / "run.log")],
        "2026-10-25T16:00:00", "2026-10-29T16:00:00", INC, stop_at_promotion=True,
    ), strict=True))}  # fmt: skip
    assert conf["tally"]["unmatched"] == 0 and conf["rows"][0]["roc_auc"] == 0.50
    got = _audit(tmp_path, conf)
    assert got["registered_matches"] == {"checked": 2, "header_agrees": 1}
    assert got["disagreeing"] == [
        {"start": conf["rows"][0]["start"], "tweak": "a", "run": ["DAY", 13, "c"]}
    ]


# The readout's records (reports/loop_confirmation_readout_2026-10-27.md)

RR = _load("loop_replicate_rule")
H = _load("loop_host_load")
SNAP = ROOT / "local_data/loop_logs/readout_2026-10-27"
CONF = "reports/loop_tweak_confirmation_2026-10-27.json"
FIXED = "reports/loop_tweak_confirmation_corrected_2026-10-27.json"
AUDIT = "reports/loop_confirmation_audit_2026-10-27.json"
STEPS = "reports/loop_steps_vs_ranking_2026-10-26.json"
RULE, RULE_FIXED = (
    f"reports/loop_replicate_rule_window{s}_2026-10-27.json" for s in ("", "_corrected")
)
CYCLES, WINDOW = (
    "reports/loop_host_load_window_cycles_2026-10-27.json",
    "reports/loop_host_load_window_2026-10-27.json",
)
REPORT = ROOT / "reports/loop_confirmation_readout_2026-10-27.md"
CANDIDATE = (
    ROOT / "local_data/loop_candidates/window_2026-10-25/candidate_20261026-184935.pt"
)
STANDING = "aug_mode_batchgeneratorsv2"


def _json(path):
    return json.loads((ROOT / path).read_text())


def _same(a, b):
    """Equal, but for the last bits of floats, which BLAS and runtime versions can change (#251)."""
    assert type(a) is type(b)
    if isinstance(a, dict):
        assert a.keys() == b.keys()
        for k in a:
            _same(a[k], b[k])
    elif isinstance(a, list):
        assert len(a) == len(b)
        for x, y in zip(a, b, strict=True):
            _same(x, y)
    elif isinstance(a, float):
        assert a == pytest.approx(b, rel=1e-12, abs=1e-14)
    else:
        assert a == b


def _copied_inputs_intact():
    sums = SNAP / "SHA256SUMS"
    if not sums.exists():
        return False
    for line in sums.read_text().splitlines():
        digest, name = line.split(maxsplit=1)
        assert hashlib.sha256((SNAP / name).read_bytes()).hexdigest() == digest, name
    return True


@pytest.mark.skipif(
    not (SNAP / "SHA256SUMS").exists(), reason="the readout's copied logs are absent"
)
def test_the_registered_output_and_the_audit_regenerate_from_the_copied_inputs(
    tmp_path, monkeypatch
):
    assert _copied_inputs_intact()
    monkeypatch.chdir(SNAP)
    out = tmp_path / "conf.json"
    ltr.main(["--registered", "--since", "2026-10-25T16:00:00", "--until", "2026-10-27T05:19:55",
              "--sprint-logs", "sprint_logs/sprint_log_2026-10-2*.md", "--run-log", "run.log.old", "run.log",
              "--out", str(out)])  # fmt: skip
    _same(json.loads(out.read_text()), _json(CONF))
    monkeypatch.chdir(ROOT)
    a, c = tmp_path / "audit.json", tmp_path / "fixed.json"
    A.main(["--confirmation", CONF, "--logs", str(SNAP.relative_to(ROOT)), "--steps", STEPS,
            "--out", str(a), "--corrected", str(c)])  # fmt: skip
    _same(json.loads(a.read_text()), _json(AUDIT))
    _same(json.loads(c.read_text()), _json(FIXED))


def test_the_replicate_rule_records_regenerate(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    for conf, record in ((CONF, RULE), (FIXED, RULE_FIXED)):
        RR.main(["--window", conf, "--out", str(tmp_path / "rule.json")])
        _same(json.loads((tmp_path / "rule.json").read_text()), _json(record))


@pytest.mark.skipif(
    not all((ROOT / s["path"]).exists() for s in _json(CYCLES)["sysstat"]),
    reason="the host's sysstat files (local_data/sysstat) are absent",
)
def test_the_window_load_regenerates(tmp_path, monkeypatch):
    monkeypatch.chdir(ROOT)
    paths = [s["path"] for s in _json(CYCLES)["sysstat"]]
    H.main(
        [
            "cycles",
            "--record",
            CONF,
            "--sysstat",
            *paths,
            "--out",
            str(tmp_path / "c.json"),
        ]
    )
    _same(json.loads((tmp_path / "c.json").read_text()), _json(CYCLES))
    H.main(
        [
            "window",
            "--confirmation",
            CONF,
            "--load",
            CYCLES,
            "--out",
            str(tmp_path / "w.json"),
        ]
    )
    _same(json.loads((tmp_path / "w.json").read_text()), _json(WINDOW))


def test_the_corrected_confirmation_is_the_registered_one_with_the_audited_runs():
    reg, fixed, audit = _json(CONF), _json(FIXED), _json(AUDIT)
    assert (
        reg["verdict"]["status"] == "UNMATCHED_RUNS"
        and reg["verdict"]["reading"] is None
    )
    resolved = {u["start"] for u in audit["unmatched"] if u["resolved"]}
    assert (
        len(resolved) == reg["tally"]["unmatched"] == 7
        and audit["still_unmatched"] == 0
    )
    for r, f in zip(reg["rows"], fixed["rows"], strict=True):
        assert (
            f == r
            if r["start"] not in resolved
            else {k: f[k] for k in r} == r and "roc_auc" in f
        )
    assert {k: fixed[k] for k in fixed if k not in ("rows", "tally", "effects", "standing", "verdict", "corrected")} == {
        k: reg[k] for k in reg if k not in ("rows", "tally", "effects", "standing", "verdict")}  # fmt: skip
    assert (
        fixed["verdict"]
        == audit["corrected"]["verdict"]
        == ltr.registered_verdict(fixed["rows"], fixed["tally"], fixed["incumbent"])
    )
    assert fixed["verdict"]["reading"] == "CONFIRMED"


@pytest.mark.skipif(
    not CANDIDATE.exists(), reason="the loop's candidate snapshots are absent"
)
def test_the_kept_candidate_is_the_rules_cycle():
    raw = CANDIDATE.read_bytes()
    meta = _load("loop_incumbent_reference").checkpoint_metadata(raw)
    first = _json(RULE_FIXED)["first_promotion"]
    row = next(r for r in _json(FIXED)["rows"] if r["start"] == first["start"])
    assert meta["metrics"]["val_f1"] == row["val_f1"] and row["tweak"] == STANDING
    assert f"`{meta['sha256'][:16]}…`" in REPORT.read_text()


def _quiet_rows():
    load = {c["start"]: c for c in _json(CYCLES)["cycles"]}
    return [
        r
        for r in _json(FIXED)["rows"]
        if r["start"] in load and load[r["start"]]["nice"] < H.SIDE_JOB_NICE
    ]


def test_the_report_is_the_records():
    text = " ".join(REPORT.read_text().split())
    reg, fixed, audit, rule = _json(CONF), _json(FIXED), _json(AUDIT), _json(RULE_FIXED)
    win, steps = _json(WINDOW), _json(STEPS)

    def has(*parts):
        for p in parts:
            assert p in text, p

    has(
        f"{reg['tally']['unmatched']} of the {reg['tally']['cycles']} cycles unmatched",
        "UNMATCHED_RUNS | none",
    )
    has(
        f"All {audit['registered_matches']['header_agrees']} of the registered join's matches pass"
    )
    assert (
        audit["registered_matches"]["checked"]
        == audit["registered_matches"]["header_agrees"]
    )
    for u in audit["unmatched"]:
        shift, n, tweak = u["sprint_log"]
        other = next(c for c in u["candidates"] if c != u["sprint_log"])
        has(f"| {u['start'][5:10]} {u['start'][11:]} | {tweak} | {shift} {n}, {tweak} | {other[0]} {other[1]}, {other[2]} |")  # fmt: skip
    e = {m: fixed["effects"][m][STANDING] for m in ("val_f1", "roc_auc", "ap_lift")}
    has(f"+{e['val_f1']['mean_diff']:.5f} (t {e['val_f1']['t']:.2f})", f"+{e['roc_auc']['mean_diff']:.4f} (t {e['roc_auc']['t']:.2f})",
        f"+{e['ap_lift']['mean_diff']:.4f} (t {e['ap_lift']['t']:.2f})")  # fmt: skip
    s = fixed["standing"]
    has(f"0 of 8 (best {s['val_f1_max']:.5f})", "clears 0.275762")
    assert s["cleared_bar"] == 0 and fixed["verdict"]["bar"] == pytest.approx(0.275762)
    ep = s["per_epoch"]["139c6873"]
    has(f"val_f1 {ep['val_f1_mean']:.5f} against {ep['val_f1_others']:.5f}", f"the {ep['n_others']} others",
        f"ROC AUC {ep['roc_auc_mean']:.4f} against {ep['roc_auc_others']:.4f}")  # fmt: skip
    ranked = {m: sorted((v["mean_diff"] for k, v in fixed["effects"][m].items() if k != STANDING), reverse=True)[0] for m in ("val_f1", "roc_auc")}  # fmt: skip
    assert ranked["val_f1"] < 0.0026 and ranked["roc_auc"] < 0.0059
    has("It is the only tweak above +0.0026 in val_f1 or +0.0059 in AUC")
    first, cyc = (
        rule["first_promotion"],
        {c["tweak_cycles_so_far"]: c for c in rule["standing_cycles"]},
    )
    has("TAKES_CONFIRMED_GAIN", f"at its {first['tweak_cycles_so_far']}th window cycle", f"score {first['score']:.2f}: t {cyc[6]['t_val_f1']:.2f} on val_f1, {cyc[6]['t_roc_auc']:.2f}",
        f"{cyc[7]['score']:.2f} at the 7th cycle and {cyc[8]['score']:.2f} at the 8th",
        f"{rule['null']['false_promotions']} of 1,000 shuffles ({rule['null']['centred_false_promotions']} of 1,000 centred)")  # fmt: skip
    assert first["tweak"] == STANDING and first["start"] == "2026-10-26T18:33:16"
    # the 7 dropped instead
    rows = [r for r in reg["rows"] if "threshold" in r]
    tally = dict(reg["tally"], unmatched=0)
    v = ltr.registered_verdict(rows, tally, reg["incumbent"])
    drop = RR.window_test(dict(reg, rows=rows, tally=tally, verdict=v), permutations=2)
    has(f"| the 7 dropped instead ({v['n_others']} others) | +{v['effects']['val_f1']:.5f} | +{v['effects']['roc_auc']:.4f} | +{v['effects']['ap_lift']:.4f} | {v['reading']} | 6th cycle, score {drop['first_promotion']['score']:.2f} |")  # fmt: skip
    assert drop["first_promotion"]["tweak_cycles_so_far"] == 6
    quiet = _quiet_rows()
    q = {m: ltr.effects(quiet, m)[STANDING] for m in ("val_f1", "roc_auc", "ap_lift")}
    has(f"({len(quiet)} cycles, {q['val_f1']['n']} standing) | +{q['val_f1']['mean_diff']:.5f} | +{q['roc_auc']['mean_diff']:.4f} | +{q['ap_lift']['mean_diff']:.4f}")  # fmt: skip
    cov = _json(CYCLES)
    has(
        f"covers {len(cov['cycles'])} of the {reg['tally']['cycles']} cycles ({len(cov['uncovered'])} span"
    )
    has(f"−{-win['busy_gap']['mean']:.1f} points of busy (SE {win['busy_gap']['se']:.1f}), −{-win['nice_gap']['mean']:.1f} of %nice (SE {win['nice_gap']['se']:.1f})",
        f"overlapped {win['standing_with_side_job'][0]} of its {win['standing_with_side_job'][1]} cycles",
        f"and {win['others_with_side_job'][0]} of the other {win['others_with_side_job'][1]}")  # fmt: skip
    adj = audit["corrected"]["steps"]
    has(f"{-adj['step_gap']:.0f} fewer steps", f"before the window ({-steps['standing']['step_gap']:.0f})",
        f"+{adj['roc_auc']['from_its_steps']:.4f} of its +{adj['roc_auc']['effect']:.4f} AUC effect ({adj['roc_auc']['from_its_steps'] / adj['roc_auc']['effect']:.0%})",
        f"+{adj['ap_lift']['from_its_steps']:.3f} of its +{adj['ap_lift']['effect']:.3f} AP lift ({adj['ap_lift']['from_its_steps'] / adj['ap_lift']['effect']:.0%})",
        f"({adj['val_f1']['from_its_steps'] / adj['val_f1']['effect']:.0%})",
        f"+{adj['roc_auc']['beyond_its_steps']:.4f} AUC and +{adj['ap_lift']['beyond_its_steps']:.3f} AP lift")  # fmt: skip
    has(f"median is {s['steps_median']:.0f} against {s['steps_median_others']:,}")
