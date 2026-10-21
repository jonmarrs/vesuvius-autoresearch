"""The exporter copies the benchmark report's floors into new ScrollGT-style targets, so they must be the current
scorer's, on the probability volume and skeleton the export ships. The default report predates the scorer's October
changes. ScrollGT maintains its published targets, which hold what the export does not write, so an existing target
is never written over, and a refused export leaves the output directory as it was."""

import json
import pathlib
import sys

import numpy as np
import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

import export_fiber_targets as eft  # noqa: E402

from vesuvius_autoresearch.fibers.provenance import (  # noqa: E402
    SCORING_VERSION,
    file_sha256,
)

STEM = eft.CUBES[0]
PROVENANCE_KEYS = (
    "scoring_version",
    "probability_sha256",
    "skeleton_sha256",
    "tolerance",
    "step",
    "restrict_to_bounds",
    "mask_threshold",
)


def _cube(src, stem, value=0.25):
    np.save(src / f"{stem}_fiberprob.npy", np.full((2, 2, 2), value, np.float32))
    (src / f"{stem}.nml").write_text(f"<things><!-- {stem} --></things>")


def _bench(src, stems, tolerance=2.0):
    """A report as `bench_cli floors --all-cubes` writes it with this checkout."""
    row = {"scoring_version": SCORING_VERSION, "tolerance": tolerance, "erl": 1.0}
    cubes = {
        stem: {
            "rows": {"oracle": dict(row), "floor_connected_components": dict(row)},
            "provenance": {
                "scoring_version": SCORING_VERSION,
                "probability_sha256": file_sha256(src / f"{stem}_fiberprob.npy"),
                "skeleton_sha256": file_sha256(src / f"{stem}.nml"),
                "tolerance": tolerance,
                "step": 0.5,
                "restrict_to_bounds": True,
                "mask_threshold": 0.5,
            },
        }
        for stem in stems
    }
    return {"tolerance": tolerance, "scoring_version": SCORING_VERSION, "cubes": cubes}


@pytest.fixture
def src(tmp_path, monkeypatch):
    src = tmp_path / "src"
    src.mkdir()
    monkeypatch.setattr(eft, "SRC", src)
    _cube(src, STEM)
    return src


def test_the_committed_report_is_refused_on_every_cube():
    bench = json.loads(
        (REPO_ROOT / "reports/fiber_benchmark_all_cubes.json").read_text()
    )
    for stem in eft.CUBES:
        problems = eft.bench_problems(bench, stem)
        assert problems[0] == f"report scoring_version None, not {SCORING_VERSION}", (
            stem
        )
        assert problems[-1] == "no provenance", stem


@pytest.mark.parametrize("tolerance", [2.0, 4.0])
def test_a_current_report_on_the_shipped_files_passes(src, tolerance):
    assert eft.bench_problems(_bench(src, [STEM], tolerance), STEM) == []


def _old_tracer_row(b, c):
    c["rows"]["tracer_strict_relink"] = {"scoring_version": 4, "tolerance": 2.0}


@pytest.mark.parametrize(
    "change, expected",
    [
        (lambda b, c: b.update(scoring_version=4), "report scoring_version 4"),
        (
            lambda b, c: c["rows"]["floor_connected_components"].update(
                scoring_version=4
            ),
            "rows not scored at version 5: ['floor_connected_components']",
        ),
        (_old_tracer_row, "rows not scored at version 5: ['tracer_strict_relink']"),
        (
            lambda b, c: c["rows"]["oracle"].pop("scoring_version"),
            "rows not scored at version 5: ['oracle']",
        ),
        (
            lambda b, c: c["rows"]["floor_connected_components"].update(tolerance=9.0),
            "rows not at the report's tolerance: ['floor_connected_components']",
        ),
        (lambda b, c: c["rows"].pop("oracle"), "no oracle row"),
        (lambda b, c: c.pop("provenance"), "no provenance"),
        (lambda b, c: c.update(provenance={}), "no provenance"),
        (
            lambda b, c: c["provenance"].update(scoring_version=4),
            "provenance scoring_version 4",
        ),
        (
            lambda b, c: c["provenance"].update(tolerance=4.0),
            "provenance tolerance 4.0",
        ),
        (lambda b, c: c["provenance"].update(step=1.0), "provenance step 1.0"),
        (
            lambda b, c: c["provenance"].update(restrict_to_bounds=False),
            "provenance restrict_to_bounds False",
        ),
        (
            lambda b, c: c["provenance"].update(mask_threshold=0.4),
            "mask_threshold 0.4",
        ),
        (lambda b, c: b["cubes"].pop(STEM), "not in the benchmark report"),
    ],
)
def test_each_mismatch_is_named(src, change, expected):
    bench = _bench(src, [STEM])
    change(bench, bench["cubes"][STEM])
    problems = eft.bench_problems(bench, STEM)
    assert len(problems) == 1 and expected in problems[0], problems


@pytest.mark.parametrize("key", PROVENANCE_KEYS)
def test_a_provenance_without_a_field_is_refused(src, key):
    bench = _bench(src, [STEM])
    del bench["cubes"][STEM]["provenance"][key]
    problems = eft.bench_problems(bench, STEM)
    assert len(problems) == 1 and problems[0].startswith(f"provenance {key} None, ")


def test_floors_scored_on_another_volume_or_skeleton_are_refused(src):
    bench = _bench(src, [STEM])
    _cube(
        src, STEM, value=0.75
    )  # the probability volume was recomputed after the floors
    assert eft.bench_problems(bench, STEM) == [
        f"provenance probability_sha256 {bench['cubes'][STEM]['provenance']['probability_sha256']!r}, "
        f"this export's {file_sha256(src / f'{STEM}_fiberprob.npy')!r}"
    ]
    bench = _bench(src, [STEM])
    (src / f"{STEM}.nml").write_text("<things></things>")
    assert [p.split()[1] for p in eft.bench_problems(bench, STEM)] == [
        "skeleton_sha256"
    ]


def test_a_missing_local_file_is_named_not_a_traceback(src):
    bench = _bench(src, [STEM])
    (src / f"{STEM}.nml").unlink()
    assert eft.bench_problems(bench, STEM) == [f"missing {src / f'{STEM}.nml'}"]


@pytest.fixture
def run_main(src, tmp_path, monkeypatch):
    """main() on a report covering every cube, with export stubbed to write each cube's directory where main points
    it, and to fail on the cubes in `fail`."""
    for stem in eft.CUBES:
        _cube(src, stem)
    out = tmp_path / "out"
    exported = []

    def run(bench, fail=()):
        path = tmp_path / "bench.json"
        path.write_text(json.dumps(bench))

        def export(stem, root, b):
            assert root.parent == out  # a staging directory inside the output
            if stem in fail:
                raise SystemExit(f"{stem}: landing rate")
            (root / f"fibers_{stem}").mkdir()
            exported.append(stem)

        monkeypatch.setattr(eft, "export", export)
        monkeypatch.setattr(
            sys, "argv", ["eft", "--out-root", str(out), "--bench", str(path)]
        )
        eft.main()

    return run, out, exported, lambda: _bench(src, eft.CUBES)


def test_main_exports_every_cube_into_place(run_main):
    run, out, exported, bench = run_main
    run(bench())
    assert exported == eft.CUBES
    assert sorted(p.name for p in out.iterdir()) == sorted(
        f"fibers_{stem}" for stem in eft.CUBES
    )


def test_main_refuses_an_existing_target_before_reading_the_report(run_main):
    run, out, exported, _ = run_main
    (out / f"fibers_{eft.CUBES[3]}").mkdir(parents=True)
    with pytest.raises(SystemExit, match=f"already has targets for {eft.CUBES[3]}"):
        run({"not": "a report"})
    assert exported == []
    assert [p.name for p in out.iterdir()] == [f"fibers_{eft.CUBES[3]}"]


@pytest.mark.parametrize("last_cube", ["threshold", "missing"])
def test_main_refuses_a_report_before_exporting_any_cube(run_main, last_cube):
    run, out, exported, bench = run_main
    b = bench()
    if last_cube == "threshold":
        b["cubes"][eft.CUBES[-1]]["provenance"]["mask_threshold"] = 0.4
    else:
        del b["cubes"][eft.CUBES[-1]]
    with pytest.raises(SystemExit, match=f"{eft.CUBES[-1]}: "):
        run(b)
    assert exported == [] and not out.exists()


def test_a_cube_export_refuses_leaves_the_output_as_it_was(run_main):
    run, out, exported, bench = run_main
    with pytest.raises(SystemExit, match="landing rate"):
        run(bench(), fail={eft.CUBES[5]})
    assert exported == eft.CUBES[:5]
    assert (
        list(out.iterdir()) == []
    )  # neither the five written cubes nor the staging directory
