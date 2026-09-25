"""Upstream-fitter rule: tested before any upstream arm was fitted."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from analyse_upstream_fitter import (  # noqa: E402
    BASELINE,
    RENDER_TREE,
    UPSTREAM,
    decide,
    read_arm,
)

IMG = "sha256:1f3a"


def _arm(ink, sha=RENDER_TREE, img=IMG, det="1", fit_tree=None):
    return {"ink": ink, "villa_sha": sha, "image_id": img,
            "flatten_deterministic": det, "fit_tree": fit_tree}  # fmt: skip


def _arms(base_ink, up_ink, **over):
    arms = {a: _arm(v) for a, v in zip(BASELINE, base_ink, strict=False)}
    arms.update(
        {
            a: _arm(v, fit_tree="75c79ac5f")
            for a, v in zip(UPSTREAM, up_ink, strict=False)
        }
    )
    for a, kw in over.items():
        arms[a] = {**arms[a], **kw}
    return arms


BASE = [3.16e6, 2.96e6, 3.58e6, 3.02e6, 2.84e6, 2.85e6]


def test_partial_sample_is_refused():
    arms = _arms(BASE, [3.0e6, 3.1e6, 2.9e6])
    del arms["detfit_up3"]
    with pytest.raises(ValueError, match="partial"):
        decide(arms)


@pytest.mark.parametrize(
    "over",
    [
        {"detfit_up1": {"villa_sha": "75c79ac5f"}},  # rendered on the wrong tree
        {"detfit_s4": {"image_id": "sha256:other"}},  # a different sampler
        {"detfit_up2": {"flatten_deterministic": "0"}},  # stochastic flatten
        {"detfit_up3": {"fit_tree": None}},  # provenance of the fit unknown
        {"detfit_up1": {"fit_tree": "be09a8503"}},  # fitted on the old tree
    ],
)
def test_a_failed_gate_withholds_the_verdict(over):
    res = decide(_arms(BASE, [4.0e6, 4.1e6, 4.2e6], **over))
    assert res["verdict"] == "INVALID"
    assert "relative_ci" not in res and res["failed_gates"]


def test_a_large_rise_is_detected():
    res = decide(_arms(BASE, [4.9e6, 5.0e6, 5.1e6]))
    assert res["verdict"] == "FITTER CHANGED READING (+)"
    assert res["relative_ci"]["lo"] > 0


def test_a_large_fall_is_detected():
    res = decide(_arms(BASE, [2.0e6, 2.1e6, 2.05e6]))
    assert res["verdict"] == "FITTER CHANGED READING (-)"


def test_a_change_inside_the_noise_is_not_called():
    res = decide(_arms(BASE, [3.0e6, 3.2e6, 3.1e6]))
    assert res["verdict"] == "NO DETECTED CHANGE"
    c = res["relative_ci"]
    assert c["lo"] < 0 < c["hi"]


def test_read_arm_parses_a_real_work_dir_layout(tmp_path):
    w = tmp_path / "detfit_up1"
    (w / "ink_metric").mkdir(parents=True)
    (w / "ink_metric" / "metrics.json").write_text(
        '{"summary": {"total_fg_pixels": 123}}'
    )
    (w / "VILLA_SHA").write_text(RENDER_TREE + "\n")
    (w / "RENDER_IMAGE").write_text(
        "image=vc-render:local\nimage_id=sha256:1f3a\nflatten_deterministic=1\n"
    )
    (w / "FIT_TREE").write_text("75c79ac5f\n")
    r = read_arm(w)
    assert r == {"ink": 123.0, "villa_sha": RENDER_TREE, "image_id": "sha256:1f3a",
                 "flatten_deterministic": "1", "fit_tree": "75c79ac5f"}  # fmt: skip


def test_the_real_baseline_arms_pass_the_render_gates():
    """The six baselines already exist: they must satisfy the same render gates
    the new arms will be held to, or the comparison is broken before it starts."""
    root = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
    if not (root / "detfit_s4").exists():
        pytest.skip("spiral_out not present")
    rows = [read_arm(root / a) for a in BASELINE]
    assert {r["villa_sha"] for r in rows} == {RENDER_TREE}
    assert {r["flatten_deterministic"] for r in rows} == {"1"}
    assert len({r["image_id"] for r in rows}) == 1
