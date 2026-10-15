"""Finding 90's report quotes numbers; each must come from its saved artifact."""

import json
import statistics
from pathlib import Path

import pytest

from scripts.loop_model_depth_offset import reading

REPO = Path(__file__).resolve().parents[1]
REPORT = (REPO / "reports" / "loop_model_depth_offset.md").read_text()
DATA = json.loads((REPO / "reports" / "loop_model_depth_offset.json").read_text())
SAMPLE_C = json.loads(
    (REPO / "reports" / "detector_on_full_v2_sample.json").read_text()
)


def _signed(value):
    return f"{value:+.4f}".replace("-", "−")


def _quoted():
    cards, deltas = DATA["cards"], DATA["auc_delta_deep_minus_shallow"]
    candidates = DATA["candidates"]
    quoted = {
        "patches": f"**{DATA['patches']}** patches, **{DATA['patches_with_ink']}**",
        "commit": DATA["git_commit"][:8],
        "incumbent": DATA["best_model_sha256"][:8],
        "incumbent delta": f"delta(incumbent) = **{_signed(deltas['incumbent'])}**",
        "mean delta": f"**{_signed(statistics.mean(deltas[c] for c in candidates))}** "
        f"(SD {statistics.stdev(deltas[c] for c in candidates):.4f})",
        "all-ink F1": f"all-ink F1 of {SAMPLE_C['all_ink_f1']:.4f}",
    }
    for z0 in [str(z) for z in range(8)] + ["natural"]:
        every, ink = cards["incumbent"][z0]["all"], cards["incumbent"][z0]["ink"]
        bold = "**" if z0 in ("0", "7") else ""  # the two starts the rule compares
        quoted[f"incumbent z0={z0}"] = (
            f"{every['roc_auc']:.4f}{bold} | {every['ap_prevalence_lift']:.4f} | "
            f"{every['val_f1']:.4f} | {ink['roc_auc']:.4f} |"
        )
    for name in candidates:
        short = name.removeprefix("candidate_20261013-").removesuffix(".pt")
        quoted[f"candidate {short}"] = (
            f"| {short} | {cards[name]['0']['all']['roc_auc']:.4f} | "
            f"{cards[name]['7']['all']['roc_auc']:.4f} | {_signed(deltas[name])} |"
        )
    return quoted


@pytest.mark.parametrize("name,text", sorted(_quoted().items()))
def test_report_quotes_the_artifact(name, text):
    assert text in REPORT, f"{name}: {text!r} not in the report"


def test_the_reading_follows_from_the_deltas():
    deltas = DATA["auc_delta_deep_minus_shallow"]
    expected = reading(deltas["incumbent"], [deltas[c] for c in DATA["candidates"]])
    assert DATA["reading"] == expected
    assert expected == "no dependence on the window's position"
    assert "no dependence on the window's position" in " ".join(REPORT.split())


def test_the_unregistered_counts():
    """9 of 10 candidate deltas negative (8 of 10 on ink-containing patches), and
    every fixed start above the patches' own starts, as the report says."""
    cands = DATA["candidates"]
    deltas, ink = DATA["auc_delta_deep_minus_shallow"], DATA["auc_delta_ink_patches"]
    assert sum(deltas[c] < 0 for c in cands) == 9 and deltas["incumbent"] < 0
    assert sum(ink[c] < 0 for c in cands) == 8
    inc = DATA["cards"]["incumbent"]
    fixed = [inc[str(z)]["all"]["roc_auc"] for z in range(8)]
    assert inc["natural"]["all"]["roc_auc"] < min(fixed)
    assert min(fixed) == inc["7"]["all"]["roc_auc"]  # z0 = 7 is the lowest start
    assert f"({min(fixed):.4f} to {max(fixed):.4f})" in REPORT
    spreads = [
        statistics.stdev(DATA["cards"][c][z]["all"]["roc_auc"] for c in cands)
        for z in ("0", "7")
    ]
    assert f"SD {spreads[0]:.4f} at z0 = 0, {spreads[1]:.4f} at z0 = 7" in REPORT


def test_the_prose_quotes_the_artifact():
    inc = DATA["cards"]["incumbent"]
    every = [inc[str(z)]["all"] for z in range(8)]
    ink = [inc[str(z)]["ink"]["roc_auc"] for z in range(8)]
    f1 = [card["val_f1"] for card in every]
    for text in (
        f"reads {every[0]['roc_auc']:.4f} from the shallowest window and "
        f"{every[7]['roc_auc']:.4f} from the deepest",
        f"pooled AUC is {inc['natural']['all']['roc_auc']:.4f}",
        f"{inc['natural']['ink']['roc_auc']:.4f} against {min(ink):.4f} to {max(ink):.4f}",
        f"{min(f1):.4f} to {max(f1):.4f} at every start",
    ):
        assert text in " ".join(REPORT.split()), text
