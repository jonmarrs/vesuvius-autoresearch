"""Input checks must fail closed and separate diagnostics from study verdicts."""

import json
import subprocess
import sys

import pytest

from scripts import (
    check_patch_selection as selection,
    check_patch_spatial_balance as spatial,
)


@pytest.fixture
def world(tmp_path):
    reference = tmp_path / "reference.json"
    rows = [{"id": str(i), "fraction": 0.95, "total_area": 100} for i in range(20)]
    reference.write_text(json.dumps({"patches": rows}))

    def dataset(name, ids):
        root = tmp_path / name
        for pid in ids:
            patch = root / "verified_patches" / str(pid)
            patch.mkdir(parents=True)
            x = 100 + int(pid) * 20
            (patch / "meta.json").write_text(
                json.dumps({"bbox": [[x, 0, 0], [x + 10, 10, 10]]})
            )
        (root / "verified_patches").mkdir(parents=True, exist_ok=True)
        return root

    return tmp_path, reference, rows, dataset


def test_dangling_patch_links_cannot_pass_selection(world):
    root, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [])
    for pid in ("0", "1"):
        (rand / "verified_patches" / pid).symlink_to(root / "missing" / pid)
    failures, _ = selection.check(reference, boot, rand, 0.9)
    assert failures


def test_nonfinite_area_cannot_bypass_the_match_check(world):
    _, reference, rows, dataset = world
    for row in rows:
        row["total_area"] = float("nan")
    reference.write_text(json.dumps({"patches": rows}))
    failures, _ = selection.check(
        reference, dataset("boot", [0, 1]), dataset("rand", [2, 3]), 0.9
    )
    assert failures


def test_single_patch_sets_have_an_undefined_quartile(world):
    _, reference, _, dataset = world
    failures, stats = selection.check(
        reference, dataset("boot", [0]), dataset("rand", [1]), 0.9
    )
    assert not failures
    assert stats["BOOTSTRAP"]["p25"] is None


def test_empty_arm_returns_a_failed_check(world):
    _, reference, _, dataset = world
    failures, stats = selection.check(
        reference, dataset("boot", []), dataset("rand", [1, 2]), 0.9
    )
    assert failures
    assert stats["BOOTSTRAP"]["n"] == 0


def test_small_populations_still_define_every_requested_band():
    extent = {"a": (0.0, 10.0), "b": (10.0, 20.0)}
    area = {"a": 1.0, "b": 1.0}
    edges = spatial.radial_bands(extent, area, n_bands=10)
    assert len(edges) == 9
    share, _ = spatial.area_share_by_band(set(extent), extent, edges, area)
    assert sum(share) == pytest.approx(1)


def test_spatial_text_uses_the_actual_global_area_gap(world, monkeypatch, capsys):
    _, reference, _, dataset = world
    boot, rand = dataset("boot", range(10)), dataset("rand", range(10, 15))
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "spatial",
            "--reference",
            str(reference),
            "--bootstrap",
            str(boot),
            "--random",
            str(rand),
        ],
    )
    assert spatial.main() == 0
    assert "global area gap for the same build: 25.00 points" in capsys.readouterr().out


@pytest.mark.parametrize("module", [selection, spatial])
@pytest.mark.parametrize("broken", [False, True])
def test_actual_json_cli_has_one_report_and_matching_exit_status(world, module, broken):
    root, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [2, 3])
    if broken:
        (rand / "verified_patches/2/meta.json").unlink()
        (rand / "verified_patches/2").rmdir()
        (rand / "verified_patches/2").symlink_to(root / "missing")
    caller = root / "caller"
    caller.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            module.__file__,
            "--reference",
            str(reference),
            "--bootstrap",
            str(boot),
            "--random",
            str(rand),
            "--json",
        ],
        cwd=caller,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == (1 if broken else 0), result.stderr
    report = json.loads(result.stdout)
    assert report["status"] == (
        "FAIL" if broken else "PASS" if module is selection else "MEASURED"
    )
    assert not result.stderr
    assert not report["payload_contents_hashed"]
    if module is spatial:
        assert report["balance_verdict"] == "not_assessed"
        assert not report["winding_calibration_verified"]


@pytest.mark.parametrize(
    "invalid", ["duplicate_ids", "duplicate_fields", "nonfinite", "negative_area"]
)
@pytest.mark.parametrize("module", [selection, spatial])
def test_bad_reference_produces_finite_failure_report(world, module, invalid):
    _, reference, rows, dataset = world
    if invalid == "duplicate_ids":
        rows.append(rows[0])
    elif invalid == "nonfinite":
        rows[0]["fraction"] = float("nan")
    elif invalid == "negative_area":
        rows[0]["total_area"] = -100
    reference.write_text(
        '{"patches": [], "patches": []}'
        if invalid == "duplicate_fields"
        else json.dumps({"patches": rows})
    )
    report = module.build_report(reference, dataset("boot", [0]), dataset("rand", [1]))
    assert report["status"] == "FAIL" and report["failures"]
    json.dumps(report, allow_nan=False)


@pytest.mark.parametrize("kind", ["missing", "conflicting", "reversed"])
def test_partial_or_conflicting_geometry_fails_closed(world, kind):
    _, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [0, 2])
    path = rand / "verified_patches/0/meta.json"
    if kind == "missing":
        path.unlink()
    else:
        path.write_text(
            json.dumps(
                {"bbox": [[1000, 0, 0], [1000 if kind == "conflicting" else 0, 10, 10]]}
            )
        )
    report = spatial.build_report(reference, boot, rand)
    assert report["status"] == "FAIL" and report["failures"]


@pytest.mark.parametrize("complete", [False, True])
def test_full_population_requires_every_scored_geometry(world, complete):
    _, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [2, 3])
    full = dataset("full", range(20) if complete else range(19))
    report = spatial.build_report(reference, boot, rand, full)
    assert report["status"] == ("MEASURED" if complete else "FAIL")
    if complete:
        assert sum(
            row["reference_population_share"] for row in report["bands"]
        ) == pytest.approx(1)
        assert report["arms"]["ALL"]["patch_count"] == 20


@pytest.mark.parametrize("changed", ["reference", "membership", "geometry"])
def test_changes_during_spatial_computation_prevent_a_measured_report(
    world, monkeypatch, changed
):
    _, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [2, 3])
    original = spatial.area_share_by_band
    modified = False

    def mutate(*args, **kwargs):
        nonlocal modified
        result = original(*args, **kwargs)
        if not modified:
            modified = True
            if changed == "reference":
                reference.write_text(reference.read_text() + "\n")
            elif changed == "geometry":
                path = boot / "verified_patches/0/meta.json"
                path.write_text(path.read_text() + "\n")
            else:
                (boot / "verified_patches/extra").mkdir()
        return result

    monkeypatch.setattr(spatial, "area_share_by_band", mutate)
    report = spatial.build_report(reference, boot, rand)
    assert report["status"] == "FAIL"
    assert "changed" in report["failures"][0]


def test_selection_rechecks_membership_after_computation(world, monkeypatch):
    _, reference, _, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [2, 3])
    original = selection.summarise
    modified = False

    def mutate(*args, **kwargs):
        nonlocal modified
        result = original(*args, **kwargs)
        if not modified:
            modified = True
            (boot / "verified_patches/extra").mkdir()
        return result

    monkeypatch.setattr(selection, "summarise", mutate)
    report = selection.build_report(reference, boot, rand)
    assert report["status"] == "FAIL"
    assert any("changed" in failure for failure in report["failures"])


def test_invalid_threshold_and_zero_area_arms_fail(world):
    _, reference, rows, dataset = world
    boot, rand = dataset("boot", [0, 1]), dataset("rand", [2, 3])
    assert (
        selection.build_report(reference, boot, rand, float("nan"))["status"] == "FAIL"
    )
    for row in rows[:4]:
        row["total_area"] = 0
    reference.write_text(json.dumps({"patches": rows}))
    report = selection.build_report(reference, boot, rand)
    assert report["status"] == "FAIL"
    assert report["statistics"]["BOOTSTRAP"]["area_weighted_mean"] is None


def test_finite_fields_with_an_overflowing_aggregate_fail_closed(world):
    _, reference, _, dataset = world
    rows = [{"id": "19", "fraction": 1.0, "total_area": sys.float_info.max}]
    rows += [{"id": str(i), "fraction": 1.0, "total_area": 1e291} for i in range(19)]
    reference.write_text(json.dumps({"patches": rows}))
    report = selection.build_report(
        reference, dataset("boot", [19]), dataset("rand", [19])
    )
    assert report["status"] == "FAIL"
    json.dumps(report, allow_nan=False)


def test_tied_midpoints_have_stable_cuts_and_point_boundaries():
    extent = {"b": (10.0, 10.0), "a": (10.0, 10.0)}
    area = {"a": 1.0, "b": 2.0}
    edges = spatial.radial_bands(extent, area)
    assert edges == [10.0] * 9
    shares, _ = spatial.area_share_by_band(["a", "b"], extent, edges, area)
    assert shares == [1.0] + [0.0] * 9


@pytest.mark.parametrize(
    "kind", ["unknown_id", "missing_cuts", "decreasing_cuts", "nonfinite_radius"]
)
def test_radial_helpers_reject_uninterpretable_populations(kind):
    extent, area, ids, edges = {"a": (0.0, 10.0)}, {"a": 1.0}, ["a"], [5.0] * 9
    if kind == "unknown_id":
        ids = ["unknown"]
    elif kind == "missing_cuts":
        edges = []
    elif kind == "decreasing_cuts":
        edges[1] = 4.0
    else:
        extent["a"] = (0.0, float("inf"))
    with pytest.raises(ValueError):
        spatial.area_share_by_band(ids, extent, edges, area)
