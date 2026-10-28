"""Check current Villa's object-store CLI against a snapshot of finished tracer tiles.

Plans by default. --execute uses an already configured Villa environment, exports
twice, and checks every fiber in bounded batches. No tracing, installs or GPU work.
The original run and source checkout are read only. This checks export, not the
current tracer's inference or seed-heading behavior.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import itertools
import json
import math
import os
import shutil
import subprocess
import sys
import uuid
from pathlib import Path

import numpy as np

MODULE = "vesuvius.neural_tracing.tracers.fibers.tracing.volume_store"
API = "vesuvius.neural_tracing.tracers.shared.annotations.fiber_store"
SOURCE = Path("vesuvius/src")


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for part in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(part)
    return digest.hexdigest()


def tiles(run):
    return sorted(
        p for p in (run / "tiles").glob("*.npz") if not p.name.endswith(".partial.npz")
    )


def identities(run):
    return {str(p.relative_to(run)): sha(p) for p in [run / "run.json", *tiles(run)]}


def source_identity(villa):
    def git(*args):
        return subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(villa), *args],
            text=True,
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        ).strip()

    if git("status", "--porcelain", "--", str(SOURCE)):
        raise ValueError("Villa's Python source must be clean")
    # Hash the actual Python source as well as naming the checkout's commit.
    sources = sorted((villa / SOURCE / "vesuvius/neural_tracing").rglob("*.py"))
    required = villa / SOURCE / Path(*MODULE.split(".")).with_suffix(".py")
    if required not in sources:
        raise ValueError(
            "requires Villa with tracing/volume_store.py (object-store export)"
        )
    return {
        "commit": git("rev-parse", "HEAD"),
        "sha256": {str(p.relative_to(villa)): sha(p) for p in sources},
    }


def expected_fibers(run, scale, namespace):
    """Independent tile decoding: expected UUID, native xyz and exported provenance."""
    seen = set()
    for path in tiles(run):
        with np.load(path, allow_pickle=False) as data:
            fields = {
                key: data[key]
                for key in (
                    "points",
                    "offsets",
                    "id",
                    "seed",
                    "family",
                    "plane",
                    "reasons",
                    "links",
                )
            }
        offsets, points = fields["offsets"], fields["points"]
        if (
            offsets.ndim != 1
            or not np.issubdtype(offsets.dtype, np.integer)
            or len(offsets) != len(fields["id"]) + 1
            or offsets[0] != 0
            or offsets[-1] != len(points)
            or (np.diff(offsets) < 0).any()
            or points.ndim != 2
            or points.shape[1] != 3
        ):
            raise ValueError(f"invalid tile layout: {path}")
        for index, fid in enumerate(fields["id"]):
            xyz = points[offsets[index] : offsets[index + 1]].astype(np.float64) * scale
            if len(xyz) < 2:
                continue
            if not np.isfinite(xyz).all() or int(fid) < 0 or int(fid) in seen:
                raise ValueError(f"invalid or duplicate fiber id: {fid}")
            seen.add(int(fid))

            def identifier(number):
                return (
                    None if number < 0 else str(uuid.uuid5(namespace, str(int(number))))
                )

            yield {
                "id": identifier(fid),
                "name": f"fiber_follow {int(fid):08d}",
                "family": str(fields["family"][index]),
                "xyz": xyz,
                "provenance": {
                    "run": str(namespace),
                    "run_id": int(fid),
                    "tile": path.stem,
                    "seed": (fields["seed"][index] * scale).tolist(),
                    "seed_plane": str(fields["plane"][index]),
                    "stop_reasons": [str(r) for r in fields["reasons"][index]],
                    "links": [identifier(n) for n in fields["links"][index]],
                },
            }


def verify(api, destination, run, scale, namespace, volume):
    expected = iter(expected_fibers(run, scale, namespace))
    fibers = points = 0
    while batch := list(itertools.islice(expected, 256)):
        rows = api.read_polylines(destination, [r["id"] for r in batch], volume=volume)
        actual = {row["id"]: (row, xyz) for row, xyz in rows}
        if len(rows) != len(batch) or set(actual) != {r["id"] for r in batch}:
            raise ValueError("exported fiber identities differ")
        for wanted in batch:
            row, xyz = actual[wanted["id"]]
            if (
                row["name"] != wanted["name"]
                or row["family"] != wanted["family"]
                or row["point_count"] != len(wanted["xyz"])
                or row["meta"]["coordinates"]
                != {"volume_uuid": volume, "scale_factor": 1}
                or row["meta"]["fiber_follow"] != wanted["provenance"]
                or not np.array_equal(xyz, wanted["xyz"])
            ):
                raise ValueError(
                    f"exported geometry or metadata differs: {wanted['id']}"
                )
            fibers += 1
            points += len(xyz)
    with api.open_store(destination) as store:
        if store.object_count("fiber") != fibers:
            raise ValueError("export contains extra or missing fibers")
    if not fibers:
        raise ValueError("no nonempty fibers checked")
    return {"fibers": fibers, "points": points}


def prepare(villa, run, out, volume, ct=None):
    if any(out == p or p in out.parents or out in p.parents for p in (villa, run)):
        raise ValueError("output must be outside and disjoint from both source and run")
    if out.exists():
        raise ValueError("output must be a new directory")
    before = identities(run)
    # Parse exactly the captured record whose hash is recorded.
    raw = (run / "run.json").read_bytes()
    if hashlib.sha256(raw).hexdigest() != before["run.json"]:
        raise ValueError("run record changed while reading")
    record = json.loads(raw)
    if not (ct or record.get("ct_zarr") or record.get("ct")):
        raise ValueError(
            "pass --ct for a legacy record; checkpoint fallback is disabled"
        )
    scale = float(record["grid_scale"])
    if not math.isfinite(scale) or scale <= 0 or not tiles(run):
        raise ValueError("requires a positive finite grid_scale and finished tiles")
    source = source_identity(villa)
    namespace = (
        uuid.UUID(record["fiber_namespace"])
        if record.get("fiber_namespace")
        else uuid.uuid5(
            uuid.NAMESPACE_URL, "export-check:" + json.dumps(before, sort_keys=True)
        )
    )
    plan = {
        "status": "PLANNED",
        "scope": "finished-tile export only; no tracing or GPU work",
        "villa": str(villa),
        "run": str(run),
        "out": str(out),
        "volume": volume,
        "ct_override": ct,
        "source": source,
        "inputs_sha256": before,
        "harness_sha256": sha(__file__),
        "namespace": str(namespace),
        "namespace_added_to_snapshot": not bool(record.get("fiber_namespace")),
    }
    return plan, record, scale, namespace


def run_check(plan, record, scale, namespace):
    villa, run, out = (Path(plan[k]) for k in ("villa", "run", "out"))
    # Import before creating outputs: a missing native module leaves no apparent result.
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(villa / SOURCE))
    api = importlib.import_module(API)
    if Path(api.__file__).resolve() != villa / SOURCE / Path(
        *API.split(".")
    ).with_suffix(".py"):
        raise ValueError("imported another checkout's fiber reader")
    out.mkdir(parents=True, exist_ok=False)
    report = {**plan, "status": "FAILED", "passes": []}
    report["runtime"] = {
        "python": sys.version,
        "numpy": np.__version__,
        "reader": api.__file__,
    }
    try:
        snapshot = out / "snapshot"
        (snapshot / "tiles").mkdir(parents=True)
        for relative in plan["inputs_sha256"]:
            shutil.copyfile(run / relative, snapshot / relative)
        if identities(snapshot) != plan["inputs_sha256"]:
            raise ValueError("inputs changed while copying")
        record = {**record, "fiber_namespace": str(namespace)}
        (snapshot / "run.json").write_text(json.dumps(record, indent=2) + "\n")
        snapshot_identity = identities(snapshot)
        command = [sys.executable, "-m", MODULE, str(snapshot)]
        if plan["ct_override"]:
            command += ["--ct", plan["ct_override"]]
        report["command"] = command
        env = {
            **os.environ,
            "PYTHONPATH": str(villa / SOURCE)
            + os.pathsep
            + os.environ.get("PYTHONPATH", ""),
            "PYTHONDONTWRITEBYTECODE": "1",
            "OMP_NUM_THREADS": "1",
            "OPENBLAS_NUM_THREADS": "1",
            "MKL_NUM_THREADS": "1",
        }
        for index in (1, 2):
            with (out / f"export-{index}.log").open("w") as log:
                subprocess.run(
                    command,
                    cwd=villa,
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                    check=True,
                    timeout=1800,
                )
            report["passes"].append(
                verify(
                    api,
                    snapshot / "fibers.vcobj",
                    snapshot,
                    scale,
                    namespace,
                    plan["volume"],
                )
            )
        if identities(snapshot) != snapshot_identity:
            raise ValueError("snapshot changed during verification")
        if (
            identities(run) != plan["inputs_sha256"]
            or source_identity(villa) != plan["source"]
        ):
            raise ValueError("source or original run changed during verification")
        if sha(__file__) != plan["harness_sha256"]:
            raise ValueError("verification harness changed during verification")
        report["status"] = "EXACT"
    except Exception as error:
        report["error"] = f"{type(error).__name__}: {error}"
        raise
    finally:
        (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--villa", type=Path, required=True)
    parser.add_argument(
        "--run",
        type=Path,
        required=True,
        help="closed real-data tracing run; never a live run",
    )
    parser.add_argument(
        "--out", type=Path, required=True, help="new directory outside both inputs"
    )
    parser.add_argument(
        "--volume",
        required=True,
        help="expected native volume id, independently checked from the scan",
    )
    parser.add_argument(
        "--ct",
        help="CT store for legacy records with no CT path (passed only to the export copy)",
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="run twice using the current configured Python environment",
    )
    args = parser.parse_args()
    plan, record, scale, namespace = prepare(
        args.villa.resolve(),
        args.run.resolve(),
        args.out.resolve(),
        args.volume,
        args.ct,
    )
    print(
        json.dumps(
            run_check(plan, record, scale, namespace) if args.execute else plan,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
