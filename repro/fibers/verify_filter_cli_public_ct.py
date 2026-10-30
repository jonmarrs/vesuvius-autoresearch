"""Compare the pre-streaming and current fiber CLI on one pinned public CT cube.

CPU only: both filters, identical block/halo settings, one process per case.
Downloads and TIFF conversion are outside the measured CLI wall time. No model
or tracing-quality evaluation is performed. Failed cases are retained, not rerun.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import resource
import subprocess
import sys
import time
from pathlib import Path

BASELINE = "f2efeda9dbb246b22952744c6fdf8d849e22e94f"
TIFF_SHA = "0d38453cc37157f46b180e3711172e99f56eb216948eb6755eca0019ad0dbf60"
LIMIT = 4 * 1024**3
CLI = "src/vesuvius_autoresearch/fibers/cli.py"


def sha(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as stream:
        while block := stream.read(1024**2):
            digest.update(block)
    return digest.hexdigest()


def git(root, *args):
    return subprocess.check_output(
        ["git", "--no-optional-locks", "-C", str(root), *args],
        env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
    )


def write(path, value):
    Path(path).write_text(json.dumps(value, indent=2) + "\n")


def measure(request_path):
    request = json.loads(Path(request_path).read_text())

    def budget():
        resource.setrlimit(resource.RLIMIT_AS, (LIMIT, LIMIT))

    started = time.perf_counter()
    with Path(request["log"]).open("w") as log:
        try:
            run = subprocess.run(
                request["command"],
                cwd=request["cwd"],
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=budget,
                timeout=180,
            )
            status, error = run.returncode, None
        except subprocess.TimeoutExpired:
            status, error = None, "timeout after 180 seconds; no replacement run"
    write(
        request["measurement"],
        {
            "returncode": status,
            "error": error,
            "seconds": time.perf_counter() - started,
            # A fresh wrapper per CLI avoids cumulative child peak RSS.
            "peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
            "address_space_limit_bytes": LIMIT,
        },
    )


def main():
    if sys.platform != "linux":
        raise SystemExit("requires Linux RLIMIT_AS and KiB ru_maxrss")
    if len(sys.argv) == 3 and sys.argv[1] == "--measure":
        measure(sys.argv[2])
        return
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--repo", type=Path, required=True)
    ap.add_argument("--tiff", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True, help="new directory")
    args = ap.parse_args()
    root, tiff, out = args.repo.resolve(), args.tiff.resolve(), args.out.resolve()
    if root == out or root in out.parents or out in root.parents or out in tiff.parents:
        ap.error("output must be outside source checkout and must not contain input")
    if sha(tiff) != TIFF_SHA:
        ap.error("requires the pinned public s1_00497_01497_03997_256 TIFF")
    sources = sorted((root / "src/vesuvius_autoresearch/fibers").glob("*.py"))
    sources += [
        root / "src/vesuvius_autoresearch/core/file_modes.py",
        root / "src/vesuvius_autoresearch/core/prediction_artifacts.py",
    ]
    identities = {str(p.relative_to(root)): sha(p) for p in sources}
    for relative in (
        "src/vesuvius_autoresearch/fibers/detection.py",
        "src/vesuvius_autoresearch/fibers/__init__.py",
    ):
        if (
            git(root, "show", f"{BASELINE}:{relative}")
            != (root / relative).read_bytes()
        ):
            ap.error("baseline CLI requires unchanged filter math and package imports")
    import numpy as np
    import scipy
    import tifffile

    image = tifffile.imread(tiff)
    if image.shape != (256, 256, 256) or image.dtype != np.uint8:
        ap.error("unexpected public CT layout")
    out.mkdir(parents=True, exist_ok=False)
    ct = out / "ct.npy"
    with ct.open("xb") as stream:
        np.save(stream, image, allow_pickle=False)
    del image
    ct_hash = sha(ct)
    baseline_cli = out / "baseline_cli.py"
    baseline_cli.write_bytes(git(root, "show", f"{BASELINE}:{CLI}"))
    baseline_hash = sha(baseline_cli)
    harness_hash = sha(__file__)
    env = {
        **os.environ,
        "PYTHONPATH": str(root / "src"),
        "PYTHONDONTWRITEBYTECODE": "1",
        "OMP_NUM_THREADS": "1",
        "OPENBLAS_NUM_THREADS": "1",
        "MKL_NUM_THREADS": "1",
        "CUDA_VISIBLE_DEVICES": "",
    }
    records = []
    for filter_name in ("ridges", "vesselness"):
        for variant in ("baseline", "streaming"):
            name = f"{filter_name}-{variant}"
            output = out / f"{name}.npy"
            invocation = (
                [str(baseline_cli)]
                if variant == "baseline"
                else ["-m", "vesuvius_autoresearch.fibers.cli"]
            )
            command = [
                sys.executable,
                *invocation,
                "--input",
                str(ct),
                "--output",
                str(output),
                "--filter",
                filter_name,
                "--device",
                "cpu",
                "--tiled",
                "--block-size",
                "64",
                "--halo",
                "16",
            ]
            request = {
                "command": command,
                "cwd": str(root),
                "log": str(out / f"{name}.log"),
                "measurement": str(out / f"{name}-measurement.json"),
            }
            request_path = out / f"{name}-request.json"
            write(request_path, request)
            print(f"RUN {name}", flush=True)
            subprocess.run(
                [
                    sys.executable,
                    str(Path(__file__).resolve()),
                    "--measure",
                    str(request_path),
                ],
                env=env,
                check=True,
                timeout=210,
            )
            result = json.loads(Path(request["measurement"]).read_text())
            if result["returncode"] == 0:
                response = np.load(output, allow_pickle=False, mmap_mode="r")
                result["finite_float32_response"] = (
                    response.shape == (256, 256, 256)
                    and response.dtype == np.float32
                    and all(
                        np.isfinite(response[z : z + 32]).all()
                        for z in range(0, 256, 32)
                    )
                )
                response._mmap.close()
                result["output_sha256"] = sha(output)
            records.append(
                {"filter": filter_name, "variant": variant, **request, **result}
            )
            print(json.dumps(records[-1]), flush=True)
    comparisons = {
        name: records[2 * i].get("output_sha256") is not None
        and records[2 * i].get("output_sha256")
        == records[2 * i + 1].get("output_sha256")
        for i, name in enumerate(("ridges", "vesselness"))
    }
    unchanged = (
        sha(tiff) == TIFF_SHA
        and sha(ct) == ct_hash
        and sha(baseline_cli) == baseline_hash
        and sha(__file__) == harness_hash
        and identities == {str(p.relative_to(root)): sha(p) for p in sources}
    )
    success = bool(
        unchanged
        and all(comparisons.values())
        and all(row.get("finite_float32_response") for row in records)
    )
    write(
        out / "report.json",
        {
            "source_commit": git(root, "rev-parse", "HEAD").decode().strip(),
            "baseline_cli_commit": BASELINE,
            "baseline_cli_sha256": baseline_hash,
            "baseline_scope": "Historical CLI body with byte-identical filter math/package imports",
            "harness_sha256": harness_hash,
            "source_sha256": identities,
            "tiff_sha256": TIFF_SHA,
            "ct_npy_sha256": ct_hash,
            "runtime": {
                "python": platform.python_version(),
                "numpy": np.__version__,
                "scipy": scipy.__version__,
                "tifffile": tifffile.__version__,
            },
            "measurements": records,
            "identical_npy_files": comparisons,
            "source_and_inputs_unchanged": unchanged,
            "success": success,
            "scope": "One public CT cube, CPU only, single run per case; no quality/VRAM/speedup claim",
        },
    )
    raise SystemExit(0 if success else 1)


if __name__ == "__main__":
    main()
