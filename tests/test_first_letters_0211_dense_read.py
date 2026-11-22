"""Finding 131: the denser snap's reading at the winning PHerc. 211 place. The verdict table, the arms, the script."""

import importlib.util
import os
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"
REG = ROOT / "docs/preregistration/2026-11-20_first_letters_0211_dense_read.md"


def _load():
    spec = importlib.util.spec_from_file_location(
        "dense_read_under_test", CONTROL / "dense_read.py"
    )
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


dr = _load()


@pytest.mark.parametrize(
    ("f124", "rerun", "dense", "expected"),
    [
        (
            0.8247,
            0.8247,
            0.8447,
            "DENSE_READS_BETTER",
        ),  # +0.02 with no noise: the 0.02 floor
        (0.8247, 0.8247, 0.8446, "DENSE_READS_SAME"),
        (0.8247, 0.8247, 0.8047, "DENSE_READS_WORSE"),
        (0.8247, 0.8147, 0.8346, "DENSE_READS_SAME"),  # noise 0.01: the margin is 0.02
        (
            0.8247,
            0.8047,
            0.8446,
            "DENSE_READS_SAME",
        ),  # noise 0.02: the margin is 0.04, the change 0.0399
        (0.8247, 0.8047, 0.8448, "DENSE_READS_BETTER"),
        (
            0.8247,
            0.8447,
            0.8048,
            "DENSE_READS_SAME",
        ),  # noise +0.02 counts as much as -0.02
        (0.8247, 0.8447, 0.8047, "DENSE_READS_WORSE"),  # exactly at the margin counts
    ],
)
def test_the_verdict_table(f124, rerun, dense, expected):
    assert dr.verdict(f124, rerun, dense, 0.83, True) == expected


@pytest.mark.parametrize(
    ("share", "reproduces", "dense"),
    [(0.49, True, 0.9), (0.83, False, 0.9), (0.83, True, None), (None, True, 0.9)],
)
def test_it_does_not_run_without_half_the_mask_finding_124_again_or_every_r(
    share, reproduces, dense
):
    assert dr.verdict(0.8247, 0.8247, dense, share, reproduces) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    assert (dr.LINE, dr.F124_R, dr.NEAR) == (0.02, 0.8247, 2.0)
    text = " ".join(REG.read_text().split())
    assert "the larger of 0.02 and 2 × |noise|" in text
    assert "does not give r 0.8247" in text
    for name in (
        "DENSE_READS_BETTER",
        "DENSE_READS_WORSE",
        "DENSE_READS_SAME",
        "DOES_NOT_RUN",
    ):
        assert f"`{name}`" in text


def test_the_arms_must_be_named_as_registered(tmp_path):
    base = ["compare", str(tmp_path / "o.json")]
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
    arms = []
    for name in ("f124", "rerun", "other"):
        arms += ["--arm", name, str(tmp_path), str(tmp_path), str(tmp_path)]
    with pytest.raises(SystemExit):
        dr.main(base + arms)
    assert not (tmp_path / "o.json").exists()


def test_the_run_reads_both_arms_as_finding_124_did_and_uploads_nothing():
    path = CONTROL / "run_dense_read.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync "):
        assert word not in text
    assert (
        "ARMS=(e2e_rerun e2e_dense2)" in text
        and "WINDINGS=(w033 w034 w035 w036)" in text
    )
    assert '"$BAND/densify_winding.py" "$base/$w" "$dest/$w" --factor 2' in text
    assert 'ln -sfn fit_full "$R/work/fit_e2e_rerun"' in text
    assert (
        "RENDER_SLICES" not in text
    )  # 66 layers: finding 124's validity mask reads all of them
    assert text.count("--stride 64 --blend hann") == 1 and "--batch-size 32" in text
    assert '"$HERE/end_to_end.py" orient' in text
    assert (
        '--arm f124 "$R/work/final_e2e" "$R/work/render_e2e" "$C/work/studio_e2e/maps"'
        in text
    )
    order = [text.index(f'step {s}') for s in ("check", "prepare", '"snap_', '"flatten_', '"orient_', '"render_',
                                                '"studio_', "compare")]  # fmt: skip
    assert order == sorted(order)
    shas = dict(re.findall(r"^(W_SHA|CODE_SHA)=(\w+)", text, flags=re.M))
    f124 = dict(
        re.findall(
            r"^(W_SHA|CODE_SHA)=(\w+)",
            (CONTROL / "run_studio_e2e.sh").read_text(),
            flags=re.M,
        )
    )
    assert shas == f124 and len(shas) == 2
