"""WebKnossos NML reader for the fiber-skeletons ground truth.

Unit tests use a synthetic NML so they run anywhere. The integration tests are
skipped unless the real cubes have been downloaded to
``local_data/fiber_skeletons/`` (they are gitignored, ~17 MB each).
"""

from __future__ import annotations

import pathlib

import numpy as np
import pytest

from vesuvius_autoresearch.fibers.skeleton_io import (
    Skeleton,
    load_cube_skeleton,
    origin_from_stem,
    parse_nml,
    rasterize,
    size_from_stem,
)

DATA = pathlib.Path("local_data/fiber_skeletons")
CUBES = ["s1_00497_01497_03997_256", "s5_03997_01497_03997_256"]

SYNTH = """<?xml version="1.0"?>
<things>
  <parameters>
    <experiment name="scroll1a" organization="Scroll_Prize"/>
    <scale x="7.91" y="7.91" z="7.91" unit="micrometer"/>
  </parameters>
  <thing id="1" name="fiber_one" type="DEFAULT">
    <nodes>
      <node id="10" radius="1.0" x="100" y="200" z="300"/>
      <node id="11" radius="1.0" x="101" y="200" z="300"/>
      <node id="12" radius="1.0" x="102" y="200" z="300"/>
    </nodes>
    <edges>
      <edge source="10" target="11"/>
      <edge source="11" target="12"/>
    </edges>
  </thing>
  <thing id="2" name="fiber_two" type="DEFAULT">
    <nodes>
      <node id="20" radius="1.0" x="100" y="201" z="300"/>
      <node id="21" radius="1.0" x="100" y="204" z="300"/>
    </nodes>
    <edges>
      <edge source="20" target="21"/>
      <edge source="20" target="999"/>
    </edges>
  </thing>
</things>
"""


@pytest.fixture
def synth_nml(tmp_path):
    p = tmp_path / "fibers_s1a_00300z_00200y_00100x_256_v00.nml"
    p.write_text(SYNTH)
    return p


def test_parses_trees_nodes_edges(synth_nml):
    sk = parse_nml(synth_nml)
    assert len(sk) == 2
    assert sk.n_nodes == 5
    # The edge referencing missing node 999 must be dropped, not indexed.
    assert sk.n_edges == 3
    assert sk.scale_um == (7.91, 7.91, 7.91)
    assert [f.name for f in sk.fibers] == ["fiber_one", "fiber_two"]


def test_coords_are_zyx_not_xyz(synth_nml):
    """NML writes x,y,z; we must store z,y,x to match volume indexing."""
    sk = parse_nml(synth_nml)
    first = sk.fibers[0].coords[0]
    np.testing.assert_allclose(first, [300.0, 200.0, 100.0])


def test_origin_subtraction_localizes(synth_nml):
    sk = parse_nml(synth_nml, origin_zyx=(300, 200, 100))
    np.testing.assert_allclose(sk.fibers[0].coords[0], [0.0, 0.0, 0.0])
    np.testing.assert_allclose(sk.fibers[0].coords[2], [0.0, 0.0, 2.0])


def test_stem_parsing_is_zyx_order():
    """Filename order is z,y,x, the reverse of the NML attribute order."""
    assert origin_from_stem("s1_00497_01497_03997_256") == (497, 1497, 3997)
    assert size_from_stem("s1_00497_01497_03997_256") == 256
    assert origin_from_stem("/a/b/s5_03997_01497_03997_512.nml") == (3997, 1497, 3997)
    with pytest.raises(ValueError):
        origin_from_stem("not-a-cube")


def test_lengths(synth_nml):
    sk = parse_nml(synth_nml)
    f1, f2 = sk.fibers
    assert f1.total_length() == pytest.approx(2.0)  # two 1-voxel steps
    assert f2.total_length() == pytest.approx(3.0)  # one 3-voxel step
    assert sk.total_length() == pytest.approx(5.0)
    # micrometre conversion
    assert f1.total_length(7.91) == pytest.approx(2.0 * 7.91)


def test_empty_and_degenerate_are_safe(tmp_path):
    p = tmp_path / "empty.nml"
    p.write_text("<things><parameters/></things>")
    sk = parse_nml(p)
    assert len(sk) == 0 and sk.n_nodes == 0 and sk.total_length() == 0.0

    p2 = tmp_path / "single.nml"
    p2.write_text(
        '<things><thing id="1" name="x"><nodes>'
        '<node id="1" x="5" y="5" z="5"/></nodes></thing></things>'
    )
    sk2 = parse_nml(p2)
    assert len(sk2) == 1
    assert sk2.fibers[0].total_length() == 0.0  # no edges, no length


def test_in_bounds_mask(synth_nml):
    sk = parse_nml(synth_nml, origin_zyx=(300, 200, 100))
    f = sk.fibers[0]
    # coords are (0,0,0), (0,0,1), (0,0,2)
    assert f.in_bounds_mask((256, 256, 256)).all()
    assert f.in_bounds_mask((1, 1, 2)).tolist() == [True, True, False]


def test_rasterize_writes_along_edges_not_just_nodes(synth_nml):
    """Nodes can be several voxels apart; the label must be continuous."""
    sk = parse_nml(synth_nml, origin_zyx=(300, 200, 100))
    vol = rasterize(sk, (4, 8, 8))
    # fiber_two spans y=1..4 with only two annotated nodes
    ys = np.flatnonzero(vol[0, :, 0] == 2)
    assert ys.tolist() == [1, 2, 3, 4], f"gap in rasterized fiber: {ys}"


def test_rasterize_ignores_out_of_bounds(synth_nml):
    sk = parse_nml(synth_nml)  # absolute coords, far outside a small volume
    vol = rasterize(sk, (4, 4, 4))
    assert vol.sum() == 0


# --- integration against the real dataset -----------------------------------

pytestmark_data = pytest.mark.skipif(
    not all((DATA / f"{c}.nml").exists() for c in CUBES),
    reason="fiber-skeletons cubes not downloaded to local_data/fiber_skeletons/",
)


@pytestmark_data
@pytest.mark.parametrize("stem", CUBES)
def test_real_nodes_land_exactly_on_semantic_label(stem):
    """The convention proof: in-bounds nodes must hit the shipped label at 1.0.

    This is what pins zyx order and the filename origin. If either were wrong
    the rate would collapse to roughly the label's positive rate (~1%).
    """
    tifffile = pytest.importorskip("tifffile")
    sem = tifffile.imread(DATA / f"{stem}_semantic.tif")
    sk = load_cube_skeleton(DATA, stem)
    assert len(sk) > 50

    pts = []
    for f in sk.fibers:
        pts.append(f.coords[f.in_bounds_mask(sem.shape)])
    idx = np.rint(np.concatenate(pts)).astype(int)
    hit = (sem[idx[:, 0], idx[:, 1], idx[:, 2]] > 0).mean()
    assert hit == 1.0, f"{stem}: node-on-label rate {hit:.4f}, convention is wrong"


@pytestmark_data
@pytest.mark.parametrize("stem", CUBES)
def test_real_rasterization_stays_inside_semantic_label(stem):
    tifffile = pytest.importorskip("tifffile")
    sem = tifffile.imread(DATA / f"{stem}_semantic.tif")
    sk = load_cube_skeleton(DATA, stem)
    inst = rasterize(sk, sem.shape)
    inside = ((inst > 0) & (sem > 0)).sum() / max(1, (inst > 0).sum())
    # Not 1.0: sub-voxel interpolation between nodes can clip a corner.
    assert inside > 0.95, f"{stem}: only {inside:.3f} of raster inside label"
