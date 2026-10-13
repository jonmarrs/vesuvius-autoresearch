"""Finding 86's report quotes numbers; each must come from its saved artifact."""

import json
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[1]
REPORT = (REPO / "reports" / "loop_v2_constant_control.md").read_text()
DATA = json.loads((REPO / "reports" / "loop_v2_constant_control.json").read_text())
FALLBACK = "Lasagna flattening failed for"


def _floor(p):
    return 2 * p / (1 + p)


def _quoted():
    model, const, perm, stored = (
        DATA["model"],
        DATA["constant_all_ink"],
        DATA["model_probs_permuted"],
        DATA["stored"],
    )
    v2_floor = DATA["all_ink_f1_formula"]
    v1_floor = _floor(stored["val_positive_rate"])
    gate = model["val_f1"] + 0.03  # train.F1_NOISE_TOLERANCE
    return {
        "usable patches": f"**{DATA['usable_patches']}** of {DATA['requested_patches']}",
        "pixels": f"**{DATA['n_pixels']:,}**",
        "prevalence": f"**{DATA['ink_prevalence']:.4f}**",
        "model F1": f"**{model['val_f1']:.4f}**",
        "all-ink F1": f"**{const['val_f1']:.4f}**",
        "floor formula": f"{v2_floor:.4f}",
        "permuted F1": f"{perm['val_f1']:.4f}",
        "model lift": f"**{model['ap_prevalence_lift']:.4f}**",
        "model AUC": f"**{model['roc_auc']:.4f}**",
        "permuted lift": f"{perm['ap_prevalence_lift']:.4f}",
        "permuted AUC": f"{perm['roc_auc']:.4f}",
        "predicted ink": f"{model['pred_positive_rate']:.4f}",
        "v2 margin": f"**{model['val_f1'] - v2_floor:+.4f}**".replace("-", "−"),
        "below floor": f"**{v2_floor - model['val_f1']:.4f} below**",
        "jump": f"+{model['val_f1'] - stored['val_f1']:.3f}",
        "v1 F1": f"{stored['val_f1']:.4f}",
        "v1 prevalence": f"{stored['val_positive_rate']:.4f}",
        "v1 floor": f"{v1_floor:.4f}",
        "v1 margin": f"**{stored['val_f1'] - v1_floor:+.4f}**",
        "v1 AUC": f"{stored['roc_auc']:.4f}",
        "v1 lift": f"{stored['ap_prevalence_lift']:.4f}",
        "gate": f"above {gate:.4f}",
        "gate over floor": f"{gate - v2_floor:.4f} above the all-ink floor",
        "checkpoint": DATA["checkpoint_sha256"][:16],
        "commit": DATA["git_commit"][:8],
    }


@pytest.mark.parametrize("name,text", sorted(_quoted().items()))
def test_report_quotes_the_artifact(name, text):
    assert text in REPORT, f"{name}: {text!r} not in the report"


@pytest.mark.parametrize(
    "log,count",
    [("run.log.old", 980), ("run.log", 2185)],
)
def test_report_quotes_the_logged_fallback_counts(log, count):
    path = REPO / log
    if not path.exists():
        pytest.skip(f"{log} is not in this checkout")
    assert path.read_text(errors="replace").count(FALLBACK) == count
    assert f"**{count:,}**" in REPORT
