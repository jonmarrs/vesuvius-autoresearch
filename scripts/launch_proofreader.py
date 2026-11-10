#!/usr/bin/env python3
"""Launch Villa's proofreader on aligned local 3D CT and categorical labels.

Regional ink probability and one-plane uncertainty maps require a separately
validated alignment/label conversion; they cannot be passed as full CT labels.
"""

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path
from tempfile import TemporaryDirectory

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "src")]


def generate_config(
    volume_path,
    predictions_path,
    config_out_path,
    *,
    patch_size=64,
    dataset_out_path="local_data/Proofread_Patches",
):
    """Write the pinned proofreader's scalar cubic-patch configuration."""
    if type(patch_size) is not int or patch_size < 1:
        raise ValueError("patch_size must be a positive integer")
    config = {
        "dataset_out_path": str(Path(dataset_out_path).resolve()),
        "patch_size": patch_size,
        "min_z": 0,
        "min_label_percentage": 1,
        "volumes": {
            "Autoresearch_Prediction": {
                "volume_path": str(Path(volume_path).resolve()),
                "label_path": str(Path(predictions_path).resolve()),
            }
        },
    }
    Path(config_out_path).write_text(json.dumps(config, indent=2) + "\n")
    return config_out_path


def _inputs(volume_path, predictions_path, output, patch_size):
    from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths
    from volume_cartographer_wrapper.volume import FastLocalVolume

    volume, labels = FastLocalVolume(volume_path), FastLocalVolume(predictions_path)
    if volume.shape != labels.shape:
        raise ValueError("CT and categorical labels must have the same 3D shape/grid")
    if labels.dtype.kind not in "bui":
        raise ValueError(
            "proofreader requires categorical integer labels; probability/entropy maps need conversion"
        )
    if any(size < patch_size for size in volume.shape):
        raise ValueError(
            "patch_size must fit every CT axis; select a smaller cubic patch"
        )
    if volume.path == labels.path:
        raise ValueError("CT and categorical labels must be distinct inputs")
    validate_plan_paths(
        [(output, "proofreader dataset")],
        [
            (volume.source_path, "CT source"),
            (volume.path, "CT array"),
            (labels.source_path, "label source"),
            (labels.path, "label array"),
        ],
    )
    return volume.path, labels.path


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--volume", required=True, help="local 3D CT Zarr")
    parser.add_argument(
        "--predictions", required=True, help="aligned categorical 3D label Zarr"
    )
    parser.add_argument("--patch-size", type=int, default=64, help="cubic patch edge")
    parser.add_argument(
        "--out-dir", type=Path, default=Path("local_data/Proofread_Patches")
    )
    args = parser.parse_args(argv)
    proofreader = ROOT / "villa/segmentation/vc_proofreader/main.py"
    try:
        if args.patch_size < 1:
            raise ValueError("patch_size must be a positive integer")
        if not proofreader.is_file():
            raise ValueError(
                "Villa proofreader missing; run git submodule update --init villa"
            )
        output = args.out_dir.resolve()
        if output.exists() and (not output.is_dir() or any(output.iterdir())):
            raise ValueError(
                "--out-dir must be new or empty; existing sessions need a verified resume configuration"
            )
        volume, labels = _inputs(args.volume, args.predictions, output, args.patch_size)
        with TemporaryDirectory(prefix="vesuvius-proofreader-") as temporary:
            config = Path(temporary) / "config.json"
            generate_config(
                volume,
                labels,
                config,
                patch_size=args.patch_size,
                dataset_out_path=output,
            )
            env = dict(os.environ)
            env["PYTHONPATH"] = os.pathsep.join(
                value for value in (str(ROOT / "villa"), env.get("PYTHONPATH")) if value
            )
            print(f"Launching VC Proofreader; approved patches go to {output}")
            print(
                "Press 'a' to toggle approval, then Space to save/advance.", flush=True
            )
            return subprocess.run(
                [sys.executable, str(proofreader), "--config", str(config)],
                env=env,
                cwd=ROOT,
                check=False,
            ).returncode
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Proofreader launch failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
