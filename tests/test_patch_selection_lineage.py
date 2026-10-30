"""Prepared selection records must bind the actual arms and reference bytes."""

import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from scripts import (
    build_filtered_patch_dataset as filtered,
    build_stripmatch_dataset as strip,
    check_patch_selection as selection,
    check_patch_spatial_balance as spatial,
)
from scripts.patch_dataset_artifacts import MANIFEST

MODULES = (selection, spatial)


def test_two_patch_quartile_does_not_extrapolate_outside_fraction_range():
    stats = selection.summarise(
        ["zero", "one"], {"zero": 0.0, "one": 1.0}, {"zero": 1, "one": 1}
    )
    assert stats["p25"] is None


@pytest.fixture
def prepared(tmp_path):
    full = tmp_path / "full"
    rows = []
    for pid, fraction in (("a", 0.95), ("b", 0.95), ("c", 0.4), ("d", 0.2)):
        patch = full / "verified_patches" / pid
        patch.mkdir(parents=True)
        (patch / "meta.json").write_text(
            json.dumps({"bbox": [[5644, 4621, 0], [5654, 4631, 1]]})
        )
        rows.append({"id": pid, "fraction": fraction, "total_area": 100})
    reference = tmp_path / "reference.json"
    reference.write_text(json.dumps({"patches": rows}))
    boot, control = tmp_path / "bootstrap", tmp_path / "random"
    for mode, output in (("bootstrap", boot), ("random", control)):
        assert (
            filtered.main(
                [
                    "--source",
                    str(full),
                    "--satisfied",
                    str(reference),
                    "--mode",
                    mode,
                    "--out",
                    str(output),
                ]
            )
            == 0
        )
    return tmp_path, full, reference, boot, control


def passed(module, report):
    return report["status"] == ("PASS" if module is selection else "MEASURED")


def rewrite(path, change):
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


@pytest.mark.parametrize("module", MODULES)
def test_real_builder_manifests_are_consumed_by_both_checkers(prepared, module):
    _, _, reference, boot, control = prepared
    report = module.build_report(reference, boot, control, require_manifests=True)
    assert passed(module, report), report["failures"]
    assert all(
        binding["status"] == "checked"
        for binding in report["selection_manifests"].values()
    )
    assert not report["generation_replayed"] and not report["payload_contents_hashed"]
    assert not report["scientific_validity_verified"]


@pytest.mark.parametrize("module", MODULES)
def test_changed_reference_cannot_reuse_old_selection_manifests(prepared, module):
    _, _, reference, boot, control = prepared
    rewrite(reference, lambda data: data["patches"][2].update(fraction=0.5))
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL"
    assert "reference bytes differ" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_identical_reference_bytes_at_another_path_are_accepted(prepared, module):
    root, _, reference, boot, control = prepared
    copy = root / "copied-reference.json"
    copy.write_bytes(reference.read_bytes())
    assert passed(
        module, module.build_report(copy, boot, control, require_manifests=True)
    )


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize(
    "field,value",
    [
        ("selected_ids", ["c", "d"]),
        ("selected_ids_sha256", "0" * 64),
        ("selected_count", True),
        ("selected_area", 1),
        ("status", "FAILED"),
    ],
)
def test_manifest_cannot_disagree_with_its_dataset(prepared, module, field, value):
    _, _, reference, boot, control = prepared
    rewrite(boot / MANIFEST, lambda data: data.update({field: value}))
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL" and report["failures"]


@pytest.mark.parametrize("module", MODULES)
def test_retargeted_patch_cannot_keep_the_old_source_binding(prepared, module):
    _, full, reference, boot, control = prepared
    patch = boot / "verified_patches/a"
    patch.unlink()
    patch.symlink_to(full / "verified_patches/d", target_is_directory=True)
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL"
    assert "source target differs" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_manifest_mode_cannot_relabel_a_control_as_bootstrap(prepared, module):
    _, _, reference, boot, control = prepared
    report = module.build_report(reference, control, boot)
    assert report["status"] == "FAIL"
    assert "mode" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_distinct_full_source_bindings_cannot_form_one_comparison(prepared, module):
    root, full, reference, boot, control = prepared
    other = root / "other-full"
    shutil.copytree(full, other)
    rewrite(boot / MANIFEST, lambda data: data.update(source=str(other)))
    for patch in (boot / "verified_patches").iterdir():
        patch.unlink()
        patch.symlink_to(
            other / "verified_patches" / patch.name, target_is_directory=True
        )
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL"
    assert "different full datasets" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
@pytest.mark.parametrize("alias", ["same", "root", "container"])
def test_same_physical_arm_is_not_an_independent_control(prepared, module, alias):
    root, _, reference, boot, _ = prepared
    (boot / MANIFEST).unlink()  # legacy arms still need distinct containers
    other = boot
    if alias == "root":
        other = root / "alias"
        other.symlink_to(boot, target_is_directory=True)
    elif alias == "container":
        other = root / "alias"
        other.mkdir()
        (other / "verified_patches").symlink_to(
            boot / "verified_patches", target_is_directory=True
        )
    report = module.build_report(reference, boot, other)
    assert report["status"] == "FAIL"
    assert "distinct patch containers" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_a_copy_of_the_bootstrap_links_is_not_an_independent_control(prepared, module):
    root, _, reference, boot, _ = prepared
    copy = root / "copy"
    shutil.copytree(boot, copy, symlinks=True)
    (copy / MANIFEST).unlink()  # a legacy arm: no record to name its role
    report = module.build_report(reference, boot, copy)
    assert report["status"] == "FAIL"
    assert "select the same patches" in report["failures"][0]


def test_full_dataset_may_alias_patches_the_reference_did_not_score(prepared):
    """Unscored FULL patches are outside the comparison, as the builders treat them."""
    _, full, reference, boot, control = prepared
    unscored = full / "verified_patches" / "u1"
    unscored.mkdir()
    (full / "verified_patches" / "u2").symlink_to(unscored, target_is_directory=True)
    report = spatial.build_report(
        reference, boot, control, full, require_manifests=True
    )
    assert passed(spatial, report), report["failures"]


@pytest.mark.parametrize("module", MODULES)
def test_different_ids_cannot_count_one_directory_twice(prepared, module):
    _, _, reference, boot, control = prepared
    (control / MANIFEST).unlink()
    first, second = sorted((control / "verified_patches").iterdir())
    second.unlink()
    second.symlink_to(first.resolve(), target_is_directory=True)
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL"
    assert "same directory" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_legacy_inputs_are_explicit_and_strict_mode_requires_records(prepared, module):
    _, _, reference, boot, control = prepared
    for arm in (boot, control):
        (arm / MANIFEST).unlink()
    report = module.build_report(reference, boot, control)
    assert passed(module, report)
    assert all(
        binding["status"] == "absent"
        for binding in report["selection_manifests"].values()
    )
    report = module.build_report(reference, boot, control, require_manifests=True)
    assert (
        report["status"] == "FAIL" and "manifest is required" in report["failures"][0]
    )


@pytest.mark.parametrize("module", MODULES)
def test_manifest_changes_during_computation_fail_the_result(
    prepared, module, monkeypatch
):
    _, _, reference, boot, control = prepared
    name = "summarise" if module is selection else "area_share_by_band"
    original = getattr(module, name)
    changed = False

    def mutate(*args, **kwargs):
        nonlocal changed
        result = original(*args, **kwargs)
        if not changed:
            changed = True
            path = boot / MANIFEST
            path.write_text(path.read_text() + "\n")
        return result

    monkeypatch.setattr(module, name, mutate)
    report = module.build_report(reference, boot, control)
    assert report["status"] == "FAIL"
    assert "manifests changed" in report["failures"][0]


def strip_args(full, reference, boot, output, *extra):
    return [
        "--full",
        str(full),
        "--reference",
        str(reference),
        "--bootstrap",
        str(boot),
        "--out",
        str(output),
        *extra,
    ]


def test_stripmatch_rejects_random_manifest_as_its_bootstrap(prepared):
    root, full, reference, _, control = prepared
    output = root / "strip"
    assert strip.main(strip_args(full, reference, control, output)) == 1
    assert not output.exists()


@pytest.mark.parametrize("module", MODULES)
def test_stripmatch_records_its_bootstrap_manifest_dependency(prepared, module):
    root, full, reference, boot, _ = prepared
    output = root / "strip"
    assert (
        strip.main(strip_args(full, reference, boot, output, "--require-manifests"))
        == 0
    )
    dependency = json.loads((output / MANIFEST).read_text())["bootstrap_manifest"]
    assert set(dependency) == {"status", "path", "record"}
    assert passed(
        module, module.build_report(reference, boot, output, require_manifests=True)
    )
    path = boot / MANIFEST
    path.write_text(path.read_text() + "\n")
    report = module.build_report(reference, boot, output, require_manifests=True)
    assert report["status"] == "FAIL"
    assert "bootstrap manifest changed" in report["failures"][0]


@pytest.mark.parametrize("module", MODULES)
def test_dependency_extensions_do_not_change_snapshot_identity(prepared, module):
    root, full, reference, boot, _ = prepared
    output = root / "extended-strip"
    assert (
        strip.main(strip_args(full, reference, boot, output, "--require-manifests"))
        == 0
    )
    rewrite(
        output / MANIFEST,
        lambda data: data["bootstrap_manifest"].update(extra="future report field"),
    )
    report = module.build_report(reference, boot, output, require_manifests=True)
    assert passed(module, report), report["failures"]
    assert "extra" not in report["selection_manifests"]["RANDOM"]["bootstrap_manifest"]


def test_stripmatch_strict_flag_rejects_legacy_bootstrap(prepared):
    root, full, reference, boot, _ = prepared
    (boot / MANIFEST).unlink()
    output = root / "strict-strip"
    assert (
        strip.main(strip_args(full, reference, boot, output, "--require-manifests"))
        == 1
    )
    assert not output.exists()
    assert strip.main(strip_args(full, reference, boot, root / "legacy-strip")) == 0
    manifest = json.loads((root / "legacy-strip" / MANIFEST).read_text())
    assert manifest["bootstrap_manifest"]["status"] == "absent"


def test_source_aliases_are_rejected_before_dataset_publication(prepared):
    root, full, reference, _, _ = prepared
    path = full / "verified_patches/d"
    shutil.rmtree(path)
    path.symlink_to(full / "verified_patches/a", target_is_directory=True)
    output = root / "duplicate-source"
    assert (
        filtered.main(
            [
                "--source",
                str(full),
                "--satisfied",
                str(reference),
                "--mode",
                "bootstrap",
                "--out",
                str(output),
            ]
        )
        == 1
    )
    assert not output.exists()


@pytest.mark.parametrize("module", [filtered, strip])
def test_looping_source_link_is_an_actionable_refusal(prepared, module, capsys):
    root, full, reference, boot, _ = prepared
    path = full / "verified_patches/d"
    shutil.rmtree(path)
    path.symlink_to(path)
    output = root / "looping-source"
    args = (
        [
            "--source",
            str(full),
            "--satisfied",
            str(reference),
            "--mode",
            "bootstrap",
            "--out",
            str(output),
        ]
        if module is filtered
        else strip_args(full, reference, boot, output)
    )
    assert module.main(args) == 1
    error = capsys.readouterr().err
    assert "preparation failed" in error and "Traceback" not in error
    assert not output.exists()


@pytest.mark.parametrize("module", MODULES)
def test_strict_json_cli_is_read_only_and_reports_manifest_binding(prepared, module):
    root, _, reference, boot, control = prepared
    before = {
        path: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in root.rglob("*")
        if path.is_file()
    }
    result = subprocess.run(
        [
            sys.executable,
            module.__file__,
            "--reference",
            str(reference),
            "--bootstrap",
            str(boot),
            "--random",
            str(control),
            "--require-manifests",
            "--json",
        ],
        cwd=root.parent,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr
    assert passed(module, json.loads(result.stdout))
    assert {
        path: (path.read_bytes(), path.stat().st_mtime_ns) for path in before
    } == before
