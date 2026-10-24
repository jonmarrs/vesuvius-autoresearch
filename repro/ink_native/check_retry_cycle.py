"""Check native retry termination on two empty regions of a published mesh.

This deliberately supplies two inadmissible patches, rather than invoking
patch discovery. Actual InkDataset methods and tifxyz geometry run; unused
volume handles are sentinels that forbid voxel reads. This checks the retry
consumer, not training or whether default discovery selects these patches.
Run in a configured Villa environment with its vesuvius/src on PYTHONPATH.

Exit status: 0 when the retry produces the expected native-crop RuntimeError
after exactly the two patches, 1 otherwise (including unrelated RuntimeErrors),
2 with "refused: ..." when the probe refuses to run (argparse's own usage
errors also exit 2). Any other
error, villa missing from PYTHONPATH among them, is a traceback and 1. It
refuses, before running and without writing, an output path that exists or
whose directory does not, a mesh that is missing a file or is not the
published one, surface in either corner, a patch villa does not reject, and a
platform without a POSIX interval timer; and it refuses a voxel read before
the geometry rejection whenever it happens.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import signal
import sys
import time
import warnings

from vesuvius.ink_detection.config import InkDataConfig
from vesuvius.ink_detection.data import dataset as dataset_module
from vesuvius.ink_detection.types import Patch, Segment
from vesuvius.tifxyz import read_tifxyz


HASHES = {
    "meta.json": "105c2716274077c3c832765ae6c0885cf679b2cbdef9f89a49875b1ee12fb84f",
    "x.tif": "4b39233839ab7e818ebd7bf12a4592655c705b9ed94771dc8590bf047b98ddca",
    "y.tif": "ee5c6e63339bc6698473381267dd0b04599c09897f14a2ea6d34b4e991c01d22",
    "z.tif": "a889c461f669567e85e7ab55936f0e5783eed28e019cf52303378c39997e6c27",
}


class Refused(Exception):
    """The probe cannot measure the retry on these inputs; exit 2."""


class NoVoxelReads:
    # villa's first touch of a volume it reads is `.shape`, then indexing
    def __getitem__(self, key):
        raise Refused("The geometry rejection must precede voxel reads")

    def __getattr__(self, name):
        raise Refused("The geometry rejection must precede voxel reads")


def main():
    try:
        return _probe()
    except Refused as error:
        print(f"refused: {error}", file=sys.stderr)
        return 2


def _probe():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--mesh", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    if not hasattr(signal, "setitimer"):
        raise Refused("This bounded probe requires a POSIX interval timer")
    # lexists: a dangling symlink is as much in the way as a file
    if os.path.lexists(args.out):
        raise Refused(f"{args.out} exists; records are never overwritten")
    if not args.out.parent.is_dir():
        raise Refused(f"{args.out.parent} is not a directory; nowhere to write the record")
    for name, expected in HASHES.items():
        if not (args.mesh / name).is_file():
            raise Refused(f"{name}: missing from {args.mesh}")
        if hashlib.sha256((args.mesh / name).read_bytes()).hexdigest() != expected:
            raise Refused(f"{name}: not the stated published Scroll-1 mesh")
    surface = read_tifxyz(args.mesh)
    surface.use_full_resolution()
    height, width = surface.shape
    corners = [(0, 0), (0, width - 64)]
    for y, x in corners:
        if surface[y:y+64, x:x+64][3].any():
            raise Refused(f"the 64x64 region at y={y}, x={x} has surface; two empty ones are needed")
    config = InkDataConfig.from_mapping({
        "mode": "full_3d", "patch_size": [17, 64, 64],
        "patch_overlap": 0.25, "patch_min_labeled_coverage": 0., "seed": 17,
        "datasets": [{"segments_path": str(args.mesh.parent),
                      "volume_path": "unused-volume", "volume_scale": 0}],
    })
    segment = Segment(
        data_config=config, source=config.datasets[0], dataset_idx=0,
        segment_relpath="mesh", segment_dir=args.mesh, segment_name="mesh",
        image_volume="unused-volume", inklabels=Path("unused-labels"),
        supervision_mask=Path("unused-supervision"),
    )
    patches = [Patch(segment, (0, y, x, 17, y+64, x+64)) for y, x in corners]
    data = dataset_module.InkDataset(config, do_augmentations=False, patches=patches)
    data._open = lambda *args: NoVoxelReads()
    data._tifxyz_cache[str(args.mesh)] = surface
    original_sample = data._native_sample
    if any(original_sample(patch) is not None for patch in patches):
        raise Refused("villa admits a supplied patch; the probe needs two it rejects")
    attempts = []

    def sample(patch):
        attempts.append(0 if patch is patches[0] else 1)
        return original_sample(patch)

    def deadline(signum, frame):
        raise TimeoutError("retry did not terminate within two seconds")

    data._native_sample = sample
    previous_handler = signal.signal(signal.SIGALRM, deadline)
    start = time.monotonic()
    outcome, message = "returned", ""
    try:
        signal.setitimer(signal.ITIMER_REAL, 2.)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            data[0]
    except TimeoutError as error:
        outcome, message = "timeout", str(error)
    except RuntimeError as error:
        outcome, message = "runtime_error", str(error)
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0.)
        signal.signal(signal.SIGALRM, previous_handler)
    # Two attempts alone can also precede an unrelated dataset failure. Only
    # the measured native retry error establishes bounded rejection here.
    expected_error = (
        "No admissible native crop after trying 2 distinct patches "
        "for requested idx 0 (dataset size 2); "
        "check the native crop size, surface geometry and supervision masks"
    )
    bounded = outcome == "runtime_error" and attempts == [0, 1] and message == expected_error
    result = dict(
        scope="deliberately supplied invalid mesh patches; no discovery, voxel reads or training",
        source_url="https://vesuvius-challenge-open-data.s3.amazonaws.com/PHercParis4/segments/20230702185753/mesh/20230702185753-on-20260411134726-2.4um.tifxyz/",
        input_sha256=HASHES, mesh_shape=[height, width], corners_yx=corners,
        dataset_source_sha256=hashlib.sha256(Path(dataset_module.__file__).read_bytes()).hexdigest(),
        outcome=outcome, message=message, attempt_count=len(attempts),
        first_attempts=attempts[:8], seconds=time.monotonic()-start, bounded=bounded,
    )
    with args.out.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    print(json.dumps(result, indent=2))
    return 0 if bounded else 1


if __name__ == "__main__":
    raise SystemExit(main())
