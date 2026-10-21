"""The exporter copies the benchmark report's floors into ScrollGT's meta.json, so they must be the current scorer's,
on the probability volume and skeleton the export ships. The default report predates the scorer's October changes."""

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


def _cube(src, stem, value=0.25):
    np.save(src / f"{stem}_fiberprob.npy", np.full((2, 2, 2), value, np.float32))
    (src / f"{stem}.nml").write_text(f"<things><!-- {stem} --></things>")


def _bench(src, stems):
    row = {"scoring_version": SCORING_VERSION, "erl": 1.0}
    cubes = {
        stem: {
            "rows": {"oracle": dict(row), "floor_connected_components": dict(row)},
            "provenance": {
                "scoring_version": SCORING_VERSION,
                "probability_sha256": file_sha256(src / f"{stem}_fiberprob.npy"),
                "skeleton_sha256": file_sha256(src / f"{stem}.nml"),
                "tolerance": 2.0,
                "mask_threshold": 0.5,
            },
        }
        for stem in stems
    }
    return {"tolerance": 2.0, "scoring_version": SCORING_VERSION, "cubes": cubes}


@pytest.fixture
def src(tmp_path, monkeypatch):
    monkeypatch.setattr(eft, "SRC", tmp_path)
    _cube(tmp_path, STEM)
    return tmp_path


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


def test_a_current_report_on_the_shipped_files_passes(src):
    assert eft.bench_problems(_bench(src, [STEM]), STEM) == []


@pytest.mark.parametrize(
    "change, expected",
    [
        (lambda b, c: b.update(scoring_version=4), "report scoring_version 4"),
        (lambda b, c: c["rows"]["oracle"].update(scoring_version=4), "rows not scored"),
        (lambda b, c: c["rows"]["oracle"].pop("scoring_version"), "['oracle']"),
        (lambda b, c: c.pop("provenance"), "no provenance"),
        (
            lambda b, c: c["provenance"].update(scoring_version=4),
            "provenance scoring_version 4",
        ),
        (
            lambda b, c: c["provenance"].update(tolerance=4.0),
            "provenance tolerance 4.0",
        ),
        (lambda b, c: c["provenance"].update(mask_threshold=0.4), "mask_threshold 0.4"),
        (lambda b, c: b["cubes"].pop(STEM), "not in the benchmark report"),
    ],
)
def test_each_mismatch_is_named(src, change, expected):
    bench = _bench(src, [STEM])
    change(bench, bench["cubes"][STEM])
    problems = eft.bench_problems(bench, STEM)
    assert len(problems) == 1 and expected in problems[0], problems


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


def test_main_refuses_before_writing_any_cube(src, tmp_path, monkeypatch):
    for stem in eft.CUBES:
        _cube(src, stem)
    bench = _bench(src, eft.CUBES)
    bench["cubes"][eft.CUBES[-1]]["provenance"]["mask_threshold"] = 0.4
    path = tmp_path / "bench.json"
    path.write_text(json.dumps(bench))
    exported = []
    monkeypatch.setattr(eft, "export", lambda stem, out, b: exported.append(stem))
    argv = ["eft", "--out-root", str(tmp_path / "out"), "--bench", str(path)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit, match=f"{eft.CUBES[-1]}: provenance mask_threshold"):
        eft.main()
    assert exported == []
    bench["cubes"][eft.CUBES[-1]]["provenance"]["mask_threshold"] = 0.5
    path.write_text(json.dumps(bench))
    eft.main()
    assert exported == eft.CUBES
