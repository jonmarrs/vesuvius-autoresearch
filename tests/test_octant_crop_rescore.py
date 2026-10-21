"""scripts/octant_crop_rescore.py: the three in-sample 512³ cubes scored in their eight 256³ octants."""

import sys
import types
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import octant_crop_rescore as oc  # noqa: E402

PEN = "erl_merge_penalized"


def _fiber(fid, *nodes):
    c = np.asarray(nodes, float)
    return types.SimpleNamespace(
        id=fid,
        name=f"f{fid}",
        node_ids=np.arange(len(c)),
        coords=c,
        edges=np.array([[i, i + 1] for i in range(len(c) - 1)]),
        in_bounds_mask=lambda shape, c=c: np.all(
            (c >= 0) & (c <= np.asarray(shape) - 1), axis=1
        ),
    )


def test_the_octants_tile_the_cube():
    assert len(oc.OCTANTS) == 8 and len(set(oc.OCTANTS)) == 8
    assert all(all(v in (0, 256) for v in o) for o in oc.OCTANTS)


def test_a_cropped_skeleton_is_shifted_and_keeps_fibers_with_two_nodes_inside():
    skel = types.SimpleNamespace(
        fibers=[
            _fiber(
                1, (300, 10, 10), (310, 10, 10), (320, 10, 10)
            ),  # inside the octant at z 256
            _fiber(2, (250, 10, 10), (260, 10, 10)),  # one node inside: dropped
            _fiber(3, (10, 10, 10), (20, 10, 10)),  # in another octant: dropped
            _fiber(
                4, (250, 20, 20), (257, 20, 20), (265, 20, 20)
            ),  # two inside: kept, its outside node kept too
        ],
        scale_um=(7.91,) * 3,
        origin_zyx=(0, 0, 0),
    )
    out = oc.crop_skeleton(skel, (256, 0, 0), 256)
    assert [f.id for f in out.fibers] == [1, 4]
    assert np.allclose(out.fibers[0].coords[:, 0], [44, 54, 64])
    assert np.allclose(out.fibers[1].coords[:, 0], [-6, 1, 9])
    assert out.scale_um == skel.scale_um


def test_a_cropped_labelling_is_the_octants_voxels():
    lab = np.zeros((512, 512, 512), np.int32)
    lab[300, 5, 400] = 7
    c = oc.crop_labels(lab, (256, 0, 256), 256)
    assert c.shape == (256, 256, 256) and c[44, 5, 144] == 7 and c.sum() == 7


def _rows(neural, tracer):
    return {
        f"{c}@{o}": {"neural": {4.0: {PEN: neural}}, "tracer": {4.0: {PEN: tracer}}}
        for c in oc.CUBES
        for o in oc.OCTANTS
    }


def test_the_verdict_thresholds():
    assert oc.verdict(_rows(5.0, 4.0))["reading"].startswith(
        "cropping does not reverse it"
    )
    assert oc.verdict(_rows(3.0, 4.0))["reading"].startswith("cropping reverses it")
    rows = _rows(5.0, 4.0)
    for k in list(rows)[:9]:
        rows[k]["neural"][4.0][PEN] = 3.0  # 15 of 24 lead: neither threshold
    v = oc.verdict(rows)
    assert v["neural_leads_at_4"] == [15, 24] and v["reading"].startswith(
        "inconclusive"
    )
    rows = _rows(5.0, 4.0)
    for k in list(rows)[:8]:
        rows[k]["neural"][4.0][PEN] = 3.0  # 16 of 24: holds, inclusive
    assert oc.verdict(rows)["prediction_P1_leads_on_16_of_24"] is True


def test_ties_do_not_lead():
    assert oc.verdict(_rows(4.0, 4.0))["neural_leads_at_4"] == [0, 24]


@pytest.mark.parametrize(
    "identity, status", [({"x": ["erl"]}, "IDENTITY_FAILED"), ({}, "OK")]
)
def test_the_status(identity, status):
    got, reading = oc.outcome(identity, _rows(5.0, 4.0))
    assert got == status and (reading is None) == (status == "IDENTITY_FAILED")


def test_the_cubes_are_the_in_sample_512_ones():
    assert [c for c in oc.f91.IN_SAMPLE if c.endswith("_512")] == oc.CUBES and len(
        oc.CUBES
    ) == 3
