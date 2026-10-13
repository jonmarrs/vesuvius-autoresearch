"""Finding 88's report quotes numbers; each must come from its saved artifact."""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = (REPO / "reports" / "detector_on_loop_sample.md").read_text()
A = json.loads((REPO / "reports" / "detector_on_loop_sample.json").read_text())
B = json.loads((REPO / "reports" / "detector_random_window_control.json").read_text())
C_PATH = REPO / "reports" / "detector_on_full_v2_sample.json"
C = json.loads(C_PATH.read_text()) if C_PATH.exists() else None
TOLERANCE = 0.03  # train.F1_NOISE_TOLERANCE


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


def _quoted():
    inc = A["cards"]["loop_incumbent"]["val_f1"]
    bar = inc + TOLERANCE
    best = max(
        A["margins_over_all_ink"][k]
        for k in ("detector_single_window", "detector_tiled")
    )
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
    assert (bar - A["all_ink_f1"]) / best > 4, "the report says more than four times"
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
    return quoted


def test_the_pre_registered_reading_of_c_holds():
    if C is None:
        pytest.skip("measurement C not saved")
    m = C["margins_over_all_ink"]
    assert m["detector_single_window"] > TOLERANCE >= m["loop_incumbent"]
    assert C["loop_usable_patches"] == C["patches_with_ink"] == A["usable_patches"]


@pytest.mark.parametrize("name,text", sorted(_quoted().items()))
def test_report_quotes_the_artifacts(name, text):
    assert text in REPORT, f"{name}: {text!r} not in the report"


def test_all_measurements_used_the_same_checkpoints():
    assert A["detector_sha256"] == B["detector_sha256"]
    if C is not None:
        assert C["detector_sha256"] == A["detector_sha256"]
        assert C["best_model_sha256"] == A["best_model_sha256"]


def test_the_loop_sample_reproduces_the_stored_incumbent_score():
    import torch

    stored = torch.load(REPO / "best_model.pt", weights_only=False, map_location="cpu")
    assert A["best_model_val_protocol"] == stored["val_protocol"]
    assert abs(A["cards"]["loop_incumbent"]["val_f1"] - stored["val_f1"]) < 1e-5
