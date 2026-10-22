"""The README's headline numbers must match the artifacts they come from.

The README is the front door. Its opening paragraph and its spiral-fitting box quoted 74 numbers from
the detector and spiral reports, and on 2026-10-22 changing any one of them by one in its last digit failed
no test: test_headline_numbers_consistent.py only checks that a README quoting the geometry gains says
"circular". Each test here recomputes a figure from the committed JSON, or from the report table where no
JSON holds it, and asserts the README states it, rounded once from the raw value.
"""

import json
import re
import statistics
from pathlib import Path

from scipy import stats

_REPO = Path(__file__).resolve().parent.parent
_README = _REPO / "README.md"
_REPORTS = _REPO / "reports"


def _flat(path: Path) -> str:
    # the headline is a wrapped blockquote; compare on unquoted, single-spaced text
    lines = (re.sub(r"^> ?", "", line) for line in path.read_text().splitlines())
    return " ".join(" ".join(lines).split())


def _json(rel: str):
    return json.loads((_REPORTS / rel).read_text())


def _report(rel: str) -> str:
    return (_REPORTS / rel).read_text()


def _sig2(x: float) -> str:
    # a ratio quoted to two significant figures: 443.0 -> "440"
    return f"{float(f'{x:.2g}'):.0f}"


def _counts(pattern: str, text: str) -> list[int]:
    return [int(v.replace(",", "")) for v in re.findall(pattern, text, re.M)]


def test_the_detector_rows_match_their_measurements():
    txt = _flat(_README)
    cs = _json("detector/cross_scroll_measurement.json")
    same, cross = cs["PHercParis2Fr143"], cs["20230702185753"]
    assert (
        f"held-out same-scroll `val_f1` {same['val_f1']:.3f} / prevalence-lift "
        f"{same['ap_prevalence_lift']:.2f}, its epoch chosen on that fragment"
    ) in txt
    assert (
        f"(lift {cross['ap_prevalence_lift']:.2f} — the quantified generalization gap)"
        in txt
    )

    sota = _json("detector/sota_distill_measurement.json")["distilled_vs_teacher"]
    assert (
        f"(`val_f1` {sota['val_f1']:.3f} / lift {sota['ap_prevalence_lift']:.2f} *agreement-with-teacher* "
        "on the open SOTA data, the best of 12 epochs on the held-out region"
    ) in txt
    assert "the best of 12 epochs by val_f1 on this region" in _report(
        "detector/sota_distill_measurement.md"
    )


def test_the_cross_scroll_distillation_figures_match():
    txt = _flat(_README)
    held = _json("detector/cross_scroll_distill.json")["on_held_1667"]
    one, two = held["armA"]["ap_prevalence_lift"], held["armB"]["ap_prevalence_lift"]
    assert (
        f"unseen-scroll transfer {one:.2f} → {two:.2f} at fixed budget ({two:.2f} is the best epoch"
        in txt
    )
    three = _json("detector/cross_scroll_scale.json")["on_held_1667"]["armC"][
        "ap_prevalence_lift"
    ]
    assert three < two  # "no measured gain over that selected row"
    assert f"(≈{three:.1f}, the third-scroll model's last epoch" in txt


def test_the_ground_truth_calibration_matches_its_validations():
    txt = _flat(_README)
    canon = "canon teacher (binarized release)"
    first = _json("detector/registered_gt_validation.json")["rows"][canon]
    held = _json("detector/registered_gt_heldout_validation.json")["rows"]
    teacher = held[canon]
    assert (
        f"the canon prediction scores ROC-AUC {first['roc_auc']:.2f}–{teacher['roc_auc']:.2f} "
        f"({first['roc_auc']:.2f} on a segment since retired non-scoring"
    ) in txt

    # arms B and C carry the claim; arm A chose its epoch on this segment
    clean = [held["arm B (2-scroll student)"], held["arm C (3-scroll student)"]]
    auc, lift, f1 = (
        [r[k] for r in clean] for k in ("roc_auc", "ap_prevalence_lift", "f1_at_0.5")
    )
    floor = held["legacy detector"]["roc_auc"]
    assert (
        f"**ROC-AUC {min(auc):.3f}–{max(auc):.3f} / lift {min(lift):.1f}–{max(lift):.1f}** against an "
        f"all-positive floor of {floor:.3f}"
    ) in txt
    assert max(auc) < teacher["roc_auc"]  # "at or just under the canon teacher's"
    assert (
        f"at or just under the canon teacher's {teacher['roc_auc']:.3f} there on ROC-AUC"
        in txt
    )
    assert (
        f"the teacher leads, {teacher['f1_at_0.5']:.3f} vs {min(f1):.2f}–{max(f1):.2f}"
        in txt
    )


def test_the_render_validations_match():
    txt = _flat(_README)
    scroll1 = _json("detector/render_validation.json")["results"]["sign1"]["ncc"]
    v = _json("detector/render_validation_1667.json")
    assert v["verdict"] == "PASS" and "NCC >= 0.6 " in v["gate"]
    assert (
        f"NCC {v['ncc']:.2f} vs pre-registered 0.60; Scroll 1's {scroll1:.2f} confirmed"
        in txt
    )
    assert (
        f"measured Scroll 1 NCC {scroll1:.2f} and PHerc1667 NCC **{v['ncc']:.2f}, gate PASS**"
        in txt
    )


def test_the_column_figures_match_their_rows():
    txt = _flat(_README)
    full = _json("detector/columns_fullband_arm_C.json")["metrics"]
    part = _json("detector/columns_baseline_arm_C.json")["metrics"]
    assert (
        f"the published reading's {len(full['cols_scored'])} columns were registered"
        in txt
    )
    # the noise floor is the report's; no JSON records it
    rep = _report("detector/scrollgt_v02_columns.md")
    noise = re.search(r"^\| \*noise floor \(same n\)\* \| \*([\d.]+)\* \|", rep, re.M)[
        1
    ]
    assert f"| arm C | {full['col_gutter_auc']:.3f} |" in rep
    assert (
        f"arm C col-vs-gutter AUC {full['col_gutter_auc']:.3f} against a noise floor of {noise} on the "
        f"definitive full-band n={full['n_text_cols']}v{full['n_gutters']} rows"
    ) in txt
    assert (
        f"an earlier {part['col_gutter_auc']:.3f} here came from a superseded "
        f"n={part['n_text_cols']}v{part['n_gutters']} extreme"
    ) in txt


def test_the_gap_fix_case_states_each_metric_on_its_own_fits():
    """The geometry figure is the five-fit test's and the ink figure the six-fit one's."""
    txt = _flat(_README)
    table = _report("gap_fix_costs_ink_established.md")
    base = _counts(r"^\| \w+ \| BASE \| [\d.]+ \| ([\d,]+) \|$", table)
    gap = _counts(r"^\| \w+ \| GAP \| [\d.]+ \| ([\d,]+) \|$", table)
    ink = _json("gap_fix_mechanism.json")["ink  total_fg_pixels"]
    assert len(base) == len(gap) == 6
    assert (
        statistics.mean(base) == ink["baseline"]
        and statistics.mean(gap) == ink["gap133"]
    )
    # the report's summary line states the table's mean, not another
    stated = _counts(r"^BASE mean ([\d,]+) ", table)
    assert len(stated) == 1 and abs(stated[0] - ink["baseline"]) <= 0.5

    first = _report("gap_expander_fix_improves_the_fit.md")
    geo = {
        arm: (int(n), float(m))
        for arm, n, m in re.findall(
            r"^> \| (BASE|GAP) \| (\d) \| ([\d.]+) \|", first, re.M
        )
    }
    (n_base, m_base), (n_gap, m_gap) = geo["BASE"], geo["GAP"]
    assert (n_base, n_gap) == (6, 5)
    assert (
        f"improved geometry {m_gap / m_base - 1:+.2%} ({n_gap} fits against {n_base}) while costing "
        f"**{ink['rel']:+.2%} of the ink** ({len(gap)} against {len(base)})"
    ) in txt

    draft = (_REPO / "docs/VILLA_DRAFT_metrics_disagree.md").read_text()
    row = re.search(r"^\| baseline \(n=6\) \| ([\d.]+) \| ([\d,]+) \|$", draft, re.M)
    assert (
        float(row[1]) == m_base
        and abs(int(row[2].replace(",", "")) - ink["baseline"]) <= 0.5
    )
    assert f"| changed (n=6) | {m_gap} (first five) |" in draft

    # the case tables label each metric's fits too
    label = f"| gap-expander config, {n_gap}v{n_base} geometry, {len(gap)}v{len(base)} ink |"
    geo = f"{m_gap / m_base - 1:+.2%}"
    assert f"{label} {geo} (p=3.9e-06) |" in (_REPO / "FINDINGS.md").read_text()
    assert _report("SPIRAL_FINDINGS_SUMMARY.md").count(f"{label} {geo} |") == 2


def test_the_other_decoupling_cases_match_their_sources():
    txt = _flat(_README)
    boot = _json("patch_bootstrap_verdict.json")["geometry"]["rel_diff"]
    strip = _json("stripmatch_verdict.json")["geometry"]["rel_diff"]
    assert (
        f"raised geometry **{boot:+.2%} and {strip:+.2%} for no ink gain at all**"
        in txt
    )
    # their ink nulls are bounded by the pinned tier's floor, not the registered df=3 one
    survey = _json("manipulation_effects_survey.json")
    bounds = {f"{survey[k]['mde']:.0%}" for k in ("patch bootstrap", "stripmatch")}
    assert len(bounds) == 1
    assert f"both ink nulls are bounded at ~{bounds.pop()}, not zero" in txt

    # the ablation's geometry endpoint is in its report's table only
    rep = _report("samewinding_verdict.md")
    removed = re.search(r"^# Removing ([\d,]+) same-winding constraints", rep)[1]
    row = re.search(
        r"^\| `satisfied_area_fraction` \| ([\d.]+) \| ([\d.]+) \| \*\*(-[\d.]+)%\*\* \| \*\*([\d.]+)\*\* \|$",
        rep,
        re.M,
    )
    base, ablated, rel, p = float(row[1]), float(row[2]), float(row[3]) / 100, row[4]
    # the quoted change is from unrounded means; it must overlap what the four-place ones allow
    half = 0.00005
    assert (ablated - half) / (base + half) - 1 <= rel + half
    assert rel - half <= (ablated + half) / (base - half) - 1
    assert (
        f"an ablation of **{removed} winding constraints** that measurably *degraded* the geometry "
        f"({rel:.2%}, p={p})"
    ) in txt


def test_the_current_code_gain_matches_its_baselines():
    txt = _flat(_README)
    cur = _report("current_code_baseline.md")
    current = _counts(r"^\| curbase_s\d \| [\d.]+ \| ([\d,]+) \|", cur)
    pinned = _json("samewinding_verdict.json")["ink"][
        "mean_base"
    ]  # the six pinned baselines
    assert (
        len(current) == 3
        and pinned
        == _json("gap_fix_mechanism.json")["ink  total_fg_pixels"]["baseline"]
    )
    gain = statistics.mean(current) / pinned - 1
    assert f"**+{gain:.1%} on the objective." in cur
    assert (
        f"current villa recovers {gain:.1%} more ink through a byte-identical scorer"
        in txt
    )


def test_the_flatten_figures_match_their_measurements():
    txt = _flat(_README)
    outer = _json("flatten_normal_offset/stock_vs_stock_outer.json")
    assert (
        f"offset ~{outer['in_plane_p50']:.0f} voxels in-plane ({outer['normal_abs_p50']:.2f} vx apart along "
        "the normal"
    ) in txt
    render = _json("render_reproducibility.json")["ink"]
    assert f"move `total_fg_pixels` **{render:.2%}**." in txt

    det = _json("deterministic_flatten_verdict.json")
    rep = _report("the_flatten_is_reproducible_when_asked.md")
    row = re.search(
        rf"\| {det['its']} it/s vs ~(\d+) stock — \*\*([\d.]+)× slower\*\* \|", rep
    )
    stock = float(row[1])
    assert row[2] == f"{stock / det['its']:.1f}"
    walls = [
        int(s)
        for s in re.search(
            r"wall time per flatten \(incl\. export\) \| (\d+) s, (\d+) s", rep
        ).groups()
    ]
    assert det["mean_nn"] == 0.0  # bit-reproducible
    assert (
        f"at a {stock / det['its']:.1f}× flatten cost, ~{statistics.mean(walls) / 60:.0f} min against 2 h renders"
    ) in txt

    fixed = _json("flat_displacement_floor.json")
    pixels = abs(fixed["rad0"] - fixed["zero"])
    assert fixed["F"] == pixels / fixed["rad0"]
    assert f"from {render:.2%} to **{fixed['F']:.4%}** — {pixels} pixels" in txt

    moved = _json("flat_displacement_verdict.json")
    inward, outward = (f"{moved[k]:.2%}".replace("-", "−") for k in ("in", "out"))
    assert (
        f"costs ink in **both** directions, {inward} inward and {outward} outward"
        in txt
    )


def test_the_fit_only_floor_matches_its_fits():
    txt = _flat(_README)
    d = _json("fit_only_floor.json")
    det, stock = list(d["det"].values()), list(d["stock"].values())
    cv = statistics.stdev(det) / statistics.mean(det)
    stock_cv = statistics.stdev(stock) / statistics.mean(stock)
    assert abs(cv - d["cv"]) < 1e-12 and len(det) == len(stock) == 6
    df = len(det) - 1
    ratio = (cv / stock_cv) ** 2
    p = 2 * min(stats.f.sf(ratio, df, df), stats.f.cdf(ratio, df, df))
    lo, hi = d["ci"]
    assert (
        f"six seeds re-flattened deterministically give a CV of **{cv:.2f} [{lo:.2f}, {hi:.2f}]**, "
        f"statistically indistinguishable from stock (F({df},{df}) p={p:.2f})"
    ) in txt


def test_the_scorer_floor_ratios_divide_the_figures_they_name():
    """0.0032% is ~440× under the 1.42% floor and 950× under the 3.04% render spread."""
    header = (_REPO / "repro/spiral_render/score_arms.sh").read_text()
    runs = [
        int(v)
        for v in re.search(r"total_fg_pixels (\d+) / (\d+) / (\d+)", header).groups()
    ]
    scorer = (max(runs) - min(runs)) / statistics.mean(runs)
    pairs = _report("the_determinism_floor_rests_on_one_draw.md")
    floor_pair = _counts(
        r"^\| (?:original \(`render_lasagna`\)|repeat \(`dup_armREPEAT`\)) \| ([\d,]+) \|$",
        pairs,
    )
    second_pair = _counts(
        r"^\| `(?:seedarm_04|probe_innerprob)` \| ([\d,]+) \|$", pairs
    )
    floor = abs(floor_pair[1] - floor_pair[0]) / floor_pair[0]
    second = abs(second_pair[1] - second_pair[0]) / second_pair[0]
    render = _json("render_reproducibility.json")["ink"]
    vs_floor, vs_render, tighter = (
        _sig2(floor / scorer),
        _sig2(render / scorer),
        _sig2(floor / second),
    )

    readme = _flat(_README)
    assert f'"pipeline is deterministic to {floor:.1%}" floor' in readme
    assert (
        f"the scorer it blamed contributes **{scorer:.4%}**, ~{vs_floor}× too little"
        in readme
    )

    summary = _flat(_REPORTS / "SPIRAL_FINDINGS_SUMMARY.md")
    assert f"same-mesh pair agreed to four pixels — {tighter}× tighter" in summary
    assert (
        f"moves a fixed strip by {scorer:.4%}, ~{vs_floor}× too small to produce {floor:.2%}."
        in summary
    )

    pairs = _flat(_REPORTS / "the_determinism_floor_rests_on_one_draw.md")
    assert f"measured twice, {tighter}× apart" in pairs
    assert f"**The two measurements differ by {tighter}×.**" in pairs
    assert f"the scorer is {vs_render}× too small to be responsible" in pairs
    assert f"**{tighter}× tighter**" in _flat(
        _REPORTS / "pipeline_determinism_and_which_floor_applies.md"
    )
    assert (
        f"The scorer is **~{vs_floor}× too small** to produce {floor:.2%}, and {vs_render}× smaller than the "
        f"{render:.2%} render spread."
    ) in _flat(_REPORTS / "the_render_is_the_noise_floor.md")
    assert f"the scorer is ~{vs_floor}× too small" in _flat(
        _REPORTS / "the_radial_study_design_is_invalid.md"
    )
    villa = _flat(_REPO / "docs/VILLA_PR_CANDIDATE_flatten_nondeterminism.md")
    assert (
        f"**{render:+.2%}**" in villa
        and f"**{scorer:.4%}** — ~{vs_render}× too little" in villa
    )


def test_the_seed_noise_history_ends_at_the_current_floor():
    txt = _flat(_README)
    current = _json("noise_floor_by_tier.json")["current"]
    assert (
        "the seed-noise figure was published too low twice: 0.0125, withdrawn when a third arm moved it to "
        "0.0263, inside the interval that had never been printed, and 0.0263, withdrawn when six fits already "
        f"on disk doubled it to {current['cv']:.4f}."
    ) in txt
    summary = _flat(_REPORTS / "SPIRAL_FINDINGS_SUMMARY.md")
    assert (
        "**0.0263 (df=6)** — first published as 0.0125 (df=4) and withdrawn when a third arm"
        in summary
    )
    assert (
        f"current-tier CV goes **0.0263 → {current['cv']:.4f}** (df={current['df']})"
        in summary
    )
