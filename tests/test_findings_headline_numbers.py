"""FINDINGS.md's headline numbers must match the artifacts they come from, and carry their corrections.

FINDINGS is the document the README sends readers to for "honest results". On 2026-10-22 it still
stated results that later reports had corrected, among them:
- two flattens landing "on surfaces 7.15 vx apart" (corrected 09-22: the same surface, 0.25 vx along the
  normal);
- the anchor study's control "fitted" on another tree (corrected 09-27: the split is at the render);
- the current-code null's ±3% bound (withdrawn 09-27: it rests on three tight control seeds);
- the same-winding null's registered 8.3% bound (the pinned tier's floor gives ~10%);
- the tracer "losing to connected components" (recomputed 10-09: ahead on merge-penalized ERL on 4 of 11);
- the column AUCs at n = 3v2 (superseded by the full band, n = 18v17);
- the loop promoting "topology-improving configurations" (it promotes on val_f1).

Each test here recomputes a figure from the committed JSON, or from the report table where no JSON
holds it, and asserts FINDINGS states it, rounded once from the raw value.
"""

import json
import re
import statistics
from pathlib import Path

from scipy import stats

_REPO = Path(__file__).resolve().parent.parent
_FINDINGS = _REPO / "FINDINGS.md"
_REPORTS = _REPO / "reports"


def _flat(path: Path) -> str:
    # compare on unquoted, single-spaced text so rewrapping is harmless
    lines = (re.sub(r"^> ?", "", line) for line in path.read_text().splitlines())
    return " ".join(" ".join(lines).split())


def _json(rel: str):
    return json.loads((_REPORTS / rel).read_text())


def _pct(x: float, dp: int = 2, minus: str = "−") -> str:
    return f"{x * 100:+.{dp}f}%".replace("-", minus)


def test_the_detector_table_matches_its_measurement():
    text = _FINDINGS.read_text()
    cs = _json("detector/cross_scroll_measurement.json")
    same, cross = cs["PHercParis2Fr143"], cs["20230702185753"]
    rows = [
        ("`val_f1`", "val_f1", 3),
        ("`average_precision`", "average_precision", 3),
        ("`ap_prevalence_lift` (1.0 = chance)", "ap_prevalence_lift", 2),
        ("ROC-AUC (secondary)", "roc_auc", 3),
    ]
    for label, key, dp in rows:
        assert f"| {label} | {same[key]:.{dp}f} | {cross[key]:.{dp}f} |" in text, label

    # the selection caveat: epoch 7 of 12 is the sweep's best, against the last epoch
    sweep = (_REPORTS / "detector/REPRODUCTION.md").read_text()
    auc = {
        int(e): float(a)
        for e, a in re.findall(r"\| \**(\d+)\** \| \**(0\.\d{4})\** \|", sweep)
    }
    assert sorted(auc) == list(range(12)) and max(auc, key=auc.get) == 7
    flat = _flat(_FINDINGS)
    assert (
        f"its checkpoint, epoch 7 of {len(auc)}, was chosen by ROC-AUC on Fr143 itself"
        in flat
    )
    assert (
        f"epoch 7 scored {auc[7]:.4f} and the last epoch, a fixed rule, {auc[max(auc)]:.4f}"
        in flat
    )


def test_the_sota_distillation_matches_its_measurement():
    d = _json("detector/sota_distill_measurement.json")
    s, b = d["distilled_vs_teacher"], d["baseline_vs_teacher"]
    assert (
        f"held-out segment val_f1 **{s['val_f1']:.3f}**, AP **{s['average_precision']:.3f}**, "
        f"lift **{s['ap_prevalence_lift']:.2f}**, ROC-AUC **{s['roc_auc']:.3f}** (baseline = the "
        f"detector above at the chance floor, lift {b['ap_prevalence_lift']:.2f})"
    ) in _flat(_FINDINGS)


def test_the_cross_scroll_note_points_at_the_measurement():
    lift = _json("detector/cross_scroll_measurement.json")["20230702185753"]
    assert (
        f"*(Since measured: the first valid cross-scroll measurement, lift "
        f'{lift["ap_prevalence_lift"]:.2f}, is in "Metric pivot" above.)*'
    ) in _flat(_FINDINGS)


def test_the_anchor_and_current_code_nulls_carry_their_control_sensitivity():
    flat = _flat(_FINDINGS)
    anchor = _json("anchor_ablation_verdict.json")
    ink, geo = anchor["ink"], anchor["geometry"]
    lo, hi = ink["ci"]
    # the ablated arm's CV against the registered control's, as the verdict report rounds them
    # (no JSON keeps the ablated arm's CV)
    cvs = re.search(
        r"CV \*\*([\d.]+)\*\* against \*\*([\d.]+)\*\*",
        (_REPORTS / "anchor_ablation_verdict.md").read_text(),
    ).groups()
    noisier = float(cvs[0]) / float(cvs[1])
    assert (
        f"changes reading by {_pct(ink['rel_diff'])}, p={ink['p']:.2f} — but bounded only at "
        f"[{_pct(lo)}, {_pct(hi)}], because the ablated arm is {noisier:.1f}× noisier than the "
        f"baselines. Its geometry rise ({_pct(geo['rel_diff'])}, p={geo['p']:.4f})"
    ) in flat

    cur = _json("samewinding_current_verdict.json")["ink"]
    assert (
        f"On current code the ink null reproduces ({_pct(cur['rel_diff'])}, p={cur['p']:.2f}, "
        f"95% CI [{_pct(cur['ci'][0], minus='-')}, {_pct(cur['ci'][1])}])"
    ) in flat

    # the corrections: the swap is between two samples of one configuration
    eff = _json("control_sensitivity.json")["effects"]
    reg, matched = "registered s1-s3 (old render)", "render-matched s4-s9"
    an, sw = eff["anchor ablation 59->10"], eff["same-winding ablation (current)"]
    assert an[reg]["rel"] == ink["rel_diff"] and sw[reg]["rel"] == cur["rel_diff"]
    assert (
        f"the ink estimate moves **{_pct(an[reg]['rel'])} → {_pct(an[matched]['rel'])}** "
        "(verdict still NULL)"
    ) in flat
    m = sw[matched]
    assert (
        f"against the six render-matched control seeds it is {_pct(m['rel'])}, 95% CI "
        f"[{_pct(m['lo'])}, {_pct(m['hi'])}], so its ±3% bound is withdrawn"
    ) in flat
    assert "*(Corrected 2026-09-27: the split is at the render, not the fit." in flat
    # the render split's measured effect, against same-code render noise
    rerender = _json("rerender_test_verdict.json")
    render = _json("render_reproducibility.json")["ink"]
    assert rerender["verdict"] == "RENDER CHANGE IS INERT" and rerender["rel"] < render
    assert (
        f"Every current-tier fit ran from one `d8c5f488a` copy, and the render split was measured "
        f"inert, {_pct(rerender['rel'])} inside the {render:.2%} render noise."
    ) in flat

    # the count agreement in the placement study is the registered seeds' CV
    cv = _json("control_sensitivity.json")["control_cv"]
    assert (
        f"agree on `total_fg_pixels` to **{cv[reg]:.1%}** *(the CV of three seeds since found unusually "
        f"tight; across all nine of that configuration it is {cv['all nine s1-s9']:.1%},"
    ) in flat


def test_the_flatten_and_fit_floors_match_their_measurements():
    flat = _flat(_FINDINGS)
    outer = _json("flatten_normal_offset/stock_vs_stock_outer.json")
    render = _json("render_reproducibility.json")["ink"]
    assert (
        f"lay the same surface out on grids **~{outer['in_plane_p50']:.0f} vx** apart in-plane "
        f"({outer['normal_abs_p50']:.2f} vx along the normal; corrected 2026-09-22"
    ) in flat
    assert f"and move the count **{render:.2%}**." in flat

    det = _json("deterministic_flatten_verdict.json")
    rep = (_REPORTS / "the_flatten_is_reproducible_when_asked.md").read_text()
    stock = float(
        re.search(rf"{re.escape(str(det['its']))} it/s vs ~(\d+) stock", rep)[1]
    )
    assert f"**bit-reproducible** at a {stock / det['its']:.1f}× flatten cost" in flat

    d = _json("fit_only_floor.json")
    fits, stock_fits = list(d["det"].values()), list(d["stock"].values())
    cv = statistics.stdev(fits) / statistics.mean(fits)
    stock_cv = statistics.stdev(stock_fits) / statistics.mean(stock_fits)
    n = len(fits) - 1
    ratio = (cv / stock_cv) ** 2
    p = 2 * min(stats.f.sf(ratio, n, n), stats.f.cdf(ratio, n, n))
    assert (
        f"six seeds of one config give a CV of **{cv:.4f} [{d['ci'][0]:.4f}, {d['ci'][1]:.4f}]** "
        f"— statistically indistinguishable from the same six with stock flattens "
        f"(F({n},{n}) p={p:.2f})"
    ) in flat


def test_the_case_table_states_each_study():
    text = _FINDINGS.read_text()
    table = re.search(
        r"^\| case \| `satisfied_area` \| `total_fg_pixels` \| what the guard does \|\n\|[-:| ]+\|\n((?:\|.*\|\n)+)",
        text,
        re.M,
    )[1].splitlines()
    assert len(table) == 4
    assert (
        "We have four pre-registered cases where those two move independently"
        in _flat(_FINDINGS)
    )

    boot, strip = (
        _json("patch_bootstrap_verdict.json"),
        _json("stripmatch_verdict.json"),
    )
    for row, d, name, bold in (
        (table[1], boot, "patch bootstrap", True),
        (table[2], strip, "stripmatch", False),
    ):
        g = f"{d['geometry']['rel_diff'] * 100:+.2f}%"
        assert d["geometry"]["p"] < 1e-4
        assert row.startswith(
            f"| {name}, n=6 | {f'**{g}**' if bold else g} (p<1e-4) | "
            f"{d['ink']['rel_diff'] * 100:.2f}% (p={d['ink']['p']:.2f}, null) |"
        ), row

    # the gap fix: ink 6 v 6, geometry the five-fit test's
    gap = _json("manipulation_effects_survey.json")["gap-expander fix"]
    first = (_REPORTS / "gap_expander_fix_improves_the_fit.md").read_text()
    welch = re.search(r"Welch: \*\*([+-][\d.]+)%\*\* .*?\*\*p = ([\d.e-]+)\*\*", first)
    assert table[0].startswith(
        f"| gap-expander config, 5v6 geometry, 6v6 ink | {float(welch[1]):+.2f}% (p={welch[2]}) | "
        f"**{gap['rel'] * 100:.2f}%** (p={gap['p']:.4f}) |"
    ), table[0]

    sw = _json("samewinding_verdict.json")["ink"]
    geo = re.search(
        r"^\| `satisfied_area_fraction` \| [\d.]+ \| [\d.]+ \| \*\*(-[\d.]+%)\*\* \| \*\*([\d.]+)\*\* \|$",
        (_REPORTS / "samewinding_verdict.md").read_text(),
        re.M,
    ).groups()
    assert table[3].startswith(
        f"| same-winding ablation, 3v6 | **{geo[0]}** (p={geo[1]}) | "
        f"{sw['rel_diff'] * 100:.2f}% (p={sw['p']:.2f}, null) |"
    ), table[3]


def test_each_null_states_its_corrected_bound():
    flat = _flat(_FINDINGS)
    survey = _json("manipulation_effects_survey.json")

    # same-winding (pinned), 3 v 6: the registered df=3 bound against the pinned tier's
    registered = _json("samewinding_verdict.json")["mde"]
    pinned = survey["same-winding ablation (pinned)"]["mde"]
    assert (
        f"leaves recovered ink unchanged within ~{pinned:.0%} ({registered:.1%} as registered; "
        "corrected with the pinned tier's noise floor"
    ) in flat
    assert (
        f"**NULL on reading**, bounded at ~{pinned:.0%}, not zero ({registered:.1%} as registered"
        in _flat(_REPORTS / "SPIRAL_FINDINGS_SUMMARY.md")
    )

    # the two patch studies, 3 v 3
    reg = {
        f"{_json(f)['mde']:.0%}"
        for f in ("patch_bootstrap_verdict.json", "stripmatch_verdict.json")
    }
    cor = {f"{survey[k]['mde']:.0%}" for k in ("patch bootstrap", "stripmatch")}
    assert len(reg) == len(cor) == 1
    assert (
        f"no ink effect larger than ~{reg.pop()} *(corrected 2026-09-12 to ~{cor.pop()}:"
        in flat
    )


def test_the_current_code_gain_matches_its_baselines():
    cur = (_REPORTS / "current_code_baseline.md").read_text()
    current = [
        int(v.replace(",", ""))
        for v in re.findall(r"^\| curbase_s\d \| [\d.]+ \| ([\d,]+) \|", cur, re.M)
    ]
    pinned = _json("samewinding_verdict.json")["ink"]["mean_base"]
    assert len(current) == 3
    gain = statistics.mean(current) / pinned - 1
    assert (
        f"Current villa recovers {gain:.1%} more ink through a byte-identical renderer"
        in _flat(_FINDINGS)
    )


def test_the_loop_is_described_by_its_promotion_rule():
    # read as text: importing train.py pulls in torch
    train = (_REPO / "scripts/training/train.py").read_text()
    lift = float(re.search(r"^LIFT_MARGIN = (.+)$", train, re.M)[1])
    assert re.search(r"^F1_NOISE_TOLERANCE = ", train, re.M)
    assert "return val_f1 > best_val_f1 + F1_NOISE_TOLERANCE" in train
    assert (
        json.loads((_REPO / "config.json").read_text())["enforce_prize_gates"] is False
    )
    flat = _flat(_FINDINGS)
    assert (
        "promotes a configuration only when its `val_f1` beats the incumbent's by more than the "
        f"noise tolerance, with an AP-prevalence lift above {1 + lift:.2f}."
    ) in flat
    assert "promotes only topology-improving configurations" not in flat
    assert (
        "`config.json` records the prize gates without enforcing them (`enforce_prize_gates: false`)"
        in flat
    )


def test_the_tracer_ranking_is_the_rescores():
    cubes = [c for c in _json("tracer_rescore.json")["cubes"].values() if c["ran"]]
    raw = [c["cc_v2"]["erl"] / c["tracer_v2"]["erl"] for c in cubes]
    pen_ahead = [
        c
        for c in cubes
        if c["tracer_v2"]["erl_merge_penalized"] > c["cc_v2"]["erl_merge_penalized"]
    ]
    big = [c for c in cubes if c["size_class"] == 512]
    assert (
        all(r > 1 for r in raw) and len(big) == 3 and all(c in pen_ahead for c in big)
    )
    assert (
        f"raw ERL still trails connected components on all {len(cubes)}, by {min(raw):.1f}–{max(raw):.1f}×, "
        f"but merge-penalized ERL leads on {len(pen_ahead)} of {len(cubes)}, all three "
        "512³ cubes among them."
    ) in _flat(_FINDINGS)


def test_the_column_result_is_the_full_band():
    full = {
        m: _json(f"detector/columns_fullband_{m}.json")["metrics"]
        for m in ("arm_C", "legacy")
    }
    floor = re.search(
        r"^\| \*noise floor \(same n\)\* \| \*([\d.]+)\* \|",
        (_REPORTS / "detector/scrollgt_v02_columns.md").read_text(),
        re.M,
    )[1]
    c = full["arm_C"]
    assert c["n_text_cols"] == full["legacy"]["n_text_cols"]
    assert (
        f"Over the full band, all {len(c['cols_scored'])} columns at n = {c['n_text_cols']} text columns "
        f"against {c['n_gutters']} gutters, arm C scores col-vs-gutter AUC {c['col_gutter_auc']:.3f} and "
        f"the legacy detector {full['legacy']['col_gutter_auc']:.3f}, against a "
        f"noise floor of {floor} at that n"
    ) in _flat(_FINDINGS)


def test_the_window_verdict_is_marked_superseded():
    auc = _json("detector/cross_scroll_measurement.json")["PHercParis2Fr143"]["roc_auc"]
    assert (
        "~~Verdict — detection at 64 px is window-limited: the ink↔CT signal is not a learnable "
        "function of the 64 px patch.~~* **Superseded by Phase 5**, like the TimeSformer bullet above: "
        f"a 64 px-lateral recipe reads real, transferable ink (held-out AUC {auc:.3f})"
    ) in _flat(_FINDINGS)
