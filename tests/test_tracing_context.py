"""scripts/tracing_context.py and its chain: the registered design of docs/preregistration/2026-10-23_tracing_context.md."""

from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_analysis as f91  # noqa: E402
import octant_crop_rescore as f95  # noqa: E402
import tracing_context as tc  # noqa: E402

from vesuvius_autoresearch.fibers.skeleton_io import (  # noqa: E402
    origin_from_stem,
    size_from_stem,
)

CHAIN = _REPO / "repro/fibers/run_tracing_context_chain.sh"
F91_CHAIN = _REPO / "repro/fibers/run_neural_tracer_chain.sh"
PEN = tc.PEN


def test_each_stand_in_is_its_octants_absolute_origin():
    out = tc.stems()
    assert len(out) == 24 and len({s for s, _, _ in out}) == 24
    for stem, parent, o in out:
        assert origin_from_stem(stem) == tuple(
            a + b for a, b in zip(origin_from_stem(parent), o, strict=False)
        )
        assert (
            size_from_stem(stem) == 256 and stem.split("_")[0] == parent.split("_")[0]
        )
    assert (
        tc.stand_in("s5_06494_01994_03994_512", (256, 0, 256))
        == "s5_06750_01994_04250_256"
    )


def test_no_stand_in_names_a_real_cube():
    names = {s for s, _, _ in tc.stems()}
    assert not names & set(f91.ALL) and tc.SMOKE not in names
    assert (
        tc.SMOKE in f91.IN_SAMPLE
        and tc.SMOKE.endswith("_256")
        and tc.SMOKE.startswith("s5_")
    )


def test_the_octants_and_parents_are_finding_95s():
    assert (
        tc.PARENTS == f95.CUBES
        and tc.OCTANTS == f95.OCTANTS
        and tc.SIZE == f95.SIZE == 256
    )
    assert tc.TOLS == (4.0, 2.0)
    assert [tc.octant_key(p, o) for _, p, o in tc.stems()] == [
        f"{p}@{o[0]}_{o[1]}_{o[2]}" for p in f95.CUBES for o in f95.OCTANTS
    ]


def test_crop_takes_the_octant_and_refuses_a_short_one():
    v = np.arange(8**3).reshape(8, 8, 8)
    assert np.array_equal(tc.crop(v, (4, 0, 4), 4), v[4:8, 0:4, 4:8])
    with pytest.raises(ValueError):
        tc.crop(v, (6, 0, 0), 4)


def _fake_source(tmp_path: Path, parent: str, n: int) -> tuple[Path, Path, np.ndarray]:
    import tifffile
    import zarr

    src, zarrs = tmp_path / "src", tmp_path / "zarr"
    src.mkdir()
    image = np.random.default_rng(0).integers(0, 255, (n, n, n), dtype=np.uint8)
    tifffile.imwrite(src / f"{parent}_image.tif", image)
    (src / f"{parent}.nml").write_bytes(b"<things/>")
    zarr.open(
        str(zarrs / f"{parent}.zarr"),
        mode="w",
        shape=image.shape,
        chunks=(4, 4, 4),
        dtype="u1",
    )[...] = image
    tifffile.imwrite(src / f"{tc.SMOKE}_image.tif", image[:4, :4, :4])
    (src / f"{tc.SMOKE}.nml").write_bytes(b"<smoke/>")
    return src, zarrs, image


def test_prepare_writes_each_octant_and_resumes(tmp_path):
    import tifffile
    import zarr

    parent = "s5_00100_00200_00300_8"
    octants = [(z, y, x) for z in (0, 4) for y in (0, 4) for x in (0, 4)]
    src, zarrs, image = _fake_source(tmp_path, parent, 8)
    data, ct = tmp_path / "w" / "data", tmp_path / "w" / "ct"
    args = {
        "src": src,
        "zarrs": zarrs,
        "parents": [parent],
        "octants": octants,
        "size": 4,
    }
    out = tc.prepare(data, ct, **args)
    assert len(out["stems"]) == 8
    for stem, _, o in tc.stems([parent], octants, 4):
        want = tc.crop(image, o, 4)
        assert np.array_equal(tifffile.imread(data / f"{stem}_image.tif"), want)
        assert np.array_equal(
            zarr.open(str(ct / f"{stem}.zarr" / "0"), mode="r")[...], want
        )
        assert (data / f"{stem}.nml").read_bytes() == b"<things/>"
    assert not list(data.glob("*_fiberprob*"))
    assert (ct / f"{tc.SMOKE}.zarr" / "0").is_symlink()
    tc.prepare(data, ct, **args)  # a resume finds everything identical
    stem = out["stems"][0]
    tifffile.imwrite(data / f"{stem}_image.tif", np.zeros((4, 4, 4), np.uint8))
    with pytest.raises(FileExistsError):
        tc.prepare(data, ct, **args)


def test_prepare_gives_its_outputs_the_umasks_mode(tmp_path):
    """mkstemp and mkdtemp create 0600 and 0700; renamed into place as they are, the outputs would be the owner's
    alone (tests/test_file_modes.py)."""
    import os
    import stat

    parent = "s5_00100_00200_00300_8"
    src, zarrs, _ = _fake_source(tmp_path, parent, 8)
    data, ct = tmp_path / "w" / "data", tmp_path / "w" / "ct"
    previous = os.umask(0o027)
    try:
        out = tc.prepare(
            data,
            ct,
            src=src,
            zarrs=zarrs,
            parents=[parent],
            octants=[(0, 0, 0)],
            size=4,
        )
    finally:
        os.umask(previous)
    stem = out["stems"][0]

    def mode(p):
        return stat.S_IMODE(os.stat(p).st_mode)

    assert (
        mode(data / f"{stem}_image.tif") == 0o640
        and mode(data / f"{stem}.nml") == 0o640
    )
    assert mode(ct / f"{stem}.zarr") == 0o750


def test_prepare_refuses_when_finding_85s_array_differs_from_the_tiff(tmp_path):
    import zarr

    parent = "s5_00100_00200_00300_8"
    src, zarrs, image = _fake_source(tmp_path, parent, 8)
    zarr.open(str(zarrs / f"{parent}.zarr"), mode="r+")[0, 0, 0] = (
        int(image[0, 0, 0]) ^ 1
    )
    with pytest.raises(SystemExit):
        tc.prepare(tmp_path / "d", tmp_path / "c", src=src, zarrs=zarrs, parents=[parent],
                   octants=[(0, 0, 0)], size=4)  # fmt: skip


def test_smoke_passes_only_when_all_three_match():
    p, lab = np.full((2, 2, 2), 0.5, np.float32), np.ones((2, 2, 2), np.int32)
    assert tc.smoke_problems(p, p.copy(), lab, lab.copy(), True) == []
    q = p.copy()
    q[0, 0, 0] = 0.5000001
    assert len(tc.smoke_problems(q, p, lab, lab, True)) == 1
    assert "max |diff|" in tc.smoke_problems(q, p, lab, lab, True)[0]
    assert len(tc.smoke_problems(p, p, lab * 2, lab, True)) == 1
    assert len(tc.smoke_problems(p, p, lab, lab, False)) == 1
    assert len(tc.smoke_problems(p[:1], p, lab[:1], lab, False)) == 3


def _rows(
    leads: int, n: int, neural: float = 2.0, tracer: float = 1.0
) -> tuple[dict, dict]:
    rows, crops = {}, {}
    for i in range(n):
        hi, lo = (neural, tracer) if i < leads else (tracer, neural)
        rows[f"k{i}"] = {
            "neural": {4.0: {PEN: hi}, 2.0: {PEN: 0.5}},
            "tracer": {4.0: {PEN: lo}, 2.0: {PEN: 1.0}},
        }
        crops[f"k{i}"] = {"neural": {"4.0": {PEN: hi}}, "tracer": {"4.0": {PEN: lo}}}
    return rows, crops


@pytest.mark.parametrize(
    "leads,n,p1,word",
    [
        (16, 24, True, "not the tracing context"),
        (15, 24, False, "inconclusive"),
        (9, 24, False, "inconclusive"),
        (8, 24, False, "the tracing context reproduces it"),
        (14, 21, True, "not the tracing context"),
        (7, 21, False, "the tracing context reproduces it"),
        (13, 20, False, "inconclusive"),
    ],
)
def test_the_decision_rule(leads, n, p1, word):
    v = tc.verdict(*_rows(leads, n))
    assert v["neural_leads_at_4"] == [leads, n] and v["prediction_P1"] is p1
    assert v["reading"].startswith(word)
    assert v["neural_leads_at_2"] == [0, n]


def test_a_tie_is_not_a_lead_at_either_tolerance():
    rows, crops = _rows(24, 24)
    for r in rows.values():
        r["neural"][4.0][PEN] = r["tracer"][4.0][PEN]
        r["neural"][2.0][PEN] = r["tracer"][2.0][PEN]
    v = tc.verdict(rows, crops)
    assert v["neural_leads_at_4"] == [0, 24] and v["neural_leads_at_2"] == [0, 24]


def test_fewer_than_20_scored_is_incomplete_and_identity_comes_first():
    rows, crops = _rows(19, 19)
    status, v = tc.outcome({}, rows, crops)
    assert (
        status == "INCOMPLETE" and v["prediction_P1"] is None and v["reading"] is None
    )
    rows, crops = _rows(24, 24)
    assert tc.outcome({"smoke": ["x"]}, rows, crops) == ("IDENTITY_FAILED", None)
    assert tc.outcome({}, rows, crops)[0] == "OK"


def test_p2_is_each_tracers_median_run_over_crop_within_the_band():
    rows, crops = _rows(24, 24)
    assert tc.verdict(rows, crops)["prediction_P2"] is True
    for r in rows.values():
        r["tracer"][4.0][PEN] *= 0.89
    v = tc.verdict(rows, crops)
    assert (
        v["prediction_P2"] is False and v["median_run_over_crop_at_4"]["neural"] == 1.0
    )
    assert v["median_run_over_crop_at_4"]["tracer"] == pytest.approx(0.89)
    for r in crops.values():
        r["neural"]["4.0"][PEN] = 0.0
    with pytest.raises(ValueError):
        tc.verdict(rows, crops)


def test_an_octant_without_both_runs_is_not_scored(tmp_path):
    (tmp_path / "tracer").mkdir()
    np.save(tmp_path / "tracer" / "x_instances.npy", np.zeros((2, 2, 2), np.int32))
    assert tc.octant_labels(tmp_path, "x") == {
        "neural": None,
        "tracer": None,
    }  # wrong shape, no .afv


def _neural_flags(text: str) -> dict:
    cmd = text.split("tracers.fibers.tracing.volume", 1)[1].split(">", 1)[0]
    return dict(re.findall(r"(--[a-z-]+) (\"[^\"]*\"|\S+)", cmd))


def test_the_neural_tracer_runs_with_finding_91s_settings():
    ours, f91c = CHAIN.read_text(), F91_CHAIN.read_text()
    ckpt = re.compile(r'^CKPT="([^"]+)"$', re.M)
    assert ckpt.search(ours).group(1) == ckpt.search(f91c).group(1)
    a, b = _neural_flags(ours), _neural_flags(f91c)
    differ = {"--ct", "--presence", "--box", "--afv-template", "--out"}
    assert a.keys() == b.keys() and {k for k in a if a[k] != b[k]} <= differ
    assert (
        a["--box"] == '"0,0,0,128,128,128"'
        and a["--base-um"] == "7.91"
        and a["--grid-scale"] == "2"
    )
    assert a["--afv-template"] == '"$G/run/$parent.afv"'


def test_our_tracer_runs_at_its_published_defaults_on_the_stand_in():
    text = CHAIN.read_text()
    call = text.split("vesuvius_autoresearch.fibers.bench_cli", 1)[1].split(">", 1)[0]
    flags = re.findall(r"--[a-z-]+", call)
    assert flags == [
        "--data-dir",
        "--cube",
        "--device",
        "--save-instances",
        "--json-out",
    ]
    assert '--data-dir "$W/data" trace' in call and "--device cuda" in call


def test_the_smoke_gates_every_octant():
    text = CHAIN.read_text()
    assert (
        text.index('run "$SMOKE" "$SMOKE"')
        < text.index('tracing_context.py" smoke')
        < text.index('for L in "${LINES[@]}"')
    )
    assert "exit 4" in text.split('say "SMOKE_OK"')[0]
    assert f"SMOKE={tc.SMOKE}" in text


def _local_imports(script: str, seen: set[str]) -> set[str]:
    tree = ast.parse((_REPO / "scripts" / f"{script}.py").read_text())
    for node in ast.walk(tree):
        names = [a.name for a in node.names] if isinstance(node, ast.Import) else []
        for name in names:
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
    want = _local_imports("tracing_context", {"tracing_context"}) | {
        "make_tracer_presence"
    }
    assert set(frozen) == {f"{s}.py" for s in want}


def test_the_chain_runs_the_registered_commits_package():
    """The shared venv's editable install resolves vesuvius_autoresearch from the main checkout; the chain pins it."""
    text = CHAIN.read_text()
    pin = text.index('export PYTHONPATH="$REPO/src')
    assert pin < text.index(
        '"$PY" "$LOOPDIR/scripts/loop_control.py"'
    ) and pin < text.index("vesuvius_autoresearch.fibers.bench_cli")


def test_the_registrations_figures_are_the_evidence():
    """The figures docs/preregistration/2026-10-23_tracing_context.md argues from are findings 91, 94
    and 95's committed rows, and its thresholds are the script's."""
    import json
    import statistics
    from collections import Counter

    flat = " ".join(
        (_REPO / "docs/preregistration/2026-10-23_tracing_context.md")
        .read_text()
        .split()
    )
    t94 = json.loads((_REPO / "reports/tolerance4_rescore.json").read_text())
    f95j = json.loads((_REPO / "reports/octant_crop_rescore.json").read_text())
    f91j = json.loads((_REPO / "reports/neural_tracer_entrant.json").read_text())

    ratio = {
        c: t94["rows_neural"][c][PEN] / t94["rows_tracer"][c][PEN]
        for c in f91.IN_SAMPLE
    }
    small = [v for c, v in ratio.items() if c.endswith("_256")]
    big = [v for c, v in ratio.items() if c.endswith("_512")]
    assert len(small) == 8 and max(small) < 1 and len(big) == 3 and min(big) > 1
    assert (
        "leads our tracer on all three in-sample 512³ cubes, and trails it on all eight in-sample 256³ ones"
        in flat
    )
    assert (
        f"a median {statistics.median(small):.2f} of ours ({min(small):.2f}–{max(small):.2f})"
        in flat
    )

    octant = {
        k: v["neural"]["4.0"][PEN] / v["tracer"]["4.0"][PEN]
        for k, v in f95j["octants"].items()
    }
    leads = [v for v in octant.values() if v > 1]
    assert (
        f"The lead held on {len(leads)} of {len(octant)}, a median {statistics.median(octant.values()):.2f}×"
        in flat
    )
    assert (
        f"{sum(v < 1.15 for v in leads)} of finding 95's {len(leads)} leads are under 1.15×"
        in flat
    )

    stops = Counter()
    for row in f91j["neural_rows"].values():
        stops.update(row["stop_reasons"])
    others = sum(stops.values()) - stops["bounds"]
    assert (
        f"finding 91's {len(f91j['neural_rows'])} runs record {stops['bounds']} `bounds` stops "
        f"against {others:,} others" in flat
    )
    assert 1 - ((tc.SIZE - 2 * 64) / tc.SIZE) ** 3 == 7 / 8
    assert "7/8 of an octant lies within 64 voxels of a face" in flat

    lo, hi = tc.P2_BAND
    assert f"lies in {lo:.2f}–{hi:.2f}" in flat
    assert f"| n < {tc.MIN_SCORED} | INCOMPLETE |" in flat
    assert "at least two thirds of the octants scored (16 of 24)" in flat
