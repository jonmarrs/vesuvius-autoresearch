#!/usr/bin/env python3
"""Plan or explicitly run the pinned manual Zarr-to-Zarr registration viewer.

Saved XYZ affine transforms are validated before publication. This tool neither
resamples CT nor proves alignment accuracy; save with W before exiting the REPL.
"""

from __future__ import annotations

import argparse
import os
import shlex
import subprocess
import sys
from pathlib import Path

import numpy as np
import zarr

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, separate_paths
from scripts.geometry_artifacts import REGISTRATION_DIR, validate_transform, voxel_size
from scripts.labeling.label_artifacts import new_output, publish_new_file, volume
from scripts.validate_prize_artifact import _load_json


def registration_plan(
    fixed, moving, output_transform, fixed_voxel_size, moving_voxel_size
):
    fixed, moving = separate_paths(fixed, moving)
    output = new_output(output_transform, fixed, moving)
    if output.suffix != ".json":
        raise ValueError("output transform must end with .json")
    shapes, sizes = [], []
    for source, supplied in ((fixed, fixed_voxel_size), (moving, moving_voxel_size)):
        root, array = volume(source)
        if not isinstance(root, zarr.Group) or array.dtype.kind not in "uif":
            raise ValueError(
                "pinned registration requires a real 3D Zarr group with array '0'"
            )
        size = voxel_size(supplied)
        if "multiscales" in root.attrs:
            raise ValueError(
                "general OME transforms are unsupported by this isotropic raw-volume wrapper; make a verified registration-compatible export"
            )
        metadata_path = source / "metadata.json"
        if metadata_path.is_file():
            metadata = _load_json(metadata_path)
            measured = (
                metadata.get("scan", {})
                .get("tomo", {})
                .get("acquisition", {})
                .get("detector", {})
                .get("samplePixelSize")
            )
            if measured is not None and not np.isclose(
                voxel_size(measured) * 1000, size
            ):
                raise ValueError(
                    "declared voxel size disagrees with scan metadata.json"
                )
        shapes.append(array.shape)
        sizes.append(size)
    tool = REGISTRATION_DIR / "find_transform.py"
    if not tool.is_file():
        raise FileNotFoundError(f"pinned registration tool missing: {tool}")
    command = [
        sys.executable,
        "-i",
        str(tool),
        "--fixed",
        str(fixed),
        "--moving",
        str(moving),
        "--moving-type",
        "zarr",
        "--fixed-voxel-size",
        str(sizes[0]),
        "--moving-voxel-size",
        str(sizes[1]),
        "--output-transform",
        str(output),
    ]
    return {
        "fixed": fixed,
        "moving": moving,
        "output": output,
        "shapes": shapes,
        "command": command,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--fixed", required=True)
    parser.add_argument("--moving", required=True)
    parser.add_argument(
        "--fixed-voxel-size",
        type=float,
        help="Declared isotropic fixed voxel size in micrometers",
    )
    parser.add_argument(
        "--moving-voxel-size",
        type=float,
        help="Declared isotropic moving voxel size in micrometers",
    )
    parser.add_argument(
        "--output-transform",
        "--output_transform",
        dest="output_transform",
        required=True,
    )
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Probe optional runtime, then launch the interactive manual viewer",
    )
    args = parser.parse_args(argv)
    try:
        plan = registration_plan(
            args.fixed,
            args.moving,
            args.output_transform,
            args.fixed_voxel_size,
            args.moving_voxel_size,
        )
        print(f"Manual registration command: {shlex.join(plan['command'])}")
        print(
            "Coordinates: moving XYZ voxels -> fixed XYZ voxels. Accuracy is unverified; no CT resampling or training integration is performed."
        )
        if not args.execute:
            print(
                "Dry run. Use --execute in an interactive terminal. No transform was saved."
            )
            return 0
        if not sys.stdin.isatty():
            raise ValueError(
                "--execute requires an interactive terminal for the Python REPL"
            )
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            filter(None, (str(REGISTRATION_DIR), env.get("PYTHONPATH")))
        )
        probe = subprocess.run(
            [
                sys.executable,
                "-c",
                "import neuroglancer; import registration; import transform_utils",
            ],
            cwd=REGISTRATION_DIR,
            env=env,
            capture_output=True,
            text=True,
            check=False,
        )
        if probe.returncode:
            raise RuntimeError(
                f"optional registration runtime failed: {probe.stderr.strip()}"
            )
        print(
            "In the viewer press W to write the current transform, then Ctrl+D in the terminal to exit. Ctrl+D does not save. Landmark fits and manual transforms still require independent accuracy review."
        )
        with publish_new_file(plan["output"], plan["fixed"], plan["moving"]) as staging:
            command = list(plan["command"])
            command[-1] = str(staging)
            result = subprocess.run(command, cwd=REGISTRATION_DIR, env=env, check=False)
            if result.returncode:
                raise RuntimeError(
                    f"registration process exited with status {result.returncode}"
                )
            validate_transform(staging, plan["fixed"], *plan["shapes"])
        print(
            f"Validated manual transform published: {plan['output']}. Alignment accuracy remains unverified."
        )
        return 0
    except (*ARTIFACT_ERRORS, RuntimeError, ImportError) as exc:
        print(f"Registration failed: {exc}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print(
            "Registration interrupted; no final transform was published.",
            file=sys.stderr,
        )
        return 130


if __name__ == "__main__":
    raise SystemExit(main())
