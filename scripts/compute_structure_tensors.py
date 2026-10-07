#!/usr/bin/env python3
"""Stage the pinned villa structure-tensor/eigenanalysis pipeline and its provenance."""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import (
    ARTIFACT_ERRORS,
    array_3d,
    separate_paths,
    spatial_blocks,
    staged_directory,
    tensor_arrays,
    tensor_settings,
)

VESUVIUS_SRC = REPO_ROOT / "villa/vesuvius/src"
RUN_SCRIPT = VESUVIUS_SRC / "vesuvius/structure_tensor/run_create_st.py"


def compute_structure_tensors(input_path, output_path, sigma=2.0, gpus="all", rho=None):
    if rho is not None:
        raise ValueError("--rho is unsupported by the pinned villa runner; use --sigma")
    tensor_settings(sigma, gpus)
    if not RUN_SCRIPT.is_file():
        raise FileNotFoundError(f"{RUN_SCRIPT} missing; initialize the villa submodule")
    input_path, output_path = separate_paths(input_path, output_path)
    source = array_3d(input_path)
    source_attrs = dict(source.attrs)
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        filter(None, (str(VESUVIUS_SRC), env.get("PYTHONPATH")))
    )
    with staged_directory(output_path) as staging:
        command = [
            sys.executable,
            str(RUN_SCRIPT),
            "--input_dir",
            str(input_path),
            "--output_dir",
            str(staging),
            "--sigma",
            str(sigma),
            "--gpus",
            gpus,
        ]
        print(f"Computing structure tensors from {input_path}", flush=True)
        subprocess.run(command, env=env, check=True, cwd=REPO_ROOT)
        root, arrays = tensor_arrays(staging, source.shape, mode="r+")
        if arrays[0].dtype.kind != "f" or any(
            array.dtype != np.dtype("uint8") for array in arrays[1:]
        ):
            raise ValueError("unexpected upstream structure tensor/eigenanalysis dtype")
        for selection in spatial_blocks(source.shape):
            if not np.isfinite(arrays[0][(slice(None), *selection)]).all():
                raise ValueError("upstream structure tensor contains nonfinite values")
            for array in arrays[1:]:
                array[selection]  # reject corrupt encoded payloads before publication
        if dict(array_3d(input_path).attrs) != source_attrs:
            raise RuntimeError(
                "source crop changed during structure tensor computation"
            )
        root.attrs["candidate_tensor_completion"] = {
            "contract": 1,
            "source_path": str(input_path),
            "source_crop": source_attrs,
            "sigma": sigma,
            "gpus": gpus,
            "upstream_script": str(RUN_SCRIPT),
        }
    print(f"Structure tensors and eigenanalysis published at {output_path}")
    return output_path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Input local 3D Zarr array")
    parser.add_argument("--output", required=True, help="Output structure tensor group")
    parser.add_argument("--sigma", type=float, default=2.0)
    parser.add_argument(
        "--rho",
        type=float,
        default=None,
        help="Unsupported legacy option; supplying it fails",
    )
    parser.add_argument("--gpus", default="all")
    args = parser.parse_args(argv)
    try:
        compute_structure_tensors(
            args.input, args.output, args.sigma, args.gpus, args.rho
        )
    except (*ARTIFACT_ERRORS, RuntimeError, subprocess.CalledProcessError) as exc:
        parser.exit(1, f"Structure tensor computation failed: {exc}\n")


if __name__ == "__main__":
    main()
