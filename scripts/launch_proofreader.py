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
    record_session=False,
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
    if record_session:
        from vesuvius_autoresearch.core.proofreader_session import recorded_config

        config = recorded_config(
            volume_path, predictions_path, dataset_out_path, patch_size
        )
    Path(config_out_path).write_text(json.dumps(config, indent=2) + "\n")
    return config_out_path


def _inputs(volume_path, predictions_path, output, patch_size, *, record_session=False):
    from vesuvius_autoresearch.core.prediction_artifacts import validate_plan_paths
    from vesuvius_autoresearch.core.proofreader_session import validate_input_arrays
    from volume_cartographer_wrapper.volume import (
        FastLocalVolume,
        local_volume_array_path,
        local_volume_path,
    )

    volume_source = local_volume_path(volume_path).resolve()
    label_source = local_volume_path(predictions_path).resolve()
    volume = local_volume_array_path(volume_source)
    labels = local_volume_array_path(label_source)
    validate_plan_paths(
        [(output, "proofreader dataset")],
        [
            (volume_source, "CT source"),
            (volume, "CT array"),
            (label_source, "label source"),
            (labels, "label array"),
        ],
    )
    # Recorded launches validate these arrays between hashing and the final inventory.
    if not record_session:
        validate_input_arrays(
            FastLocalVolume(volume), FastLocalVolume(labels), patch_size
        )
    return volume, labels


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
    parser.add_argument(
        "--record-session",
        action="store_true",
        help="hash bounded source trees and record initial inputs before GUI launch; does not enable resume",
    )
    parser.add_argument("--max-source-bytes", type=int, default=8 * 1024**3)
    parser.add_argument("--max-file-bytes", type=int, default=64 * 1024**2)
    parser.add_argument("--max-entries", type=int, default=100_000)
    args = parser.parse_args(argv)
    proofreader = ROOT / "villa/segmentation/vc_proofreader/main.py"
    try:
        from vesuvius_autoresearch.core.proofreader_session import limits

        budget = limits(
            max_source_bytes=args.max_source_bytes,
            max_file_bytes=args.max_file_bytes,
            max_entries=args.max_entries,
        )
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
        volume, labels = _inputs(
            args.volume,
            args.predictions,
            output,
            args.patch_size,
            record_session=args.record_session,
        )
        with TemporaryDirectory(prefix="vesuvius-proofreader-") as temporary:
            config = Path(temporary) / "config.json"
            generate_config(
                volume,
                labels,
                config,
                patch_size=args.patch_size,
                dataset_out_path=output,
                record_session=args.record_session,
            )
            if args.record_session:
                from vesuvius_autoresearch.core.proofreader_session import create_record

                record = create_record(
                    json.loads(config.read_bytes()), proofreader, budget
                )
                print(f"Initial input record: {record}")
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
