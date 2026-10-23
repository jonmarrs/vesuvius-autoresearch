"""Compare Villa's actual CPU seed functions before/after a plane-spacing fix.

Uses the three published ScrollGT v0.8.1 masks listed below, averaged 2x2x2
and scaled to uint8 presence. This validates seeding, not tracing quality.
Only NumPy and SciPy are needed: the four seed functions and their constants
are compiled directly from the supplied source files, without importing the
unrelated model/runtime dependencies of volume.py. No seed algorithm is copied.
See reports/villa_fractional_plane_spacing_2026-10-20.md for commands.
"""
from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import scipy
from scipy import ndimage

MASKS = {
    "s1": ("s1_00497_01497_03997_256", "3263fbe85731bdf934b86004f78593be96791155e17edbffd35aa105886d5b4a"),
    "s3": ("s3_00994_00494_01994_512", "2f88aa371ef55f12d25fc4659380bf804131473a5bdcd1ee3eadaf957429d1ee"),
    "s5": ("s5_03997_01497_03997_256", "577b09ee7fb527b3b3d46ac355985351cb61e4db906a9c5159f50b1638fb3498"),
}


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_seeding(source):
    functions = {"unit", "_hessian_kernels", "ridge_directions", "tile_dots"}
    constants = {"HESSIAN_SIGMA", "HESSIAN_RADIUS", "_KERNELS"}
    nodes = []
    found = set()
    for node in ast.parse(source.read_text()).body:
        if isinstance(node, ast.FunctionDef) and node.name in functions:
            nodes.append(node)
            found.add(node.name)
        elif isinstance(node, ast.Assign):
            names = {n.id for t in node.targets for n in ast.walk(t) if isinstance(n, ast.Name)}
            if names & constants:
                nodes.append(node)
                found.update(names & constants)
    if found != functions | constants:
        raise ValueError(f"Seed functions/constants changed in {source}: {sorted(found)}")
    namespace = {"np": np, "ndimage": ndimage}
    exec(compile(ast.Module(body=nodes, type_ignores=[]), str(source), "exec"), namespace)
    return SimpleNamespace(**namespace)


def presence_from_mask(path):
    with np.load(path, allow_pickle=False) as saved:
        shape = tuple(int(v) for v in saved["shape"])
        mask = np.unpackbits(saved["packed"])[:int(np.prod(shape))].reshape(shape)
    z, y, x = (v // 2 for v in shape)
    presence = np.rint(mask.reshape(z, 2, y, 2, x, 2).mean(axis=(1, 3, 5))*255).astype("u1")
    return shape, presence


def describe(dots):
    return {
        "dots": len(dots["xyz"]),
        "plane_dots": int((dots["plane"] != "fill").sum()),
        "fill_dots": int((dots["plane"] == "fill").sum()),
        "planes": sorted(str(v) for v in set(dots["plane"]) - {"fill"}),
        "array_sha256": {k: hashlib.sha256(v.tobytes()).hexdigest() for k, v in dots.items()},
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--before", type=Path, required=True, help="baseline Villa volume.py")
    ap.add_argument("--after", type=Path, required=True, help="patched Villa volume.py")
    ap.add_argument("--data", type=Path, required=True, help="s1_mask.npz, s3_mask.npz and s5_mask.npz")
    ap.add_argument("--out", type=Path, required=True, help="new JSON evidence file")
    args = ap.parse_args()
    if args.out.exists():
        raise FileExistsError(args.out)
    before, after = load_seeding(args.before), load_seeding(args.after)
    rows = []
    for scroll, (cube, expected_hash) in MASKS.items():
        mask = args.data / f"{scroll}_mask.npz"
        if sha256(mask) != expected_hash:
            raise ValueError(f"{mask}: not the published ScrollGT v0.8.1 mask")
        shape, presence = presence_from_mask(mask)
        for spacing in (64., 64*7.91/9.6, 64*9.6/7.91):
            settings = SimpleNamespace(threshold=128., dot_radius=2., fill_spacing=4., plane_spacing=spacing)
            old, new = (v.tile_dots(presence, np.zeros(3), np.array(presence.shape[::-1], float), settings)
                        for v in (before, after))
            identical = old.keys() == new.keys() and all(
                old[k].shape == new[k].shape and old[k].dtype == new[k].dtype
                and old[k].tobytes() == new[k].tobytes() for k in old
            )
            if spacing == 64. and not identical:
                raise ValueError(f"{cube}: default seed arrays changed")
            row = dict(cube=cube, mask_shape=shape, mask_sha256=expected_hash, spacing=spacing,
                       before=describe(old), after=describe(new), identical=identical)
            rows.append(row)
            print(f"{cube} spacing={spacing:.9f}: {row['before']['dots']} -> {row['after']['dots']}; "
                  f"all seed arrays identical={identical}", flush=True)
    result = dict(scope="CPU seeding only; thresholded model masks, not findings 91/92 probability volumes",
                  data_release="https://github.com/jonmarrs/scrollgt/tree/v0.8.1",
                  preprocessing="2x2x2 block mean of binary mask, round(255*mean) to uint8",
                  numpy=np.__version__, scipy=scipy.__version__,
                  before_source_sha256=sha256(args.before), after_source_sha256=sha256(args.after), rows=rows)
    args.out.write_text(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
