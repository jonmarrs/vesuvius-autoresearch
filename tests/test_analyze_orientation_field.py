"""scripts/analyze_orientation_field.py: the field it measures is the tracer's, on an attested probability volume."""

import json
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import analyze_orientation_field as aof  # noqa: E402

from vesuvius_autoresearch.fibers.provenance import file_sha256  # noqa: E402

STEM = "s1_00497_01497_03997_256"
ORIGIN = (497, 1497, 3997)  # z, y, x from the stem
SIZE = 16


def _cube(src):
    """A 16^3 cube: a straight fiber along x through a blurred tube, its NML in scroll coordinates, and the cache
    record bench_cli writes beside the probability volume."""
    from scipy import ndimage

    prob = np.zeros((SIZE,) * 3, np.float32)
    prob[8, 8, 2:14] = 1
    prob = ndimage.gaussian_filter(prob, 1.0)
    prob = (prob / prob.max()).astype(np.float32)
    np.save(src / f"{STEM}_fiberprob.npy", prob)
    z, y, x = ORIGIN
    nodes = "".join(
        f'<node id="{i}" radius="1" x="{x + 3 + 2 * i}" y="{y + 8}" z="{z + 8}"/>'
        for i in range(5)
    )
    edges = "".join(f'<edge source="{i}" target="{i + 1}"/>' for i in range(4))
    (src / f"{STEM}.nml").write_text(
        f'<things><thing id="1" name="f"><nodes>{nodes}</nodes><edges>{edges}</edges></thing></things>'
    )
    record = {
        "inference": {"model": "stub"},
        "probability_sha256": file_sha256(src / f"{STEM}_fiberprob.npy"),
    }
    (src / f"{STEM}_fiberprob.json").write_text(json.dumps(record))
    return record


@pytest.fixture
def src(tmp_path, monkeypatch):
    monkeypatch.setattr(aof, "SRC", tmp_path)
    monkeypatch.setattr(aof, "size_from_stem", lambda stem: SIZE)
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
    assert row["provenance"] == record
    # bench_cli.cmd_trace's field: the cached volume as float64, at gauss_sigma 2 and sigma 3.
    assert seen == [(np.dtype(float), {"gauss_sigma": 2, "sigma": 3})]
    assert (
        row["n_scored"] > 0 and row["median_deg"] < 10
    )  # the field follows a straight tube
    # A straight fiber has constant curvature, so no correlation, written as null, not NaN.
    assert row["err_vs_curvature_pearson_r"] is None
    json.loads(json.dumps(row, allow_nan=False))


def test_a_volume_its_record_does_not_attest_is_refused(src):
    _cube(src)
    np.save(src / f"{STEM}_fiberprob.npy", np.zeros((SIZE,) * 3, np.float32))
    with pytest.raises(SystemExit, match="is not the volume its cache record attests"):
        aof.run(STEM)


def test_a_volume_without_a_record_is_refused(src):
    _cube(src)
    (src / f"{STEM}_fiberprob.json").unlink()
    with pytest.raises(SystemExit, match="no cache record"):
        aof.run(STEM)
