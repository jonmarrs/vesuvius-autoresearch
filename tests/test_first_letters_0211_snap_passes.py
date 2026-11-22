"""Finding 134: three snap passes against one at PHerc. 211's prize place. The verdict table, the consequence finding
133 reads, the arms, and the run script."""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load():
    spec = importlib.util.spec_from_file_location(
        "snap_passes_read_under_test", CONTROL / "snap_passes_read.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


sp = _load()


@pytest.mark.parametrize(
    ("r", "expected"),
    [
        ((0.8247, 0.8247, 0.83, 0.85), "SNAP3_READS_BETTER"),  # +0.02 at the 0.02 line
        ((0.8247, 0.8247, 0.83, 0.8499), "SNAP3_READS_SAME"),
        ((0.8247, 0.8247, 0.83, 0.81), "SNAP3_READS_WORSE"),
        (
            (0.8247, 0.8047, 0.83, 0.86),
            "SNAP3_READS_SAME",
        ),  # noise 0.02: the margin is 0.04
        ((0.8247, 0.8047, 0.83, 0.87), "SNAP3_READS_BETTER"),
        ((0.8247, None, 0.83, 0.87), "DOES_NOT_RUN"),
    ],
)
def test_the_verdict_uses_finding_131s_margin(r, expected):
    assert sp.verdict(*r, share=0.83, reproduces=True) == expected


def test_no_verdict_without_finding_124_or_enough_cells():
    assert (
        sp.verdict(0.8247, 0.8247, 0.83, 0.9, 0.83, reproduces=False) == "DOES_NOT_RUN"
    )
    assert sp.verdict(0.8247, 0.8247, 0.83, 0.9, 0.0, reproduces=True) == "DOES_NOT_RUN"


@pytest.mark.parametrize(
    ("verdict", "gain", "expected"),
    [
        ("SNAP3_READS_BETTER", None, "three_passes"),
        ("SNAP3_READS_BETTER", -0.01, "three_passes"),
        ("SNAP3_READS_SAME", 0.03, "three_passes"),
        ("SNAP3_READS_SAME", 0.0, "one_pass"),
        ("SNAP3_READS_SAME", None, "one_pass"),
        ("SNAP3_READS_WORSE", 0.05, "one_pass"),
        ("DOES_NOT_RUN", 0.05, "one_pass"),
    ],
)
def test_finding_133_snaps_three_times_only_if_it_reads_no_worse_and_sits_more_on_the_sheet(
    verdict, gain, expected
):
    assert sp.consequence(verdict, gain) == expected


def test_the_geometry_gain_is_the_median_of_each_windings_change():
    shares = {
        "dense2": {"a": 0.8, "b": 0.7, "c": 0.9},
        "dense2s3": {"a": 0.85, "b": 0.72, "c": 0.9},
    }
    assert sp.geometry_gain(shares) == 0.02
    assert sp.geometry_gain({"dense2": None, "dense2s3": shares["dense2s3"]}) is None
    assert sp.geometry_gain({"dense2": {"a": None}, "dense2s3": {"a": 0.9}}) is None
    assert sp.geometry_gain({"dense2": {"a": 0.8}, "dense2s3": {"b": 0.9}}) is None


def test_the_arms_are_finding_131s_and_this_one(tmp_path):
    base = ["compare", str(tmp_path / "out.json")]
    for flag in (
        "--winner-mesh",
        "--winner-maps",
        "--winner-render",
        "--studio",
        "--studio-mask",
        "--ours-render-map",
    ):
        base += [flag, str(tmp_path)]
    base += ["--windings", "w033"]
    arm = lambda n: ["--arm", n, "f", "r", "m"]  # noqa: E731
    with pytest.raises(SystemExit, match="the arms are"):
        sp.main(base + arm("f124") + arm("rerun") + arm("dense2"))
    (tmp_path / "out.json").write_text("{}")
    assert (
        sp.main(base + arm("f124") + arm("rerun") + arm("dense2") + arm("dense2s3"))
        == 2
    )  # measured once


def test_the_run_snaps_three_times_reads_with_the_winners_command_and_uploads_nothing():
    path = CONTROL / "run_snap_passes.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert 'step snap env FL_SNAP_PASSES=3 bash "$BAND/run_snap.sh" "$ARM"' in text
    assert (
        'ln -sfn fit_e2e_dense2 "$R/work/fit_$ARM"' in text
    )  # finding 131's densified windings
    assert "--stride 64 --blend hann" in text and "--batch-size 32" in text
    for arm in ("f124", "rerun", "dense2", "dense2s3"):
        assert f"--arm {arm} " in text
    assert '"$C/work/snap_passes.json"' in text
    shas = dict(re.findall(r"^(W_SHA|CODE_SHA)=(\w+)", text, flags=re.M))
    f131 = dict(
        re.findall(
            r"^(W_SHA|CODE_SHA)=(\w+)",
            (CONTROL / "run_dense_read.sh").read_text(),
            flags=re.M,
        )
    )
    assert shas == f131 and len(shas) == 2


def test_the_registration_fixes_the_rule_finding_133_reads():
    reg = " ".join(
        (ROOT / "docs/preregistration/2026-11-20_first_letters_0211_snap_passes.md")
        .read_text()
        .split()
    )
    assert (
        "Finding 134" in reg
        and "before any winding has been snapped more than once at PHerc. 211" in reg
    )
    for word in (
        "`SNAP3_READS_BETTER`",
        "`SNAP3_READS_SAME`",
        "`SNAP3_READS_WORSE`",
        "`three_passes`",
        "`one_pass`",
    ):
        assert word in reg
    assert "max(0.02, 2 × |r(rerun) − r(f124)|)" in reg
    controls = (
        ROOT / "repro/first_letters/eligible_band/run_after_controls.sh"
    ).read_text()
    assert (
        '"$CTRL/work/snap_passes.json" consequence' in controls
        and '"$C134" = three_passes' in controls
    )
    record_keys = json.dumps({"consequence": sp.consequence("SNAP3_READS_SAME", 0.01)})
    assert "three_passes" in record_keys
