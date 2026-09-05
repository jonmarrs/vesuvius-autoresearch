"""Resolve the six arms' result files and invoke the pre-committed analysis.

This does NOT decide anything. `scripts/analyse_patch_bootstrap.py` holds the
registered rule and is called unchanged; this only assembles its arguments.

It exists because assembling them by hand means typing twelve paths, and the way
that goes wrong is silent: a glob like `*patch_<tag>` with `head -1` will happily
pair one arm's fresh `metrics.json` with another run's stale
`satisfaction_metrics_fitted.json` and report a verdict on a mixture. Today every
tag resolves to exactly one directory, but re-running a single arm -- the obvious
thing to do if one fails -- creates a second, and nothing downstream would notice.

So a tag matching zero or several directories is an error here, not a choice.
"""

import argparse
import glob
import os
import subprocess
import sys

BOOT = ("boot090s1", "boot090s2", "boot090s3")
RAND = ("rand090s1", "rand090s2", "rand090s3")
STRIP = ("strip090s1", "strip090s2", "strip090s3")

# One resolver, two studies. The STRIPMATCH follow-up reuses the BOOTSTRAP arms
# rather than refitting them, so its comparison is BOOT vs STRIP. Duplicating the
# resolver into a second script would leave two copies of the ambiguity guard to
# drift apart, which is exactly the failure it exists to prevent.
STUDIES = {
    "bootstrap": (BOOT + RAND, "analyse_patch_bootstrap.py"),
    "stripmatch": (BOOT + STRIP, "analyse_stripmatch.py"),
}


def resolve(spiral_out, tag):
    """(metrics.json, satisfaction_metrics_fitted.json) for one arm.

    Raises rather than guessing when the fit directory is ambiguous or absent.
    """
    metrics = os.path.join(spiral_out, f"outer_{tag}", "ink_metric", "metrics.json")
    if not os.path.isfile(metrics):
        raise SystemExit(f"{tag}: no metrics.json at {metrics} -- arm not scored yet")

    dirs = sorted(glob.glob(os.path.join(spiral_out, f"*patch_{tag}")))
    if len(dirs) != 1:
        raise SystemExit(
            f"{tag}: expected exactly one fit directory, found {len(dirs)}"
            + (":\n  " + "\n  ".join(dirs) if dirs else "")
            + "\nRefusing to guess: pairing one arm's metrics with another run's "
            "satisfaction file would produce a verdict on a mixture."
        )

    sat = os.path.join(dirs[0], "satisfaction_metrics_fitted.json")
    if not os.path.isfile(sat):
        raise SystemExit(f"{tag}: no satisfaction_metrics_fitted.json in {dirs[0]}")
    return metrics, sat


def build_args(spiral_out, tags=BOOT + RAND):
    return [f"{t}={m},{s}" for t in tags for m, s in [resolve(spiral_out, t)]]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument(
        "--study",
        default="bootstrap",
        choices=sorted(STUDIES),
        help="which registered comparison to run (default: the parent study)",
    )
    ap.add_argument("--out", default=None, help="write the verdict json here")
    args = ap.parse_args()

    tags, analysis = STUDIES[args.study]
    specs = build_args(args.spiral_out, tags)
    here = os.path.dirname(os.path.abspath(__file__))
    cmd = [sys.executable, os.path.join(here, analysis), *specs]
    if args.out:
        cmd += ["--out", args.out]

    print(f"resolved all {len(specs)} arms for study '{args.study}':")
    for s in specs:
        print(f"  {s.split('=')[0]}")
    print()
    return subprocess.call(cmd)


if __name__ == "__main__":
    sys.exit(main())
