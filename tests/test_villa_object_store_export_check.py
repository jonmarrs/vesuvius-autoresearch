"""The export check rejects geometry, identity, input-drift and CLI failures.

These fixtures test the verifier, not the unavailable native store. The final
source comparison exercises Villa's pinned tile iterator without native I/O.
"""

import ast
import copy
import importlib.util
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "export_check", ROOT / "repro/fibers/verify_villa_object_store_export.py"
)
check = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(check)
NAMESPACE = uuid.UUID("b03518ef-c852-4418-bd42-93cd425d71e0")


@pytest.fixture
def inputs(tmp_path, monkeypatch):
    villa, run, out = (tmp_path / name for name in ("villa", "run", "out"))
    villa.mkdir()
    (run / "tiles").mkdir(parents=True)
    record = {
        "grid_scale": 2.5,
        "fiber_namespace": str(NAMESPACE),
        "ct_zarr": "recorded-CT",
    }
    (run / "run.json").write_text(json.dumps(record))
    np.savez(
        run / "tiles/tile.npz",
        points=np.array([[1, 2, 3], [4, 5, 6], [7, 8, 9], [10, 11, 12]], np.float32),
        offsets=[0, 2, 4],
        id=[3, 7],
        seed=[[1.0, 2.0, 3.0], [7.0, 8.0, 9.0]],
        family=["H", "V"],
        plane=["z", "x"],
        reasons=[["box", "owned"], ["owned", "box"]],
        links=[[-1, 7], [3, -1]],
    )
    # An incomplete tile must never participate, even if unreadable.
    (run / "tiles/tile.partial.npz").write_bytes(b"not a complete tile")
    monkeypatch.setattr(
        check, "source_identity", lambda _: {"commit": "fixture", "sha256": {}}
    )
    return villa, run, out, record


def reader(rows):
    class Store:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def object_count(self, kind):
            assert kind == "fiber"
            return len(rows)

    return SimpleNamespace(
        read_polylines=lambda destination, ids, volume: [
            (r, xyz) for r, xyz in rows if r["id"] in ids
        ],
        open_store=lambda _: Store(),
    )


def exported_rows():
    ids = [str(uuid.uuid5(NAMESPACE, str(n))) for n in (3, 7)]
    rows = []
    for k, fid in enumerate((3, 7)):
        start = (1, 2, 3) if k == 0 else (7, 8, 9)
        xyz = np.array([start, np.array(start) + 3], dtype=np.float64) * 2.5
        row = {
            "id": ids[k],
            "name": f"fiber_follow {fid:08d}",
            "family": ("H", "V")[k],
            "point_count": 2,
            "meta": {
                "coordinates": {"volume_uuid": "volume-id", "scale_factor": 1},
                "fiber_follow": {
                    "run": str(NAMESPACE),
                    "run_id": fid,
                    "tile": "tile",
                    "seed": (np.array(start) * 2.5).tolist(),
                    "seed_plane": ("z", "x")[k],
                    "stop_reasons": (["box", "owned"], ["owned", "box"])[k],
                    "links": ([None, ids[1]], [ids[0], None])[k],
                },
            },
        }
        rows.append((row, xyz))
    return rows


def test_plan_does_not_import_native_module_or_create_output(inputs, monkeypatch):
    villa, run, out, _ = inputs
    before = check.identities(run)
    monkeypatch.setattr(
        check.importlib,
        "import_module",
        lambda _: pytest.fail("native import during plan"),
    )
    plan, _, _, _ = check.prepare(villa, run, out, "volume-id")
    assert plan["status"] == "PLANNED" and plan["inputs_sha256"] == before
    assert not out.exists() and check.identities(run) == before


def test_missing_native_dependency_leaves_no_output(inputs, monkeypatch):
    villa, run, out, _ = inputs
    plan, record, scale, namespace = check.prepare(villa, run, out, "volume-id")

    def missing(_):
        raise ModuleNotFoundError("vc_object_store")

    monkeypatch.setattr(check.importlib, "import_module", missing)
    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(ModuleNotFoundError, match="vc_object_store"):
        check.run_check(plan, record, scale, namespace)
    assert not out.exists()


def test_reader_from_another_checkout_is_refused(inputs, monkeypatch):
    villa, run, out, _ = inputs
    plan, record, scale, namespace = check.prepare(villa, run, out, "volume-id")
    monkeypatch.setattr(
        check.importlib, "import_module", lambda _: SimpleNamespace(__file__=__file__)
    )
    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    with pytest.raises(ValueError, match="another checkout"):
        check.run_check(plan, record, scale, namespace)
    assert not out.exists()


@pytest.mark.parametrize(
    "location", ["source", "run", "inside-run", "parent", "existing", "alias"]
)
def test_refuses_output_that_could_replace_inputs(inputs, location):
    villa, run, out, _ = inputs
    if location == "existing":
        out.mkdir()
    if location == "alias":
        out.symlink_to(run, target_is_directory=True)
    output = {
        "source": villa,
        "run": run,
        "inside-run": run / "new",
        "parent": run.parent,
        "existing": out,
        "alias": out.resolve(),
    }[location]
    before = check.identities(run)
    with pytest.raises(ValueError, match="disjoint|new directory"):
        check.prepare(villa, run, output, "volume-id")
    assert check.identities(run) == before


def test_legacy_namespace_is_derived_only_for_the_export_copy(inputs):
    villa, run, out, record = inputs
    record.pop("fiber_namespace")
    (run / "run.json").write_text(json.dumps(record))
    before = (run / "run.json").read_bytes()
    first = check.prepare(villa, run, out, "volume-id")
    second = check.prepare(villa, run, out, "volume-id")
    assert first[0]["namespace_added_to_snapshot"] is True and first[3] == second[3]
    assert (run / "run.json").read_bytes() == before


def test_legacy_record_requires_ct_instead_of_loading_a_checkpoint(inputs):
    villa, run, out, record = inputs
    record.pop("ct_zarr")
    (run / "run.json").write_text(json.dumps(record))
    with pytest.raises(ValueError, match="checkpoint fallback is disabled"):
        check.prepare(villa, run, out, "volume-id")
    plan, _, _, _ = check.prepare(villa, run, out, "volume-id", ct="explicit-CT")
    assert plan["ct_override"] == "explicit-CT" and not out.exists()


def test_captured_config_hash_cannot_bind_different_parsed_contents(
    inputs, monkeypatch
):
    villa, run, out, record = inputs
    original = check.identities

    def rewrite(path):
        captured = original(path)
        (run / "run.json").write_text(json.dumps({**record, "grid_scale": 99}))
        return captured

    monkeypatch.setattr(check, "identities", rewrite)
    with pytest.raises(ValueError, match="changed while reading"):
        check.prepare(villa, run, out, "volume-id")
    assert not out.exists()


def test_exact_geometry_ids_and_links_pass(inputs):
    _, run, _, _ = inputs
    assert check.verify(
        reader(exported_rows()), "unused", run, 2.5, NAMESPACE, "volume-id"
    ) == {
        "fibers": 2,
        "points": 4,
    }


@pytest.mark.parametrize(
    "fault", ["axis-order", "scale", "family", "volume", "link", "missing", "extra"]
)
def test_rejects_semantically_wrong_exports(inputs, fault):
    _, run, _, _ = inputs
    rows = exported_rows()
    if fault == "axis-order":
        rows[0] = (rows[0][0], rows[0][1][:, ::-1])
    elif fault == "scale":
        rows[0] = (rows[0][0], rows[0][1] / 2.5)
    elif fault == "family":
        rows[0][0]["family"] = "V"
    elif fault == "volume":
        rows[0][0]["meta"]["coordinates"]["volume_uuid"] = "other-volume"
    elif fault == "link":
        rows[0][0]["meta"]["fiber_follow"]["links"] = [None, None]
    elif fault == "missing":
        rows.pop()
    else:
        extra = copy.deepcopy(rows[0])
        extra[0]["id"] = str(uuid.uuid4())
        rows.append(extra)
    with pytest.raises(ValueError):
        check.verify(reader(rows), "unused", run, 2.5, NAMESPACE, "volume-id")


@pytest.mark.parametrize("fault", [None, "cli", "original-drift", "snapshot-drift"])
def test_two_cli_exports_preserve_inputs_and_fail_closed(inputs, monkeypatch, fault):
    villa, run, out, _ = inputs
    plan, record, scale, namespace = check.prepare(villa, run, out, "volume-id")
    before = check.identities(run)
    api = reader(exported_rows())
    api.__file__ = str(
        villa / check.SOURCE / Path(*check.API.split(".")).with_suffix(".py")
    )
    monkeypatch.setattr(check.importlib, "import_module", lambda _: api)
    monkeypatch.setattr(sys, "path", sys.path[:])
    monkeypatch.setattr(sys, "dont_write_bytecode", False)
    calls = []

    def cli(command, **kwargs):
        assert command[1:3] == ["-m", check.MODULE]
        assert kwargs["check"] and kwargs["timeout"] == 1800
        assert kwargs["env"]["PYTHONPATH"].split(os.pathsep)[0] == str(
            villa / check.SOURCE
        )
        calls.append(command)
        if fault == "cli":
            raise subprocess.CalledProcessError(17, command)
        if fault == "original-drift":
            (run / "tiles/new.npz").write_bytes(b"a live run added a tile")
        if fault == "snapshot-drift":
            (out / "snapshot/run.json").write_text("{}")

    monkeypatch.setattr(check.subprocess, "run", cli)
    if fault:
        with pytest.raises((ValueError, subprocess.CalledProcessError)):
            check.run_check(plan, record, scale, namespace)
    else:
        check.run_check(plan, record, scale, namespace)
        assert check.identities(run) == before and len(calls) == 2
    result = json.loads((out / "report.json").read_text())
    assert result["status"] == ("FAILED" if fault else "EXACT")
    assert (
        "error" in result
        if fault
        else result["passes"] == [{"fibers": 2, "points": 4}] * 2
    )


def test_decoder_matches_the_pinned_real_villa_tile_iterator(inputs):
    _, run, _, _ = inputs
    villa = Path(os.environ.get("VILLA_REVIEW_ROOT", ROOT / "villa"))
    source = subprocess.run(
        [
            "git",
            "-C",
            str(villa),
            "show",
            "39a8cf3a124bdd5540ee826e1cb30047c8dc8c85:vesuvius/src/vesuvius/neural_tracing/tracers/fibers/tracing/volume_store.py",
        ],
        capture_output=True,
        text=True,
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )
    if source.returncode:
        pytest.skip("requires the cached Villa object-store source at 39a8cf3a")
    nodes = [
        node
        for node in ast.parse(source.stdout).body
        if isinstance(node, ast.FunctionDef)
        and node.name in ("fiber_uuid", "run_fibers")
    ]
    assert len(nodes) == 2
    namespace = {"np": np, "uuid": uuid, "Path": Path}
    exec(
        compile(ast.Module(nodes, type_ignores=[]), "Villa volume_store.py", "exec"),
        namespace,
    )
    actual = list(namespace["run_fibers"](run, 2.5, str(NAMESPACE)))
    expected = list(check.expected_fibers(run, 2.5, NAMESPACE))
    assert len(actual) == len(expected) == 2
    for (row, xyz), wanted in zip(actual, expected, strict=False):
        np.testing.assert_array_equal(xyz, wanted["xyz"])
        assert row == {
            "id": wanted["id"],
            "name": wanted["name"],
            "family": wanted["family"],
            "meta": {"fiber_follow": wanted["provenance"]},
        }
