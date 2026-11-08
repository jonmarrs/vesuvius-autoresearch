"""Smoke for finding 107's run, from finding 106's cached fields (no prediction).

Builds, for the zone's cube, a 1088³ context whose core is the cube's CT and whose ring is 1 (not 0, so no exterior
black), and caches each block's field as finding 106's one-block field of the cube placed at [288, 800), zero
elsewhere. The blocks' read borders then fall where finding 106's blocks of 256 had theirs, so run() should reproduce
the record's arm `same` rows (8 blocks cut from one field), main and patched.

The smoke ran before finding 107's registration was pushed; its result.json is
reports/evidence/afv_generator_default_zone_smoke_2026-11-08.json.

Usage (the generator's venv): python -I scripts/afv_generator_default_zone_smoke.py WORK, then
  scripts/afv_generator_default_zone.py run --context WORK/context.npy --work WORK ... (as for the zone itself)
"""

import sys
from pathlib import Path

import numpy as np
import zarr

work = Path(sys.argv[1])
sys.path.insert(0, str(Path(__file__).resolve().parent))
import afv_generator_default_zone as dz  # noqa: E402

work.mkdir(parents=True, exist_ok=True)
own = np.asarray(zarr.open(str(dz.bs.CT / f"{dz.CUBE}.zarr"), mode="r")[:])
ctx = np.ones((dz.SIDE,) * 3, np.uint8)
c = slice(dz.PAD, dz.PAD + dz.SIZE)
ctx[c, c, c] = own
np.save(work / "context.npy", ctx)
del ctx
one = np.load(
    Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out/afv_gen/block_seams")
    / dz.CUBE
    / "prob_one.npy",
    mmap_mode="r",
)


class Cli:
    @staticmethod
    def zone_blocks(
        origin_xyz, size_xyz, block
    ):  # the #1934 head's, as tests/test_afv_generator_default_zone.py reads it
        axes = [
            [(o + start, min(block, s - start)) for start in range(0, s, block)]
            for o, s in zip(origin_xyz, size_xyz, strict=True)
        ]
        return [
            ([x, y, z], [sx, sy, sz])
            for z, sz in axes[2]
            for y, sy in axes[1]
            for x, sx in axes[0]
        ]


for i, (_, _, low, high) in enumerate(dz.block_crops(Cli, np.full(3, dz.SIDE))):
    lo, hi = low[::-1], high[::-1]  # z, y, x
    field = np.zeros((*(hi - lo), 3), np.uint8)
    a, b = np.maximum(lo, dz.PAD), np.minimum(hi, dz.PAD + dz.SIZE)
    if np.all(b > a):
        field[
            tuple(
                slice(int(x - s0), int(y - s0))
                for x, y, s0 in zip(a, b, lo, strict=True)
            )
        ] = one[
            tuple(
                slice(int(x - dz.PAD), int(y - dz.PAD))
                for x, y in zip(a, b, strict=True)
            )
        ]
    np.save(work / f"prob_block_{i}.npy", field)
    print(i, lo, hi, "cube part", a - dz.PAD, b - dz.PAD, flush=True)
