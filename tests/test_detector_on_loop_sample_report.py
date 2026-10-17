"""Finding 88's report quotes numbers; each must come from its saved artifact."""

import hashlib
import json
import os
import statistics
import subprocess
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = (REPO / "reports" / "detector_on_loop_sample.md").read_text()
A = json.loads((REPO / "reports" / "detector_on_loop_sample.json").read_text())
B = json.loads((REPO / "reports" / "detector_random_window_control.json").read_text())
C_PATH = REPO / "reports" / "detector_on_full_v2_sample.json"
C = json.loads(C_PATH.read_text()) if C_PATH.exists() else None
D_PATH = REPO / "reports" / "loop_candidate_spread.json"
D = json.loads(D_PATH.read_text()) if D_PATH.exists() else None
TOLERANCE = 0.03  # train.F1_NOISE_TOLERANCE when finding 88 ran (0.01 from 2026-10-17)
# The last commit holding the first runs of A, C and D, which read the detector
# before validation's jitter (corrected 2026-10-14, 9acb865a).
FIRST_RUN = "f592a25b"


def _signed(x):
    return f"{x:+.4f}".replace("-", "−")


def _row(label, data, key, bold_auc=False):
    c = data["cards"][key]
    margin = data["margins_over_all_ink"][key]
    auc = f"**{c['roc_auc']:.4f}**" if bold_auc else f"{c['roc_auc']:.4f}"
    margin_text = "0" if key == "constant_all_ink" else f"**{_signed(margin)}**"
    return (
        f"| {label} | {c['val_f1']:.4f} | {margin_text} | {auc} | "
        f"{c['ap_prevalence_lift']:.4f} |"
    )


def _tweak(row):
    diff = row["config_diff"]
    return ", ".join(f"{k}={v}" for k, v in sorted(diff.items()) if k != "depth_band")


def _candidate_row(row):
    a, c = row["cards"]["A"], row["cards"]["C"]
    m = row["margin_over_incumbent"]
    return (
        f"| `{row['snapshot'][10:25]}` | {_tweak(row)} | {a['val_f1']:.4f} | {_signed(m['A'])} | "
        f"{c['val_f1']:.4f} | {_signed(m['C'])} | {c['best_threshold']:.2f} | "
        f"{c['pred_positive_rate']:.2f} | {'yes' if row['would_promote_under_C'] else 'no'} |"
    )


def _d_quoted():
    rows, sep = D["rows"], D["separation"]
    labels = {"val_f1": "val_f1", "roc_auc": "ROC AUC", "ap_prevalence_lift": "AP lift"}
    quoted = {}
    for metric, label in labels.items():
        for p in "AC":
            s = sep[metric][p]
            r = f"**{s['ratio']:.2f}**" if metric == "val_f1" else f"{s['ratio']:.2f}"
            quoted[f"D {metric} {p}"] = (
                f"| {label} | {p} | {s['gap']:.4f} | {s['spread']:.4f} | {r} |"
            )
    ra, rc = sep["val_f1"]["A"]["ratio"], sep["val_f1"]["C"]["ratio"]
    dev = max(abs(r["cards"]["A"]["val_f1"] - r["stored_val_f1"]) for r in rows)
    m = {p: [r["margin_over_incumbent"][p] for r in rows] for p in "AC"}
    share = [r["cards"]["C"]["pred_positive_rate"] for r in rows]
    auc = [r["cards"]["C"]["roc_auc"] for r in rows]
    inc_c = D["incumbent"]["C"]
    quoted |= {
        "D commit": f"`{D['git_commit'][:8]}`",
        "D count": f"The first **{D['candidates']}** snapshots",
        "D names": f"(`{rows[0]['snapshot'][:-3]}` to `{rows[-1]['snapshot'][:-3]}`, none excluded)",
        "D rule": f"{rc:.2f} ≥ 2 × {ra:.2f} = {2 * ra:.2f}",
        "D reproduces": f"within {dev:.1e}".replace("e-0", "e-"),
        "D no promotion": f"Their margins run from {_signed(min(m['C']))} to {_signed(max(m['C']))}",
        "D above C": f"All {len(rows)} score above the incumbent under C** "
        f"(mean {_signed(statistics.mean(m['C']))})",
        "D above A": f"under A, {sum(x > 0 for x in m['A'])} of {len(rows)} do "
        f"(mean {_signed(statistics.mean(m['A']))})",
        "D share": f"calls {min(share) * 100:.0f}–{max(share) * 100:.0f}% of pixels ink",
        "D incumbent share": f"The incumbent's is {inc_c['best_threshold']:.2f}, and it calls "
        f"{inc_c['pred_positive_rate'] * 100:.0f}%",
        "D auc": f"ROC AUC {min(auc):.2f}–{max(auc):.2f} under C",
        "D tolerance": f"{TOLERANCE / sep['val_f1']['A']['spread']:.1f} times the candidates' "
        f"val_f1 spread under A and {TOLERANCE / sep['val_f1']['C']['spread']:.1f} times it under C",
        "D meaning": f"the val_f1 gap is {rc:.2f} SDs on the 400-patch draw against {ra:.2f}",
        "D ranking comparable": f"({sep['roc_auc']['A']['ratio']:.2f} against "
        f"{sep['roc_auc']['C']['ratio']:.2f}, and {sep['ap_prevalence_lift']['A']['ratio']:.2f} "
        f"against {sep['ap_prevalence_lift']['C']['ratio']:.2f})",
        "D option 1": f"margin gaps equal val_f1 gaps: {ra:.2f} SDs",
        "D option 2": f"AP lift separates them too ({sep['ap_prevalence_lift']['C']['ratio']:.2f})",
        "D option 3": f"separates them about as well: {sep['ap_prevalence_lift']['A']['ratio']:.2f} "
        f"and {sep['roc_auc']['A']['ratio']:.2f} SDs",
    }
    for row in rows:
        quoted[f"D row {row['snapshot']}"] = _candidate_row(row)
    return quoted


def _quoted():
    inc = A["cards"]["loop_incumbent"]["val_f1"]
    bar = inc + TOLERANCE
    single = A["margins_over_all_ink"]["detector_single_window"]
    tiled = A["margins_over_all_ink"]["detector_tiled"]
    above = bar - A["all_ink_f1"]
    quoted = {
        "A patches": f"**{A['usable_patches']}** ink-containing patches",
        "A pixels": f"**{A['n_pixels']:,}** pixels",
        "A prevalence": f"**{A['ink_prevalence']:.4f}**",
        "A floor": f"F1 **{A['all_ink_f1']:.4f}**",
        "A incumbent": _row("loop incumbent (`best_model.pt`)", A, "loop_incumbent"),
        "A single": _row(
            "detector, each patch's own 64 px window", A, "detector_single_window"
        ),
        "A tiled": _row("detector, its normal stride-32 tiling", A, "detector_tiled"),
        "A constant": _row("every pixel ink", A, "constant_all_ink"),
        "A primary": f"primary margin is {_signed(A['margins_over_all_ink']['detector_single_window'])}",
        "A tiled text": f"normal inference reaches {_signed(A['margins_over_all_ink']['detector_tiled'])}",
        "A bar": f"beat the incumbent's {inc:.4f} by 0.03, that is, reach {bar:.4f}, which is "
        f"{bar - A['all_ink_f1']:.4f} above",
        "A prevalence pct": f"{A['ink_prevalence'] * 100:.1f}% of whose pixels",
        "B windows": f"**{B['windows']}** random stride-32 windows",
        "B seed": f"(seed {B['seed']}, of **{B['candidate_windows']:,}**; **{B['windows_with_ink']}** contain ink)",
        "B pixels": f"**{B['n_pixels']:,}** pixels, prevalence **{B['ink_prevalence']:.4f}**",
        "B detector": _row(
            "detector, single window", B, "detector_single_window", bold_auc=True
        ),
        "B constant": _row("every pixel ink", B, "constant_all_ink"),
        "B auc text": f"AUC {B['cards']['detector_single_window']['roc_auc']:.4f} against",
        "A commit": f"run at `{A['git_commit'][:8]}`",
        "B commit": f"`{B['git_commit'][:8]}`",
    }
    quoted |= {
        "A bar multiples": f"{above / single:.1f} times the detector's primary margin here, "
        f"and {above / tiled:.1f} times what its tiled inference reaches",
        "A meaning": f"where that detector reaches {_signed(single)} ({_signed(tiled)} tiled)",
    }
    if C is not None:
        mc, ma = C["margins_over_all_ink"], A["margins_over_all_ink"]
        cc, ca = C["cards"], A["cards"]
        quoted |= {
            "C patches": f"all **{C['patches']}** patches",
            "C with ink": f"**{C['patches_with_ink']}** contain ink",
            "C pixels": f"**{C['n_pixels']:,}** pixels, prevalence **{C['ink_prevalence']:.4f}**",
            "C floor": f"all-ink F1\n**{C['all_ink_f1']:.4f}**",
            "C incumbent": _row(
                "loop incumbent (`best_model.pt`)", C, "loop_incumbent"
            ),
            "C detector": _row(
                "detector, each patch's own 64 px window", C, "detector_single_window"
            ),
            "C constant": _row("every pixel ink", C, "constant_all_ink"),
            "C store": f"incumbent would store {cc['loop_incumbent']['val_f1']:.4f}, the bar would be "
            f"{cc['loop_incumbent']['val_f1'] + TOLERANCE:.4f}",
            "C clears": f"({cc['detector_single_window']['val_f1']:.4f}, lift "
            f"{cc['detector_single_window']['ap_prevalence_lift']:.4f})",
            "A gaps": f"separates them by {ma['detector_single_window'] - ma['loop_incumbent']:.4f} "
            f"and AUC by {ca['detector_single_window']['roc_auc'] - ca['loop_incumbent']['roc_auc']:.4f}",
            "C gaps": f"margin separates them by {mc['detector_single_window'] - mc['loop_incumbent']:.4f} "
            f"and AUC by {cc['detector_single_window']['roc_auc'] - cc['loop_incumbent']['roc_auc']:.4f}",
            "C commit": f"`{C['git_commit'][:8]}`",
        }
    if D is not None:
        quoted |= _d_quoted()
    return quoted


def test_the_pre_registered_reading_of_c_holds():
    if C is None:
        pytest.skip("measurement C not saved")
    m = C["margins_over_all_ink"]
    assert m["detector_single_window"] > TOLERANCE >= m["loop_incumbent"]
    assert C["loop_usable_patches"] == C["patches_with_ink"] == A["usable_patches"]


def test_the_pre_registered_reading_of_d_holds():
    if D is None:
        pytest.skip("measurement D not saved")
    rows, sep = D["rows"], D["separation"]["val_f1"]
    assert D["candidates"] == len(rows) == 10
    assert rows[0]["snapshot"] == "candidate_20261013-155821.pt"
    assert [r["snapshot"] for r in rows] == sorted(r["snapshot"] for r in rows)
    assert sep["C"]["ratio"] >= 2 * sep["A"]["ratio"]
    assert D["reading"] == "C separates better; finding 88's recommendation stands"
    assert max(abs(r["cards"]["A"]["val_f1"] - r["stored_val_f1"]) for r in rows) < 1e-3


def test_d_gaps_and_incumbent_are_finding_88s():
    if D is None or C is None:
        pytest.skip("measurements C and D not saved")
    for p, data in (("A", A), ("C", C)):
        cards = data["cards"]
        assert (
            abs(D["incumbent"][p]["val_f1"] - cards["loop_incumbent"]["val_f1"]) < 1e-5
        )
        for metric in ("val_f1", "roc_auc", "ap_prevalence_lift"):
            gap = (
                cards["detector_single_window"][metric]
                - cards["loop_incumbent"][metric]
            )
            assert abs(D["separation"][metric][p]["gap"] - gap) < 1e-9


def test_d_claims_about_the_candidates():
    if D is None:
        pytest.skip("measurement D not saved")
    rows = D["rows"]
    assert not any(r["would_promote_under_C"] for r in rows)
    assert all(r["margin_over_incumbent"]["C"] > 0 for r in rows)
    assert all(r["config_diff"]["depth_band"] == [1, 27] for r in rows)
    assert {r["cards"]["C"]["best_threshold"] for r in rows} == {0.1}
    by_c = sorted(rows, key=lambda r: r["margin_over_incumbent"]["C"])
    assert {r["config_diff"]["lr"] for r in by_c[:2]} == {0.0001}
    assert sum(r["config_diff"]["lr"] == 0.0001 for r in rows) == 2


@pytest.mark.parametrize("name,text", sorted(_quoted().items()))
def test_report_quotes_the_artifacts(name, text):
    flat = " ".join(REPORT.split())
    assert text in REPORT or " ".join(text.split()) in flat, (
        f"{name}: {text!r} not in the report"
    )


def test_all_measurements_used_the_same_checkpoints():
    assert A["detector_sha256"] == B["detector_sha256"]
    if C is not None:
        assert C["detector_sha256"] == A["detector_sha256"]
        assert C["best_model_sha256"] == A["best_model_sha256"]


def _check_stored_incumbent(path):
    import torch

    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != A["best_model_sha256"]:
        pytest.skip(f"{path.name} is no longer the checkpoint finding 88 measured")
    stored = torch.load(path, weights_only=False, map_location="cpu")
    assert A["best_model_val_protocol"] == stored["val_protocol"]
    assert abs(A["cards"]["loop_incumbent"]["val_f1"] - stored["val_f1"]) < 1e-5


def test_the_loop_sample_reproduces_the_stored_incumbent_score():
    _check_stored_incumbent(REPO / "best_model.pt")


def test_a_later_incumbent_skips_rather_than_fails(tmp_path):
    # The loop commits each promotion to best_model.pt, and a protocol change
    # re-scores it; neither makes finding 88's measurement wrong.
    import torch

    later = tmp_path / "best_model.pt"
    torch.save({"val_protocol": A["best_model_val_protocol"], "val_f1": 0.9}, later)
    with pytest.raises(pytest.skip.Exception):
        _check_stored_incumbent(later)


def test_the_ranking_metrics_separate_comparably_on_both_samples():
    # The correction withdraws "ROC AUC and AP lift point the same way": by D's
    # own factor-of-two test, neither sample separates better on them.
    if D is None:
        pytest.skip("measurement D not saved")
    for metric in ("roc_auc", "ap_prevalence_lift"):
        a, c = (D["separation"][metric][p]["ratio"] for p in "AC")
        assert a < 2 * c and c < 2 * a, metric


def _first_run(name):
    """A first-run artifact from git history, or None without it."""
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    shown = subprocess.run(
        ["git", "show", f"{FIRST_RUN}:reports/{name}"],
        cwd=REPO,
        env=env,
        capture_output=True,
        text=True,
    )
    return json.loads(shown.stdout) if shown.returncode == 0 else None


def _correction_column(a, c, d):
    ma, mc = a["margins_over_all_ink"], c["margins_over_all_ink"]
    sep = d["separation"]
    return [
        _signed(ma["detector_single_window"]),
        _signed(ma["detector_tiled"]),
        f"{a['cards']['detector_single_window']['roc_auc']:.4f}",
        _signed(mc["detector_single_window"]),
        f"{c['cards']['detector_single_window']['roc_auc']:.4f}",
        *(
            f"{sep[m]['A']['ratio']:.2f}, {sep[m]['C']['ratio']:.2f}"
            for m in ("val_f1", "roc_auc", "ap_prevalence_lift")
        ),
    ]


def test_the_correction_table_quotes_both_runs():
    if C is None or D is None:
        pytest.skip("measurements C and D not saved")
    names = (
        "detector_on_loop_sample.json",
        "detector_on_full_v2_sample.json",
        "loop_candidate_spread.json",
    )
    first = [_first_run(name) for name in names]
    if None in first:
        pytest.skip(f"the first runs ({FIRST_RUN}) are not in this checkout's history")
    assert first[0]["git_commit"].startswith("b8a8fff3")
    assert first[1]["git_commit"].startswith("c59cfa86")
    assert "separation_git_commit" not in first[2]
    section = REPORT.split("## Correction")[1].split("**All three")[0]
    rows = [
        [cell.strip() for cell in line.split("|")[2:4]]
        for line in section.splitlines()
        if line[:4] in ("| A:", "| C:", "| D:")
    ]
    assert [r[0] for r in rows] == _correction_column(*first)
    assert [r[1] for r in rows] == _correction_column(A, C, D)
    assert A["git_commit"] == C["git_commit"] == D["separation_git_commit"]
