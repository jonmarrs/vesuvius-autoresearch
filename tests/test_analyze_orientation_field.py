"""scripts/analyze_orientation_field.py: the field it measures is the tracer's, on an attested probability volume,
the same model and recipe for every cube, and its JSON is valid."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_orientation_field as aof  # noqa: E402

from vesuvius_autoresearch.fibers.provenance import file_sha256  # noqa: E402

pytestmark = pytest.mark.filterwarnings("error::RuntimeWarning")

# A 16^3 cube, so the stem's own size and origin are parsed as for a real one.
STEM = "s1_00497_01497_03997_16"
OTHER = "s1_00497_02497_02997_16"
SIZE = 16
MODEL_FILES = {
    "plans.json": "p",
    "dataset.json": "d",
    "fold_0/checkpoint_final.pth": "c",
}
RECIPE = {
    "configuration": "3d_fullres",
    "patch_size": [128] * 3,
    "device": "cuda",
    "amp": True,
}
INFERENCE = {
    "version": 1,
    "image": {"shape": [SIZE] * 3, "dtype": "<u2", "sha256": "img"},
    "model_dir": "/home/someone/models/fiber_hz_vt",
    "model_files": MODEL_FILES,
    "recipe": RECIPE,
}


def _cube(src, stem=STEM, prob=None, inference=INFERENCE):
    """A straight fiber along x through a blurred tube, its NML in scroll coordinates, and the cache record bench_cli
    writes beside the probability volume."""
    from scipy import ndimage

    if prob is None:
        prob = np.zeros((SIZE,) * 3, np.float32)
        prob[8, 8, 2:14] = 1
        prob = ndimage.gaussian_filter(prob, 1.0)
        prob = (prob / prob.max()).astype(np.float32)
    np.save(src / f"{stem}_fiberprob.npy", prob)
    z, y, x = aof.origin_from_stem(stem)
    nodes = "".join(
        f'<node id="{i}" radius="1" x="{x + 3 + 2 * i}" y="{y + 8}" z="{z + 8}"/>'
        for i in range(5)
    )
    edges = "".join(f'<edge source="{i}" target="{i + 1}"/>' for i in range(4))
    (src / f"{stem}.nml").write_text(
        f'<things><thing id="1" name="f"><nodes>{nodes}</nodes><edges>{edges}</edges></thing></things>'
    )
    record = {
        "inference": inference,
        "probability_sha256": file_sha256(src / f"{stem}_fiberprob.npy"),
    }
    (src / f"{stem}_fiberprob.json").write_text(json.dumps(record))
    return record


@pytest.fixture
def src(tmp_path, monkeypatch):
    monkeypatch.setattr(aof, "SRC", tmp_path)
    return tmp_path


def test_a_row_records_the_attested_volume_and_the_field_is_float64(src, monkeypatch):
    record = _cube(src)
    seen = []
    real = aof.hessian

    def hessian(volume, **kw):
        seen.append((volume.dtype, kw))
        return real(volume, **kw)

    monkeypatch.setattr(aof, "hessian", hessian)
    row = aof.run(STEM)
    # The identity without the machine's model path.
    expected = {k: v for k, v in INFERENCE.items() if k != "model_dir"}
    assert row["provenance"] == {
        "probability_sha256": record["probability_sha256"],
        "inference": expected,
    }
    # bench_cli.cmd_trace's field: the cached volume as float64, at gauss_sigma 2 and sigma 3.
    assert seen == [(np.dtype(float), {"gauss_sigma": 2, "sigma": 3})]
    assert row["n_scored"] > 0 and row["median_deg"] < 10  # it follows a straight tube
    # A straight fiber has constant curvature, so no correlation: null, not NaN.
    assert row["err_vs_curvature_pearson_r"] is None
    json.dumps(row, allow_nan=False)


def test_an_empty_measurement_is_valid_json(src):
    """A constant volume leaves the field undefined at every node: every statistic is null."""
    _cube(src, prob=np.full((SIZE,) * 3, 0.5, np.float32))
    row = aof.run(STEM)
    assert row["n_scored"] == 0 and row["median_deg"] is None
    assert row["median_estimator_disagreement_deg"] is None
    json.dumps(row, allow_nan=False)


@pytest.mark.parametrize(
    "damage, message",
    [
        (lambda src: np.save(src / f"{STEM}_fiberprob.npy", np.zeros((SIZE,) * 3, np.float32)),
         "is not the volume its cache record attests"),
        (lambda src: (src / f"{STEM}_fiberprob.json").unlink(), "no readable cache record"),
        (lambda src: (src / f"{STEM}_fiberprob.json").write_text("{not json"), "no readable cache record"),
        (lambda src: (src / f"{STEM}_fiberprob.json").write_text(json.dumps({"inference": INFERENCE})),
         "is not the volume its cache record attests"),
        (lambda src: (src / f"{STEM}_fiberprob.json").write_text(json.dumps([1, 2])),
         "is not a bench_cli cache record"),
    ],
)  # fmt: skip
def test_a_volume_its_record_does_not_attest_is_refused(src, damage, message):
    _cube(src)
    damage(src)
    with pytest.raises(SystemExit, match=message) as refused:
        aof.run(STEM)
    assert "bench_cli floors --cube" in str(refused.value)


def test_a_volume_outside_0_1_is_refused(src):
    _cube(src, prob=np.full((SIZE,) * 3, 2.0, np.float32))
    with pytest.raises(SystemExit, match=r"not a probability volume in \[0, 1\]"):
        aof.run(STEM)


def test_a_volume_of_another_size_is_refused(src):
    _cube(src)
    np.save(src / f"{STEM}_fiberprob.npy", np.zeros((8,) * 3, np.float32))
    record = json.loads((src / f"{STEM}_fiberprob.json").read_text())
    record["probability_sha256"] = file_sha256(src / f"{STEM}_fiberprob.npy")
    (src / f"{STEM}_fiberprob.json").write_text(json.dumps(record))
    with pytest.raises(SystemExit, match="expected"):
        aof.run(STEM)


def _main(src, monkeypatch):
    out = src / "out.json"
    monkeypatch.setattr(aof, "CUBES", [STEM, OTHER])
    monkeypatch.setattr(sys, "argv", ["aof", "--json-out", str(out)])
    aof.main()
    return json.loads(out.read_text())


def test_main_writes_every_cube_from_one_model_and_recipe(src, monkeypatch):
    _cube(src, STEM)
    other = {**INFERENCE, "image": {"sha256": "other"}, "model_dir": "/elsewhere"}
    _cube(src, OTHER, inference=other)
    report = _main(src, monkeypatch)
    assert [r["cube"] for r in report["cubes"]] == [STEM, OTHER]


@pytest.mark.parametrize(
    "change",
    [
        {"recipe": {**RECIPE, "patch_size": [192] * 3}},
        {"recipe": {**RECIPE, "device": "cpu", "amp": False}},
        {
            "model_files": {
                **MODEL_FILES,
                "fold_0/checkpoint_final.pth": "x",
            }
        },
        {"version": 2},
    ],
)
def test_main_refuses_cubes_from_different_models_or_recipes(src, monkeypatch, change):
    _cube(src, STEM)
    _cube(src, OTHER, inference={**INFERENCE, **change})
    with pytest.raises(SystemExit, match="different models or recipes"):
        _main(src, monkeypatch)
    assert not (src / "out.json").exists()
