"""scripts/neural_tracer_ct_context_512.py and its chain: the registered design of
docs/preregistration/2026-10-24_neural_tracer_ct_context_512.md."""

from __future__ import annotations

import ast
import json
import math
import re
import statistics
import sys
from pathlib import Path

import numpy as np
import pytest

_REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO / "scripts"))
import neural_tracer_ct_context as cc  # noqa: E402
import neural_tracer_ct_context_512 as c5  # noqa: E402
import raw_tiff_region  # noqa: E402

CHAIN = _REPO / "repro/fibers/run_neural_tracer_ct_context_512_chain.sh"
F91_CHAIN = _REPO / "repro/fibers/run_neural_tracer_chain.sh"
VOLUME = (
    _REPO
    / "villa/vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume.py"
)
REG = _REPO / "docs/preregistration/2026-10-24_neural_tracer_ct_context_512.md"
COV, PEN = c5.COV, c5.PEN


def test_the_cubes_are_the_eleven_512_cubes_inside_their_scans():
    rows = json.loads((_REPO / "reports/neural_tracer_boundary.json").read_text())[
        "rows"
    ]
    assert set(c5.ALL_CUBES) == {c for c, r in rows.items() if r["size"] == 512}
    assert c5.ALL_CUBES == c5.S5_CUBES + c5.S3_CUBES  # the Scroll-5 cubes first
    assert len(c5.S5_CUBES) == 3 and len(c5.S3_CUBES) == 8
    assert set(c5.S5_CUBES) <= set(cc.f91.IN_SAMPLE) and not set(c5.S3_CUBES) & set(
        cc.f91.IN_SAMPLE
    )
    assert c5.IN_SAMPLE == c5.S5_CUBES and c5.SMOKE in c5.S5_CUBES
    shapes = {
        "s5": (21000, 6700, 9100),
        "s3": raw_tiff_region.VOLUMES["s3"]["shape"],
    }  # 20241024131838's level 0
    for c in c5.ALL_CUBES:
        lo, hi = cc.padded_bounds(c)
        assert hi[0] - lo[0] == c5.SIZE + 2 * c5.MARGIN
        assert all(a >= 0 for a in lo) and all(
            b <= s for b, s in zip(hi, shapes[c[:2]], strict=True)
        ), c
    assert c5.S3_SOURCE.endswith("PHerc332.volpkg/volumes/20231117143551")


def test_each_cube_is_read_from_its_own_scroll(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(
        cc, "read_region", lambda lo, hi, cache, get: calls.append(("s5", lo, hi))
    )
    monkeypatch.setattr(raw_tiff_region, "read_region",
                        lambda vol, lo, hi, cache, get_ranges: calls.append((vol, lo, hi)))  # fmt: skip
    c5.read_padded("s5_06494_01994_03994_512", tmp_path)
    c5.read_padded("s3_00994_00494_01994_512", tmp_path)
    assert calls == [
        ("s5", (6366, 1866, 3866), (7134, 2634, 4634)),
        ("s3", (866, 366, 1866), (1634, 1134, 2634)),
    ]
    with pytest.raises(ValueError, match="not one of this registration's scrolls"):
        c5.read_padded("s1_00497_01497_03997_256", tmp_path)


def test_the_box_is_one_tile_and_keeps_finding_91s_seed_planes():
    lo, hi = c5.box_grid()
    assert (lo, hi) == (64, 320) and hi - lo == 256
    planes = [c - lo for c in range(0, 512, cc.PLANE_SPACING) if lo <= c < hi]
    assert planes == [
        0,
        64,
        128,
        192,
    ]  # in the cube's own grid, as in finding 91's box 0..256
    text = VOLUME.read_text()
    assert "ap.add_argument('--tile', type=float, default=256.)" in text
    assert "ap.add_argument('--plane-spacing', type=float, default=64.)" in text
    # tiles are laid from the box's corner, so the padded box is one tile as finding 91's was
    assert "for x in np.arange(lo[0], hi[0], args.tile)]" in text
    assert (
        "first = int(np.ceil(lo[axis_xyz]/args.plane_spacing)*args.plane_spacing)"
        in text
    )


def test_the_presence_is_finding_91s_level_in_the_padded_frame(tmp_path, monkeypatch):
    import zarr

    monkeypatch.setattr(c5, "SIZE", 128)  # a small cube: level 64³, padded 192³
    monkeypatch.setattr(c5, "T", tmp_path / "t")
    cube = "s5_00000_00000_00000_128"
    src = np.random.default_rng(2).integers(0, 255, (64,) * 3, dtype=np.uint8)
    zarr.open(str(tmp_path / "t/presence" / f"{cube}_presence.zarr" / "1"), mode="w", shape=src.shape,
              chunks=(32,) * 3, dtype="u1")[...] = src  # fmt: skip
    out = c5.presence(tmp_path / "w", [cube])
    assert out[cube] == {"shape": [192, 192, 192], "core_equals_finding_91": True}
    got = zarr.open(
        str(tmp_path / "w/presence" / f"{cube}_presence.zarr" / "1"), mode="r"
    )[...]
    assert (
        np.array_equal(got[64:128, 64:128, 64:128], src)
        and got.sum() == src.astype(np.int64).sum()
    )


def test_run_record_measures_seed_distance_in_the_cubes_own_grid(tmp_path):
    (tmp_path / "tiles").mkdir()
    (tmp_path / "tiles.jsonl").write_text(
        json.dumps({"dots": 10, "no_heading": 4, "owned_dots": 1, "seconds": 150.5})
        + "\n"
    )
    seeds = np.array(
        [[64 + 5, 100, 100], [200, 200, 320 - 3]], float
    )  # 5 from the low x face, 3 from the high z face
    np.savez(tmp_path / "tiles" / "z0.npz", seed=seeds)
    r = c5.run_record(tmp_path)
    assert (
        r["min_seed_face_distance_grid"] == 3.0
        and r["no_heading_share"] == 0.4
        and r["seconds"] == 150.5
    )


def test_a_padded_runs_fibers_are_scored_in_the_cubes_frame(monkeypatch):
    m = float(c5.MARGIN)
    xyz = np.array([[m + 10, m + 20, m + 400], [m + 11, m + 20, m + 400]])
    monkeypatch.setattr(cc.afv_to_labels, "read_afv", lambda path: {7: xyz})
    lab = c5.labels_in_cube(Path("unused.afv"))
    assert lab.shape == (512,) * 3 and np.count_nonzero(lab) == 2
    assert lab[400, 20, 10] and lab[400, 20, 11]


def _rows(cov, pen=10.0, cubes=c5.ALL_CUBES):
    return {
        c: {COV: cov, PEN: pen, "pred_length": 1.0, "gt_length": 1.0} for c in cubes
    }


def _records(nh, dist=10.0, cubes=c5.ALL_CUBES):
    return {
        c: {"no_heading_share": nh, "min_seed_face_distance_grid": dist} for c in cubes
    }


def _f91_records(nh=0.3, cubes=c5.ALL_CUBES):
    return {c: {"dots": 1000, "no_heading": round(1000 * nh)} for c in cubes}


def _ours(s5_pen, s3_pen, cubes=c5.ALL_CUBES):
    return {c: {PEN: s5_pen if c.startswith("s5_") else s3_pen} for c in cubes}


def _verdict(
    cubes,
    cov=0.4,
    nh=0.04,
    f91_cov=0.33,
    ours2=None,
    ours4=None,
    rows=None,
    records=None,
):
    return c5.verdict(cubes, rows or _rows(cov), _rows(cov, pen=50.0), _rows(f91_cov), _f91_records(),
                      records or _records(nh), ours2 or _ours(20.0, 5.0), ours4 or _ours(40.0, 40.0))  # fmt: skip


def test_the_decision_rule():
    v = _verdict(c5.S5_CUBES)
    assert (
        v["prediction_P1"]
        and v["prediction_P2"]
        and v["prediction_P3"]
        and v["prediction_P4"] is None
    )
    assert v["reading"].startswith(
        "on the 512³ cubes too the cube-only protocol held it back"
    )
    v = _verdict(c5.S5_CUBES, cov=0.33 * 1.149)
    assert (
        v["prediction_P1"]
        and not v["prediction_P2"]
        and v["reading"].startswith("the rule binds")
    )
    assert _verdict(c5.S5_CUBES, cov=0.33 * 1.151)["prediction_P2"]
    # P1 on the in-sample set: below 0.05 as well as below finding 91's share
    v = _verdict(c5.S5_CUBES, nh=0.05)
    assert not v["prediction_P1"] and v["reading"].startswith(
        "with CT around the cube it still drops"
    )
    # on Scroll 3 only below finding 91's share (0.3 here)
    assert _verdict(c5.S3_CUBES, nh=0.29)["prediction_P1"]
    assert not _verdict(c5.S3_CUBES, nh=0.30)["prediction_P1"]


def test_p2_needs_a_rise_on_every_cube():
    rows = _rows(0.6)
    rows[c5.S3_CUBES[0]][COV] = 0.33
    assert _verdict(c5.S3_CUBES, rows=rows)["prediction_P2"] is False


def test_p3_is_finding_91s_ranking():
    # ahead on all at tolerance 4; at tolerance 2 behind on Scroll 5 and ahead on Scroll 3
    assert (
        _verdict(c5.S5_CUBES)["prediction_P3"]
        and _verdict(c5.S3_CUBES)["prediction_P3"]
    )
    assert not _verdict(c5.S5_CUBES, ours2=_ours(9.0, 5.0))[
        "prediction_P3"
    ]  # it overtakes on Scroll 5
    assert not _verdict(c5.S3_CUBES, ours2=_ours(20.0, 11.0))[
        "prediction_P3"
    ]  # it falls behind on Scroll 3
    assert not _verdict(c5.S3_CUBES, ours4=_ours(40.0, 50.0))[
        "prediction_P3"
    ]  # a tie at tolerance 4 is no lead
    ours4 = _ours(40.0, 40.0)
    ours4[c5.S5_CUBES[1]][PEN] = 60.0
    assert not _verdict(c5.S5_CUBES, ours4=ours4)["prediction_P3"]


def test_p4_counts_the_scroll_3_cubes_below_a_tenth():
    records = _records(0.04)
    for c in c5.S3_CUBES[:2]:
        records[c]["no_heading_share"] = 0.2
    assert _verdict(c5.S3_CUBES, records=records)["prediction_P4"]  # six of eight
    records[c5.S3_CUBES[2]]["no_heading_share"] = 0.10
    assert _verdict(c5.S3_CUBES, records=records)["prediction_P4"] is False


def test_the_two_sets_are_judged_apart():
    rows, rows4, f91 = _rows(0.4), _rows(0.4, pen=50.0), _rows(0.33)
    args = (
        rows,
        rows4,
        f91,
        _f91_records(),
        _records(0.04),
        _ours(20.0, 5.0),
        _ours(40.0, 40.0),
    )
    assert c5.outcome(c5.S5_CUBES, {c5.S3_CUBES[0]: ["ct"]}, True, *args)[0] == "OK"
    assert c5.outcome(c5.S3_CUBES, {c5.S3_CUBES[0]: ["ct"]}, True, *args) == (
        "IDENTITY_FAILED",
        None,
    )
    assert c5.outcome(c5.S3_CUBES, {}, False, *args) == ("SMOKE_FAILED", None)
    rows.pop(c5.S3_CUBES[-1])
    assert c5.outcome(c5.S5_CUBES, {}, True, *args)[0] == "OK"
    assert c5.outcome(c5.S3_CUBES, {}, True, *args)[0] == "INCOMPLETE"
    far = (
        rows,
        rows4,
        f91,
        _f91_records(),
        _records(0.04, dist=19.0),
        _ours(20.0, 5.0),
        _ours(40.0, 40.0),
    )
    assert c5.outcome(c5.S5_CUBES, {}, True, *far)[0] == "MANIPULATION_FAILED"


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
    lo, hi = c5.box_grid()
    assert (
        f'"{lo},{lo},{lo},{hi},{hi},{hi}"' in ours
        and '"0,0,0,256,256,256" "$G/run/$SMOKE.afv"' in ours
    )


def test_the_smoke_gates_the_padded_runs():
    text = CHAIN.read_text()
    assert (
        text.index('trace "$W/smoke/$SMOKE"')
        < text.index('ct_context_512.py" smoke')
        < text.index("for C in $CUBES")
    )
    assert "exit 4" in text.split('say "SMOKE_OK"')[0]
    cubes = re.search(r'CUBES="(.*?)"', text, re.S).group(1).split()
    assert cubes == c5.ALL_CUBES and f"SMOKE={c5.SMOKE}" in text
    assert (
        'len(p["presence"]) == 11' in text and 'W="${W:-$T/ct_context_512_run}"' in text
    )


def test_the_chain_runs_the_registered_commits_package():
    text = CHAIN.read_text()
    assert text.index('export PYTHONPATH="$REPO/src') < text.index(
        '"$PY" "$LOOPDIR/scripts/loop_control.py"'
    )


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
    want = _local_imports(
        "neural_tracer_ct_context_512", {"neural_tracer_ct_context_512"}
    )
    assert set(frozen) == {f"{s}.py" for s in want}


def test_the_registrations_figures_are_the_evidence():
    """The figures docs/preregistration/2026-10-24_neural_tracer_ct_context_512.md argues from are findings 91, 94, 96
    and 97's committed rows, and its thresholds are the script's."""
    flat = " ".join(REG.read_text().split())
    rows = json.loads((_REPO / "reports/neural_tracer_boundary.json").read_text())[
        "rows"
    ]
    f97 = json.loads((_REPO / "reports/neural_tracer_ct_context.json").read_text())
    rep = json.loads((_REPO / "reports/neural_tracer_entrant.json").read_text())
    t94 = json.loads((_REPO / "reports/tolerance4_rescore.json").read_text())

    def span(vals, digits=3):
        return f"{min(vals):.{digits}f}–{max(vals):.{digits}f}"

    small = list(f97["records"])
    assert len(small) == 10
    before = [rows[c]["no_heading_share"] for c in small]
    after = [f97["records"][c]["no_heading_share"] for c in small]
    factor = [
        f97["rows_tol2"][c][COV] / f97["finding_91_rows_tol2"][c][COV] for c in small
    ]
    assert (
        f"fell from {span(before)} to {span(after)}, and its coverage rose {span(factor, 2)}× on every cube"
        in flat
    )
    seed512, seed256 = (
        rows[c5.SMOKE]["seedable_share"],
        rows[small[0]]["seedable_share"],
    )
    assert (
        f"fits in {seed512:.3f} of a 512³ cube, against {seed256:.3f} of a 256³ one"
        in flat
    )
    assert (
        f"There it dropped {span([rows[c]['no_heading_share'] for c in c5.ALL_CUBES])} of its seed dots"
        in flat
    )
    held = [c for c in small if rows[c]["split"] == "held_out"]
    ins = [c for c in small if c not in held]
    assert len(held) == 2 and all(rows[c]["split"] == "held_out" for c in c5.S3_CUBES)
    h = sorted(f97["records"][c]["no_heading_share"] for c in held)
    assert f"{h[0]:.3f} and {h[1]:.3f} of seed dots were still dropped" in flat
    assert (
        f"against at most {max(f97['records'][c]['no_heading_share'] for c in ins):.3f} on the eight in-sample"
        in flat
    )

    # P1's in-sample threshold is above finding 97's in-sample maximum
    assert max(f97["records"][c]["no_heading_share"] for c in ins) < c5.IN_SAMPLE_BELOW
    assert (
        f"On the three in-sample cubes it is also below {c5.IN_SAMPLE_BELOW:.2f}"
        in flat
    )
    # P2: the threshold, and the estimate it is set under
    assert (
        f"The median factor over finding 91's coverage is at least {c5.COVERAGE_FACTOR} in each set"
        in flat
    )
    med = statistics.median(factor)
    power = math.log(med) / math.log(1 / seed256)
    est = (1 / seed512) ** power
    assert (
        f"Finding 97's median factor, {med:.2f}, is about the {power:.2f}th power"
        in flat
    )
    assert (
        f"gain in seedable volume, 1/{seed256:.3f}" in flat
        and f"1/{seed512:.3f}, gives about {est:.2f}" in flat
    )
    assert est > c5.COVERAGE_FACTOR
    reach = [rows[c]["reachable_share"] for c in c5.ALL_CUBES]
    assert (
        f"{span(reach)} of a 512³ cube's ground-truth length already lies on fibers a seed can reach"
        in flat
    )
    # P3: finding 91's and finding 94's ranking
    ratio2 = {
        c: rep["neural_rows"][c][PEN] / rep["comparators"][c]["tracer"][PEN]
        for c in c5.ALL_CUBES
    }
    assert all(ratio2[c] > 1 for c in c5.S3_CUBES) and all(
        ratio2[c] < 1 for c in c5.S5_CUBES
    )
    assert all(
        t94["rows_neural"][c][PEN] > t94["rows_tracer"][c][PEN] for c in c5.ALL_CUBES
    )
    s5 = [ratio2[c] for c in c5.S5_CUBES]
    assert (
        f"it scores {span(s5, 2)} of ours, so it would need {1 / max(s5):.1f}–{1 / min(s5):.1f}× to overtake"
        in flat
    )
    # P4
    s3 = [rows[c]["no_heading_share"] for c in c5.S3_CUBES]
    s5in = [rows[c]["no_heading_share"] for c in c5.S5_CUBES]
    assert (
        f"Scroll 3 dropped {span(s3)}, near Scroll 5's in-sample 512³ cubes ({span(s5in)})"
        in flat
    )
    assert (
        f"below {c5.P4_BELOW:.2f} on at least six of the eight" in flat
        and c5.P4_AT_LEAST == 6
    )
    # the design
    lo, hi = c5.box_grid()
    assert f"`{lo},{lo},{lo},{hi},{hi},{hi}` in the padded trace grid" in flat
    assert f"({(c5.SIZE + 2 * c5.MARGIN) // 2}³ at level 1)" in flat
    assert f"re-run on the 512³ cube `{c5.SMOKE}`" in flat
    secs = []
    for c in c5.ALL_CUBES:
        tiles = cc.T / "run" / c / "tiles.jsonl"
        if not tiles.exists():
            pytest.skip("finding 91's run records are not on this machine")
        secs.append(
            sum(
                json.loads(line)["seconds"]
                for line in tiles.read_text().splitlines()
                if line.strip()
            )
        )
    assert (
        f"Finding 91's 512³ runs took {min(secs) / 60:.1f}–{max(secs) / 60:.1f} minutes each"
        in flat
    )
