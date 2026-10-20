"""scripts/neural_tracer_pitch_funnel.py: per-tile counters summed from a run's tiles.jsonl, and the ratios that say
where the pitch-matched run lost its fibers."""

import json
import math
import statistics
import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import neural_tracer_pitch_funnel as fn  # noqa: E402


def _tiles(path: Path, lines: list[dict]) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    (path / "tiles.jsonl").write_text("".join(json.dumps(d) + "\n" for d in lines))
    return path


def _line(tile, **counts):
    return {"tile": tile, **{k: counts.get(k, 0) for k in fn.COUNTERS}}


def test_a_redone_tile_counts_once_by_its_last_line(tmp_path):
    """villa's volume tracer appends a line per finished tile; a resumed run can finish a tile twice."""
    run = _tiles(
        tmp_path / "run",
        [
            _line("a", dots=10, traced=2, traced_vox=100),
            _line("b", dots=5, traced=1, traced_vox=40),
            _line("a", dots=12, traced=3, traced_vox=150),
        ],
    )
    t = fn.tile_totals(run)
    assert (t["dots"], t["traced"], t["traced_vox"]) == (17, 4, 190)


def test_physical_ratios_scale_grid_voxels_by_the_pitch(tmp_path):
    """A pitch-run grid voxel is r times longer, so the same voxel count is r times more fiber."""
    native = _line(
        "all",
        dots=100,
        no_heading=30,
        owned_dots=40,
        traced=10,
        traced_vox=600,
        kept_vox=450,
    )
    pitch = _line(
        "all",
        dots=50,
        no_heading=25,
        owned_dots=10,
        traced=5,
        traced_vox=300,
        kept_vox=225,
    )
    f = fn.funnel(native, pitch, r=1.25)
    assert f["dots"] == 0.5 and f["traces"] == 0.5
    assert f["no_heading_share"] == (0.3, 0.5) and f["owned_share"] == (0.4, 0.2)
    assert f["grid_vox_per_trace"] == (60.0, 60.0)
    assert math.isclose(f["physical_traced"], 0.625) and math.isclose(
        f["physical_kept"], 0.625
    )
    assert f["kept_share"] == (0.75, 0.75)


F = json.loads((ROOT / "reports/neural_tracer_pitch_funnel.json").read_text())
REPORT = " ".join((ROOT / "reports/neural_tracer_pitch.md").read_text().split())
CUBES = F["cubes"]


def _pct(x: float) -> str:
    return f"{round(100 * x)}%"


def test_the_json_covers_every_cube_and_its_rows_are_finding_92s():
    rows = json.loads((ROOT / "reports/neural_tracer_pitch.json").read_text())
    assert sorted(CUBES) == sorted(rows["pitch_rows"]) and len(CUBES) == 21
    assert F["ratio"] == fn.pa.R
    for c, v in CUBES.items():
        assert v["funnel"] == json.loads(
            json.dumps(fn.funnel(v["native"], v["pitch"]))
        )  # tuples are lists in JSON
        assert (
            v["coverage_ratio"]
            == rows["pitch_rows"][c]["coverage"] / rows["native_rows"][c]["coverage"]
        )


def test_the_funnel_table_quotes_the_medians():
    s = F["summary"]
    for line in (
        f"| seed dots, relative to native | 1 | {s['dots']:.2f} |",
        f"| dots skipped for having no CT heading | {_pct(s['no_heading_share'][0])} | {_pct(s['no_heading_share'][1])} |",
        f"| dots skipped for lying on a written fiber | {_pct(s['owned_share'][0])} | {_pct(s['owned_share'][1])} |",
        f"| traces, relative to native | 1 | {s['traces']:.2f} |",
        f"| grid voxels per trace | {s['grid_vox_per_trace'][0]:.0f} | {s['grid_vox_per_trace'][1]:.0f} |",
        f"| physical length traced, relative to native | 1 | {s['physical_traced']:.2f} |",
        f"| share of traced length written | {s['kept_share'][0]:.2f} | {s['kept_share'][1]:.2f} |",
    ):
        assert line in REPORT, line


def test_it_loses_fibers_it_never_starts():
    s = F["summary"]
    assert all(
        v["funnel"]["traces"] < 1 and v["funnel"]["dots"] < 1 for v in CUBES.values()
    )
    # "about as many grid voxels ... so about 21% more physical length"
    a, b = s["grid_vox_per_trace"]
    assert abs(b / a - 1) < 0.02 and round(100 * (fn.pa.R - 1)) == 21
    assert (
        abs(s["kept_share"][1] - s["kept_share"][0]) < 0.02
    )  # "the same share of what it traces"
    cov = [CUBES[c]["coverage_ratio"] for c in sorted(CUBES)]
    kept = [CUBES[c]["funnel"]["physical_kept"] for c in sorted(CUBES)]
    r = np.corrcoef(cov, kept)[0, 1]
    assert (
        f"It runs {s['traces']:.2f} times as many traces, fewer on all 21 cubes"
        in REPORT
        and f"The physical length it writes falls to {s['physical_kept']:.2f} of native"
        in REPORT
        and f"(Pearson r {r:.2f})" in REPORT
    )


def test_its_traces_are_fewer_because_its_seed_dots_are():
    s, g = F["summary"], F["groups"]
    by_group = {
        k: statistics.median(CUBES[c]["funnel"]["dots"] for c in cubes)
        for k, cubes in g.items()
    }
    assert by_group["s3"] == min(by_group.values())
    assert (
        f"It finds {s['dots']:.2f} times as many, fewer on all 21 cubes, and Scroll 3 loses the most "
        f"({by_group['s3']:.2f})" in REPORT
    )
    assert (
        f"turns away more of them ({_pct(s['no_heading_share'][1])} against {_pct(s['no_heading_share'][0])})"
        in REPORT
    )
    vol = [(fn.pa.grid_size(c) / (int(c.rsplit("_", 1)[1]) / 2)) ** 3 for c in ("s1_00497_01497_03997_256",
                                                                               "s3_00994_00494_01994_512")]  # fmt: skip
    assert (
        f"the trace grid has {vol[0]:.2f} (256³ cubes) or {vol[1]:.2f} (512³) times the voxels"
        in REPORT
    )
    assert "divided by 1.21" in REPORT and f"{fn.pa.R:.2f}" == "1.21"


def test_the_native_run_is_the_one_off_its_defaults_design():
    """grid_scale 2 at 9.6 um is villa's documented Paris 4 trace grid; natively the grid is finer by r."""
    g = fn.pa.SETTINGS["grid_scale"]
    assert (
        g == 2
        and f"{g * fn.pa.TO_UM:.1f}" == "19.2"
        and f"{g * fn.pa.rcp.FROM_UM:.1f}" == "15.8"
    )
    villa_doc = "8 base voxels = 19.2 um"  # tracing/volume.py at villa ccb431818, module docstring
    assert f'the grid villa\'s docstring gives for Paris 4 ("{villa_doc}")' in REPORT
    assert (
        f"Natively it is 15.8 µm, so finding 91's run seeded about {fn.pa.R:.2f} times more densely per micrometre"
        in REPORT
    )
