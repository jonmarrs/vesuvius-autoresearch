"""Fetch the level-0 chunks of the surface prediction that the recipe's snap can read for a set of windings.

Usage: snap_chunks.py MESHES_DIR WINDINGS.txt SURF_ZARR KEY_PREFIX MANIFEST.json [--max-off 15] [--offline]

The recipe's snap_meshes.py samples the binary surface prediction at level 0 along each node's normal,
up to --max-off voxels either way, and reads whole chunks. Only band chunks of level 1 were downloaded
for the distance field, so the level-0 chunks around the chosen windings are fetched here.

A zarr chunk that is missing on disk reads as zeros, and zeros mean "no sheet here" to the snap. So a
chunk that was needed but never fetched would move no node and raise no error. This script therefore
separates the two cases and writes them down:

  fetched            listed in the public bucket, now on disk at the listed size
  absent_in_bucket   not listed in the bucket: the array has no data there, zeros are the true value

and exits 1 unless every needed chunk is one or the other. The needed set is every chunk touched by the
box of (max-off + 1) voxels around every existing node, which contains every point the snap can sample
(its samples lie within max-off of the node and are rounded to the nearest voxel).

--offline does no network access: it recomputes the needed set and checks it against MANIFEST.json and
the files on disk. run_snap.sh calls it that way immediately before the snap.

Anonymous HTTPS listing and GET only; nothing is uploaded.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))

LEVEL = 0


def read_windings(path: Path) -> list[str]:
    return [
        line.strip()
        for line in path.read_text().splitlines()
        if line.strip() and not line.startswith("#")
    ]


def needed_chunks(
    nodes_zyx: np.ndarray,
    shape: tuple[int, int, int],
    chunks: tuple[int, int, int],
    reach: float,
) -> set[tuple[int, int, int]]:
    """Chunk indices touched by the cube of half-width `reach` around every node, clipped to the array.

    The cube is narrower than a chunk, so its eight corners find every chunk it touches.
    """
    if reach * 2 >= min(chunks):
        raise ValueError("the reach must be less than half a chunk")
    shape_a = np.asarray(shape)
    chunks_a = np.asarray(chunks)
    out: set[tuple[int, int, int]] = set()
    for dz in (-reach, reach):
        for dy in (-reach, reach):
            for dx in (-reach, reach):
                corner = np.rint(nodes_zyx + np.array([dz, dy, dx])).astype(np.int64)
                corner = np.clip(corner, 0, shape_a - 1)
                index = np.unique(corner // chunks_a, axis=0)
                out.update((int(z), int(y), int(x)) for z, y, x in index)
    return out


def load_nodes(meshes: Path, windings: list[str]) -> np.ndarray:
    import tifffile

    parts = []
    for name in windings:
        folder = meshes / name
        x, y, z = (
            tifffile.imread(str(folder / f"{a}.tif")).astype(np.float64) for a in "xyz"
        )
        valid = (
            (x > -0.5)
            & (y > -0.5)
            & (z > -0.5)
            & np.isfinite(x)
            & np.isfinite(y)
            & np.isfinite(z)
        )
        if not valid.any():
            raise SystemExit(f"{folder} has no nodes")
        parts.append(np.stack([z[valid], y[valid], x[valid]], axis=1))
    return np.concatenate(parts)


def chunk_key(prefix: str, index: tuple[int, int, int]) -> str:
    return f"{prefix}/{LEVEL}/{index[0]}/{index[1]}/{index[2]}"


def classify(
    needed: set[tuple[int, int, int]], listed: dict[str, int], prefix: str
) -> tuple[dict[str, int], list[str]]:
    """Split the needed chunks into those the bucket lists (key -> size) and those it does not."""
    present: dict[str, int] = {}
    absent: list[str] = []
    for index in sorted(needed):
        key = chunk_key(prefix, index)
        if key in listed:
            present[key] = listed[key]
        else:
            absent.append(key)
    return present, absent


def check_on_disk(
    present: dict[str, int], strip: str, dest: Path
) -> list[tuple[str, str]]:
    """Listed chunks that are not on disk at their listed size."""
    bad = []
    for key, size in present.items():
        path = dest / key[len(strip) :]
        if not path.is_file():
            bad.append((key, "not on disk"))
        elif path.stat().st_size != size:
            bad.append((key, f"{path.stat().st_size} bytes on disk, listed {size}"))
    return bad


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("meshes", type=Path)
    parser.add_argument("windings", type=Path)
    parser.add_argument(
        "surf", type=Path, help="local copy of the surface zarr (its root)"
    )
    parser.add_argument("prefix", help="bucket key of the surface zarr's root")
    parser.add_argument("manifest", type=Path)
    parser.add_argument("--max-off", type=int, default=15)
    parser.add_argument("--offline", action="store_true")
    args = parser.parse_args(argv)

    prefix = args.prefix.rstrip("/")
    strip = prefix.rsplit("/", 1)[0] + "/"
    dest = args.surf.resolve().parent
    if args.surf.name != prefix.rsplit("/", 1)[1]:
        raise SystemExit("the local zarr and the bucket key must end in the same name")
    array_meta = args.surf / str(LEVEL) / ".zarray"

    if not args.offline:
        import s3_fetch

        status, _ = s3_fetch.fetch(str(dest), strip, f"{prefix}/{LEVEL}/.zarray", None)
        if status not in ("got", "kept"):
            raise SystemExit(f"cannot fetch the level-{LEVEL} array metadata: {status}")
    meta = json.loads(array_meta.read_text())
    if meta.get("dimension_separator") != "/" or meta.get("fill_value") != 0:
        raise SystemExit(f"{array_meta}: expected '/' chunk keys and a fill value of 0")
    shape, chunks = tuple(meta["shape"]), tuple(meta["chunks"])

    windings = read_windings(args.windings)
    nodes = load_nodes(args.meshes, windings)
    needed = needed_chunks(nodes, shape, chunks, args.max_off + 1.0)

    if args.offline:
        manifest = json.loads(args.manifest.read_text())
        present = manifest["fetched"]
        known = set(present) | set(manifest["absent_in_bucket"])
        unknown = [
            chunk_key(prefix, i)
            for i in sorted(needed)
            if chunk_key(prefix, i) not in known
        ]
        bad = check_on_disk(present, strip, dest)
        for key in unknown[:10]:
            print(f"NOT IN THE MANIFEST {key}")
        for key, why in bad[:10]:
            print(f"BAD {key} {why}")
        print(
            f"offline check: {len(needed)} chunks needed, {len(unknown)} not in the manifest, "
            f"{len(bad)} listed but wrong on disk"
        )
        return 1 if unknown or bad else 0

    import s3_plan

    listed: dict[str, int] = {}
    for z in sorted({index[0] for index in needed}):
        listed.update(s3_plan.list_prefix(f"{prefix}/{LEVEL}/{z}/"))
    present, absent = classify(needed, listed, prefix)
    print(
        f"{len(needed)} chunks needed: {len(present)} listed "
        f"({sum(present.values()) / 1e9:.3f} GB), {len(absent)} not in the bucket",
        flush=True,
    )
    with ThreadPoolExecutor(s3_fetch.THREADS) as pool:
        results = list(
            pool.map(
                lambda item: (item[0], s3_fetch.fetch(str(dest), strip, *item)),
                present.items(),
            )
        )
    failed = [
        (key, status) for key, (status, _) in results if status not in ("got", "kept")
    ]
    bad = failed + check_on_disk(present, strip, dest)
    manifest = {
        "surface": prefix,
        "level": LEVEL,
        "shape": list(shape),
        "chunks": list(chunks),
        "windings": windings,
        "meshes": str(args.meshes),
        "max_off": args.max_off,
        "needed": len(needed),
        "fetched": present,
        "absent_in_bucket": absent,
        "bytes": sum(present.values()),
        "complete": not bad,
    }
    os.makedirs(args.manifest.parent, exist_ok=True)
    args.manifest.write_text(json.dumps(manifest, indent=1) + "\n")
    for key, why in bad[:20]:
        print(f"BAD {key} {why}")
    print(f"SNAP_CHUNKS_{'OK' if not bad else 'INCOMPLETE'} {args.manifest}")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
