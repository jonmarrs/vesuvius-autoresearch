"""Synthetic patch-control datasets must publish exactly the selected inputs."""

import json
import os
import random
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from scripts import (
    build_filtered_patch_dataset as filtered,
    build_stripmatch_dataset as strip,
    patch_dataset_artifacts as artifacts,
)


@pytest.fixture
def world(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "source"
    patches = source / "verified_patches"
    patches.mkdir(parents=True)
    (source / "config.json").write_text('{"synthetic": true}')
    rows = []
    for pid, fraction in (("a", 0.95), ("b", 0.95), ("c", 0.4), ("d", 0.2)):
        path = patches / pid
        path.mkdir()
        (path / "meta.json").write_text(
            json.dumps({"bbox": [[5644, 4621, 0], [5654, 4631, 1]]})
        )
        rows.append({"id": pid, "fraction": fraction, "total_area": 100})
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps({"patches": rows}))
    bootstrap = tmp_path / "bootstrap" / "verified_patches"
    bootstrap.mkdir(parents=True)
    for pid in ("a", "b"):
        (bootstrap / pid).symlink_to(patches / pid, target_is_directory=True)
    return tmp_path, source, reference, bootstrap.parent


def invoke(monkeypatch, module, *arguments):
    monkeypatch.setattr(sys, "argv", ["builder", *map(str, arguments)])
    try:
        return module.main()
    except SystemExit as exc:
        return exc.code


def test_relative_source_links_resolve_after_publication(world, monkeypatch):
    root, _, _, _ = world
    assert (
        invoke(
            monkeypatch,
            filtered,
            "--source",
            "source",
            "--satisfied",
            "reference.json",
            "--out",
            "output",
            "--mode",
            "bootstrap",
        )
        == 0
    )
    assert (root / "output/config.json").read_text() == '{"synthetic": true}'
    assert (root / "output/verified_patches/a/meta.json").is_file()


def test_stripmatch_refuses_to_merge_with_an_existing_selection(world, monkeypatch):
    root, source, reference, bootstrap = world
    output = root / "output"
    stale = output / "verified_patches" / "stale"
    stale.mkdir(parents=True)
    status = invoke(
        monkeypatch,
        strip,
        "--full",
        source,
        "--reference",
        reference,
        "--bootstrap",
        bootstrap,
        "--out",
        output,
    )
    assert status != 0
    assert list((output / "verified_patches").iterdir()) == [stale]


def test_failed_link_creation_leaves_no_published_dataset(world, monkeypatch):
    root, source, reference, _ = world
    original = os.symlink
    calls = 0

    def fail_after_first(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise OSError("injected link failure")
        return original(*args, **kwargs)

    monkeypatch.setattr(os, "symlink", fail_after_first)
    try:
        invoke(
            monkeypatch,
            filtered,
            "--source",
            source,
            "--satisfied",
            reference,
            "--out",
            root / "output",
            "--mode",
            "bootstrap",
        )
    except OSError:
        pass
    assert not (root / "output").exists()


def build(world, module, monkeypatch, *extra, output=None):
    root, source, reference, bootstrap = world
    output = root / "output" if output is None else output
    arguments = (
        ["--source", source, "--satisfied", reference, "--mode", "random"]
        if module is filtered
        else ["--full", source, "--reference", reference, "--bootstrap", bootstrap]
    )
    return invoke(monkeypatch, module, *arguments, "--out", output, *extra)


@pytest.mark.parametrize("module", [filtered, strip])
def test_complete_manifest_matches_exact_published_selection(
    world, monkeypatch, module
):
    root, source, reference, _ = world
    assert build(world, module, monkeypatch) == 0
    manifest = json.loads((root / "output" / artifacts.MANIFEST).read_text())
    ids = sorted(p.name for p in (root / "output/verified_patches").iterdir())
    assert manifest["selected_ids"] == ids
    assert manifest["selected_ids_sha256"] == artifacts.fingerprint(ids)
    assert manifest["selected_count"] == len(ids) == 2
    assert manifest["selected_area"] == manifest["bootstrap_target_area"] == 200
    assert manifest["source"] == str(source.resolve())
    assert (
        manifest["reference"]["sha256"]
        == artifacts.Snapshot.read(
            reference, artifacts.MAX_REFERENCE_BYTES
        ).provenance()["sha256"]
    )
    for pid in ids:
        path = root / "output/verified_patches" / pid
        assert path.is_symlink() and path.resolve() == source / "verified_patches" / pid
        assert Path(os.readlink(path)).is_absolute()
    assert not list(root.glob(".output-*"))


def test_random_arm_preserves_the_original_seeded_area_draw(world, monkeypatch):
    assert build(world, filtered, monkeypatch, "--seed", "7") == 0
    pool = ["a", "b", "c", "d"]
    random.Random(7).shuffle(pool)
    manifest = json.loads((world[0] / "output" / artifacts.MANIFEST).read_text())
    assert manifest["selected_ids"] == sorted(pool[:2])


def test_strip_profile_is_independent_of_id_iteration_order():
    area = {"a": 1e16, "b": 1.0, "c": 1.0}
    weight = dict.fromkeys(area, 0.5)
    assert strip.profile(["a", "b", "c"], area, weight) == strip.profile(
        ["c", "b", "a"], area, weight
    )


def test_manifest_metadata_cannot_replace_selection_facts(world):
    root, source, _, _ = world
    links = artifacts.dataset_links(source, ["a"])
    with pytest.raises(ValueError, match="overwrite dataset facts"):
        artifacts.publish_dataset(
            links,
            root / "output",
            ["a"],
            {"selected_ids": ["wrong"]},
            verify=lambda: None,
        )
    assert not (root / "output").exists()


@pytest.mark.parametrize(
    "invalid", ["duplicate_fields", "reference_bytes", "patch_count", "geometry_bytes"]
)
def test_json_contract_budgets_fail_before_publication(world, monkeypatch, invalid):
    root, _, reference, _ = world
    module: ModuleType = filtered
    if invalid == "duplicate_fields":
        reference.write_text('{"patches": [], "patches": []}')
    elif invalid == "reference_bytes":
        monkeypatch.setattr(artifacts, "MAX_REFERENCE_BYTES", 10)
    elif invalid == "patch_count":
        monkeypatch.setattr(artifacts, "MAX_PATCHES", 3)
    else:
        module = strip
        monkeypatch.setattr(artifacts, "MAX_META_BYTES", 10)
    assert build(world, module, monkeypatch) != 0
    assert not (root / "output").exists()


@pytest.mark.parametrize("module", [filtered, strip])
@pytest.mark.parametrize(
    "kind",
    [
        "inside_source",
        "broken_output",
        "external_auxiliary",
        "external_patch_container",
    ],
)
def test_unsafe_destinations_preserve_inputs(world, monkeypatch, module, kind):
    root, source, _, _ = world
    output = root / "output"
    if kind == "inside_source":
        output = source / "new_selection"
    elif kind == "broken_output":
        output.symlink_to(root / "missing")
    elif kind == "external_patch_container":
        container = root / "patch_container"
        (source / "verified_patches").rename(container)
        (source / "verified_patches").symlink_to(container, target_is_directory=True)
        output = container / "new_selection"
    else:
        auxiliary = root / "auxiliary"
        auxiliary.mkdir()
        (source / "extra").symlink_to(auxiliary, target_is_directory=True)
        output = auxiliary / "new_selection"
    assert build(world, module, monkeypatch, output=output) != 0
    assert not output.exists()
    assert (source / "config.json").read_text() == '{"synthetic": true}'


def test_external_bootstrap_container_is_an_input(world, monkeypatch):
    root, _, _, bootstrap = world
    container = root / "bootstrap_container"
    (bootstrap / "verified_patches").rename(container)
    (bootstrap / "verified_patches").symlink_to(container, target_is_directory=True)
    output = container / "new_selection"
    assert build(world, strip, monkeypatch, output=output) != 0
    assert not output.exists()


@pytest.mark.parametrize(
    "change", ["duplicate", "unsafe_id", "nan", "negative_area", "empty"]
)
def test_invalid_reference_never_publishes(world, monkeypatch, change):
    root, _, reference, _ = world
    data = json.loads(reference.read_text())
    if change == "duplicate":
        data["patches"].append(data["patches"][0])
    elif change == "unsafe_id":
        data["patches"][0]["id"] = "../escape"
    elif change == "nan":
        data["patches"][0]["fraction"] = float("nan")
    elif change == "negative_area":
        data["patches"][0]["total_area"] = -1
    else:
        data["patches"] = []
    reference.write_text(json.dumps(data))
    assert build(world, filtered, monkeypatch) != 0
    assert not (root / "output").exists()


@pytest.mark.parametrize(
    "change",
    ["missing_geometry", "reversed_bbox", "unknown_bootstrap", "empty_bootstrap"],
)
def test_stripmatch_requires_complete_input_population(world, monkeypatch, change):
    root, source, _, bootstrap = world
    path = source / "verified_patches/d/meta.json"
    if change == "missing_geometry":
        path.unlink()
    elif change == "reversed_bbox":
        path.write_text('{"bbox": [[10, 10, 1], [0, 0, 0]]}')
    elif change == "unknown_bootstrap":
        (bootstrap / "verified_patches/unknown").mkdir()
    else:
        for item in (bootstrap / "verified_patches").iterdir():
            item.unlink()
    assert build(world, strip, monkeypatch) != 0
    assert not (root / "output").exists()


@pytest.mark.parametrize("changed", ["reference", "geometry", "bootstrap"])
def test_input_drift_aborts_staged_publication(world, monkeypatch, changed):
    root, source, reference, bootstrap = world
    original = os.symlink
    modified = False

    def mutate(*args, **kwargs):
        nonlocal modified
        result = original(*args, **kwargs)
        if not modified:
            modified = True
            if changed == "reference":
                reference.write_text(reference.read_text() + "\n")
            elif changed == "geometry":
                path = source / "verified_patches/d/meta.json"
                path.write_text(path.read_text() + "\n")
            else:
                (bootstrap / "verified_patches/a").unlink()
        return result

    monkeypatch.setattr(os, "symlink", mutate)
    assert build(world, strip, monkeypatch) != 0
    assert not (root / "output").exists()
    assert not list(root.glob(".output-*"))


def test_appearing_destination_is_preserved(world, monkeypatch):
    root = world[0]
    original = os.symlink

    def appear(*args, **kwargs):
        result = original(*args, **kwargs)
        (root / "output").mkdir(exist_ok=True)
        (root / "output/sentinel").write_text("other writer")
        return result

    monkeypatch.setattr(os, "symlink", appear)
    assert build(world, filtered, monkeypatch) != 0
    assert (root / "output/sentinel").read_text() == "other writer"
    assert not (root / "output/verified_patches").exists()


@pytest.mark.parametrize("count", ["-1", "1", "1001"])
def test_stability_requires_at_least_two_bounded_draws(world, monkeypatch, count):
    assert build(world, strip, monkeypatch, "--stability", count) != 0
    assert not (world[0] / "output").exists()


def test_stability_reports_without_building_a_dataset(world, monkeypatch, capsys):
    assert build(world, strip, monkeypatch, "--stability", "2") == 0
    assert not (world[0] / "output").exists()
    assert "Draw overlap with the first" in capsys.readouterr().out


@pytest.mark.parametrize("module", [filtered, strip])
def test_real_cli_runs_from_another_directory(world, module):
    root, source, reference, bootstrap = world
    elsewhere = root / "caller"
    elsewhere.mkdir()
    arguments = (
        ["--source", source, "--satisfied", reference, "--mode", "bootstrap"]
        if module is filtered
        else ["--full", source, "--reference", reference, "--bootstrap", bootstrap]
    )
    result = subprocess.run(
        [
            sys.executable,
            module.__file__,
            *map(str, arguments),
            "--out",
            str(root / "output"),
        ],
        cwd=elsewhere,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert (root / "output" / artifacts.MANIFEST).is_file()
