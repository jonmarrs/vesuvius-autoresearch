"""Reproduce every released connected-components row on Linux, one process per target.

Uses an existing ScrollGT checkout and Python environment. No packages, data or
models are downloaded. Each CLI process has a 7 GiB address-space limit, one
OpenMP/OpenBLAS/MKL thread and a five-minute timeout. Other floor rows on its
scorecard are published metadata, not recomputed results.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import resource
import subprocess
import sys
import time
from pathlib import Path

LIMIT = 7 * 1024**3
SOURCE = "38496eb8ce5dc094c94ec852a332ee2293ea73a1"


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def git(root, *args):
    return (
        subprocess.check_output(
            ["git", "--no-optional-locks", "-C", str(root), *args],
            env={**os.environ, "GIT_NO_LAZY_FETCH": "1"},
        )
        .decode()
        .strip()
    )


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
                preexec_fn=budget,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=300,
            )
            status, error = run.returncode, None
        except subprocess.TimeoutExpired:
            status, error = None, "timeout after 300 seconds; no replacement run"
    result = {
        "returncode": status,
        "error": error,
        "seconds": time.perf_counter() - started,
        # This wrapper is fresh for every CLI process: no cumulative child peak.
        "peak_rss_kib": resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss,
        "address_space_limit_bytes": LIMIT,
    }
    Path(request["measurement"]).write_text(json.dumps(result, indent=2) + "\n")


def main():
    if sys.platform != "linux":
        raise SystemExit("measurement requires Linux RLIMIT_AS and KiB ru_maxrss")
    if len(sys.argv) == 3 and sys.argv[1] == "--measure":
        measure(sys.argv[2])
        return
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--scrollgt", type=Path, required=True)
    ap.add_argument(
        "--out",
        type=Path,
        required=True,
        help="new directory outside the ScrollGT checkout",
    )
    ap.add_argument("--python", default=sys.executable)
    ap.add_argument(
        "--launcher", type=Path, help="optional existing environment launcher before -m"
    )
    args = ap.parse_args()
    harness_sha256 = sha(__file__)
    root, out = args.scrollgt.resolve(), args.out.resolve()
    if out == root or root in out.parents or out in root.parents:
        ap.error("output must be outside and disjoint from the source checkout")
    if git(root, "rev-parse", "HEAD") != SOURCE or git(root, "status", "--porcelain"):
        ap.error(f"requires the clean measured ScrollGT checkout at {SOURCE}")
    targets = sorted((root / "data").glob("fibers_*"))
    if len(targets) != 21:
        ap.error("requires all 21 released targets; no selective subset")
    inputs = [
        p
        for target in targets
        for p in (target / "meta.json", target / "mask.npz", target / "skeleton.npz")
    ]
    sources = sorted((root / "src").rglob("*.py")) + [root / "pyproject.toml"]
    identities = {str(p.relative_to(root)): sha(p) for p in [*sources, *inputs]}
    out.mkdir(parents=True, exist_ok=False)
    env = dict(os.environ)
    env.update(
        PYTHONPATH=str(root / "src"),
        PYTHONDONTWRITEBYTECODE="1",
        OMP_NUM_THREADS="1",
        OPENBLAS_NUM_THREADS="1",
        MKL_NUM_THREADS="1",
    )
    prefix = [args.python] + ([str(args.launcher.resolve())] if args.launcher else [])
    probe = out / "runtime.py"
    probe.write_text(
        "import json,platform,numpy,scipy,sklearn\nimport scrollgt.fibers.eval_trace as e\nprint(json.dumps(dict(python=platform.python_version(),numpy=numpy.__version__,scipy=scipy.__version__,sklearn=sklearn.__version__,scorer=e.__file__)))\n"
    )
    runtime = json.loads(
        subprocess.check_output([*prefix, str(probe)], cwd=root, env=env, timeout=30)
    )
    if Path(runtime["scorer"]).resolve() != root / "src/scrollgt/fibers/eval_trace.py":
        raise RuntimeError("Python imported another checkout's scorer")
    results = []
    for index, target in enumerate(targets, 1):
        case = out / target.name
        case.mkdir()
        card = case / "scorecard.json"
        command = [
            *prefix,
            "-m",
            "scrollgt.cli",
            "score-fibers",
            "--floor",
            "connected_components",
            str(target),
            "--json-out",
            str(card),
        ]
        request = {
            "command": command,
            "cwd": str(root),
            "env": env,
            "log": str(case / "stdout.log"),
            "measurement": str(case / "measurement.json"),
        }
        # The inherited environment can contain credentials. Keep it in memory
        # in the child, never in the request or published evidence.
        request.pop("env")
        (case / "request.json").write_text(json.dumps(request, indent=2) + "\n")
        subprocess.run(
            [
                sys.executable,
                str(Path(__file__).resolve()),
                "--measure",
                str(case / "request.json"),
            ],
            env=env,
            check=True,
        )
        measured = json.loads((case / "measurement.json").read_text())
        expected = json.loads((target / "meta.json").read_text())["floors"][
            "floor_connected_components"
        ]
        actual = json.loads(card.read_text()) if measured["returncode"] == 0 else None
        metrics = actual["metrics"] if actual else None
        passed = metrics == expected and len(expected) == 15
        result = {
            "target": target.name,
            "measurement": measured,
            "expected": expected,
            "metrics": metrics,
            "exact_match": passed,
            "command": command,
            "scorecard_sha256": sha(card) if card.exists() else None,
            "log_sha256": sha(case / "stdout.log"),
        }
        results.append(result)
        print(
            f"{index}/21 {target.name}: {'EXACT' if passed else 'FAILED'}; {measured['seconds']:.2f}s; {measured['peak_rss_kib'] / 1024**2:.2f} GiB RSS",
            flush=True,
        )
    unchanged = sha(__file__) == harness_sha256 and all(
        sha(root / path) == expected for path, expected in identities.items()
    )
    report = {
        "scope": "connected-components CLI reproduction only; no model inference or GPU tracing",
        "source_commit": SOURCE,
        "runtime": runtime,
        "harness_sha256": harness_sha256,
        "inputs_and_sources_sha256": identities,
        "all_sources_unchanged": unchanged,
        "cases": results,
        "status": "EXACT"
        if unchanged and all(r["exact_match"] for r in results)
        else "FAILED",
    }
    (out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    if report["status"] != "EXACT":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
