"""scripts/neural_tracer_ct_context.py and its chain: the registered design of
docs/preregistration/2026-10-23_neural_tracer_ct_context.md."""

from __future__ import annotations

import ast
import json
import re
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_ct_context as cc  # noqa: E402

CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_chain.sh"
F91_CHAIN = _REPO / "repro/fibers/run_neural_tracer_chain.sh"
COV = cc.COV


def test_the_conversion_is_villas_generator():
    raw = np.array([0, 1, 256, 257, 514, 32767, 65278, 65279, 65535], np.uint16)
    want = np.clip(raw.astype(np.float64) / 257, 0, 255).astype(np.uint8)
    assert np.array_equal(cc.to_uint8(raw), want)
    assert cc.to_uint8(raw).tolist() == [0, 0, 0, 1, 2, 127, 254, 254, 255]


def _fake_source(shape=(12, 12, 12), chunk=4):
    from numcodecs import Blosc

    vol = np.random.default_rng(1).integers(0, 65535, shape, dtype=np.uint16)
    codec = Blosc(cname="zstd", clevel=3, shuffle=Blosc.BITSHUFFLE)
    meta = {"chunks": [chunk] * 3, "compressor": codec.get_config(), "dimension_separator": "/", "dtype": "<u2",
            "shape": list(shape), "zarr_format": 2}  # fmt: skip
    calls = []

    def get(url: str) -> bytes:
        calls.append(url)
        if url.endswith("/0/.zarray"):
            return json.dumps(meta).encode()
        kz, ky, kx = (int(v) for v in url.removeprefix("fake/0/").split("/"))
        c = chunk
        return codec.encode(
            np.ascontiguousarray(
                vol[kz * c : (kz + 1) * c, ky * c : (ky + 1) * c, kx * c : (kx + 1) * c]
            )
        )

    return vol, get, calls


def test_read_region_returns_the_exact_voxels_and_caches_chunks(tmp_path):
    vol, get, calls = _fake_source()
    got = cc.read_region((1, 3, 5), (9, 10, 12), tmp_path, source="fake", get=get)
    assert np.array_equal(got, vol[1:9, 3:10, 5:12])
    n = len(calls)
    assert np.array_equal(
        cc.read_region((1, 3, 5), (9, 10, 12), tmp_path, source="fake", get=get), got
    )
    assert (
        len(calls) == n + 1
    )  # only the .zarray again: every chunk came from the cache
    with pytest.raises(ValueError):
        cc.read_region((0, 0, 0), (13, 4, 4), tmp_path, source="fake", get=get)


def test_the_box_keeps_finding_91s_seed_planes():
    lo, hi = cc.box_grid()
    assert (lo, hi) == (64, 192) and hi - lo == 128
    # villa's planes lie at global multiples of 64: in the cube's own grid at 0 and 64, as in finding 91.
    planes = [c - lo for c in range(0, 256, cc.PLANE_SPACING) if lo <= c < hi]
    assert planes == [0, 64]
    with pytest.raises(ValueError):
        cc.box_grid(64)
    assert (
        cc.MARGIN >= 2 * 38
    )  # at least the seed window's reach beyond each face, on both sides of the 0 plane


def test_padded_bounds_and_core():
    lo, hi = cc.padded_bounds("s5_07997_02997_05497_256")
    assert lo == (7869, 2869, 5369) and hi == (8381, 3381, 5881)
    v = np.zeros((512, 512, 512), np.uint8)
    v[128:384, 128:384, 128:384] = 7
    assert cc.core(v).shape == (256, 256, 256) and (cc.core(v) == 7).all()


def test_every_cube_is_inside_the_scan_with_its_margin():
    shape = (21000, 6700, 9100)  # 20241024131838's level 0, (z, y, x)
    for c in cc.CUBES:
        lo, hi = cc.padded_bounds(c)
        assert all(a >= 0 for a in lo) and all(
            b <= s for b, s in zip(hi, shape, strict=False)
        ), c
    assert len(cc.CUBES) == 5 and all(
        c.startswith("s5_") and c.endswith("_256") for c in cc.CUBES
    )
    assert cc.SMOKE in cc.IN_SAMPLE and len(cc.IN_SAMPLE) == 3


def _rows(cov, pred=1.0):
    return {c: {COV: cov, "pred_length": pred, "gt_length": 1.0} for c in cc.CUBES}


def _records(nh, dist=10.0):
    return {
        c: {"no_heading_share": nh, "min_seed_face_distance_grid": dist}
        for c in cc.CUBES
    }


def test_the_decision_rule():
    f91 = _rows(0.2)
    v = cc.verdict(_rows(0.26), f91, _records(0.39))
    assert v["prediction_P1"] and v["prediction_P2"] and v["prediction_P3"]
    assert v["reading"].startswith("the cube-only protocol held the neural tracer back")
    v = cc.verdict(_rows(0.259), f91, _records(0.39))  # a factor of 1.295
    assert (
        v["prediction_P1"]
        and not v["prediction_P2"]
        and v["reading"].startswith("the rule binds")
    )
    v = cc.verdict(_rows(0.3), f91, _records(0.40))
    assert not v["prediction_P1"] and v["reading"].startswith(
        "with CT around the cube it still drops"
    )
    assert not cc.verdict(_rows(0.3, pred=0.82), f91, _records(0.3))["prediction_P3"]
    assert cc.verdict(_rows(0.3, pred=0.83), f91, _records(0.3))["prediction_P3"]


def test_p2_needs_a_rise_on_every_cube():
    rows, f91 = _rows(0.5), _rows(0.2)
    rows[cc.CUBES[0]][COV] = 0.2
    assert cc.verdict(rows, f91, _records(0.3))["prediction_P2"] is False


def test_outcomes():
    f91 = _rows(0.2)
    assert cc.outcome({}, False, _rows(0.3), f91, _records(0.3)) == (
        "SMOKE_FAILED",
        None,
    )
    assert cc.outcome({"x": ["ct"]}, True, _rows(0.3), f91, _records(0.3)) == (
        "IDENTITY_FAILED",
        None,
    )
    assert (
        cc.outcome({}, True, _rows(0.3), f91, _records(0.3, dist=19.0))[0]
        == "MANIPULATION_FAILED"
    )
    assert cc.outcome({}, True, _rows(0.3), f91, _records(0.3))[0] == "OK"
    rows = _rows(0.3)
    rows.pop(cc.CUBES[-1])
    assert cc.outcome({}, True, rows, f91, _records(0.3))[0] == "INCOMPLETE"


def test_run_record_measures_seed_distance_in_the_cubes_own_grid(tmp_path):
    (tmp_path / "tiles").mkdir()
    (tmp_path / "tiles.jsonl").write_text(
        json.dumps({"dots": 10, "no_heading": 4, "owned_dots": 1}) + "\n"
    )
    seeds = np.array(
        [[64 + 5, 100, 100], [150, 150, 192 - 3]], float
    )  # 5 from the low x face, 3 from the high z face
    np.savez(tmp_path / "tiles" / "z0.npz", seed=seeds)
    r = cc.run_record(tmp_path)
    assert r["min_seed_face_distance_grid"] == 3.0 and r["no_heading_share"] == 0.4


def _neural_flags(text: str, after: str = "tracers.fibers.tracing.volume") -> set[str]:
    cmd = text.split(after, 1)[1].split(">", 1)[0]
    return set(re.findall(r"--[a-z-]+", cmd))


def test_the_trace_is_finding_91s_command():
    ours, f91c = CHAIN.read_text(), F91_CHAIN.read_text()
    ckpt = re.compile(r'^CKPT="([^"]+)"$', re.M)
    assert ckpt.search(ours).group(1) == ckpt.search(f91c).group(1)
    assert _neural_flags(ours) == _neural_flags(f91c)
    assert (
        "--ct-level 0 --ct-grid-scale 1 --grid-scale 2" in ours
        and "--base-um 7.91" in ours
    )
    assert (
        '"64,64,64,192,192,192"' in ours
        and '"0,0,0,128,128,128" "$G/run/$SMOKE.afv"' in ours
    )


def test_the_smoke_gates_the_padded_runs():
    text = CHAIN.read_text()
    assert (
        text.index('trace "$W/smoke/$SMOKE"')
        < text.index('ct_context.py" smoke')
        < text.index("for C in $CUBES")
    )
    assert "exit 4" in text.split('say "SMOKE_OK"')[0]
    cubes = re.search(r'CUBES="(.*?)"', text, re.S).group(1).split()
    assert cubes == cc.CUBES and f"SMOKE={cc.SMOKE}" in text


def _local_imports(script: str, seen: set[str]) -> set[str]:
    for node in ast.walk(ast.parse((_REPO / "scripts" / f"{script}.py").read_text())):
        for name in (
            [a.name for a in node.names] if isinstance(node, ast.Import) else []
        ):
            if (_REPO / "scripts" / f"{name}.py").exists() and name not in seen:
                seen.add(name)
                _local_imports(name, seen)
    return seen


def test_the_chain_freezes_every_script_it_runs():
    frozen = (
        re.search(r"for f in (.*?); do", CHAIN.read_text(), re.S)
        .group(1)
        .replace("\\\n", " ")
        .split()
    )
    assert set(frozen) == {
        f"{s}.py"
        for s in _local_imports(
            "neural_tracer_ct_context", {"neural_tracer_ct_context"}
        )
    }
