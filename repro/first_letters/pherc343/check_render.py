"""Compare a 66-layer render with the hashes the published PHerc. 343 sidecar records.

Usage: check_render.py RENDER.zarr SIDECAR.json OUT.json

Rules, copied from the sidecar:
  tree_rule       sha256 of the sorted lines "<relative path>\\t<sha256>\\n" of every file in the folder
  area_data_note  sha256 of the decoded uint8 layers (raw orientation, area only, C order) and of
                  np.packbits(valid mask); valid_rule: all 66 layers > 0
The tree hash also covers compression and metadata bytes, so it can differ while the decoded voxels
are identical; the decoded hashes are the ones that decide whether the render is the same picture.
"""

import hashlib
import json
import os
import sys

import numpy as np
import zarr


def sha256_file(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def tree_hash(root: str) -> tuple[str, int, int]:
    lines = []
    total = 0
    for folder, _, names in os.walk(root):
        for name in names:
            path = os.path.join(folder, name)
            total += os.path.getsize(path)
            lines.append(f"{os.path.relpath(path, root)}\t{sha256_file(path)}\n")
    lines.sort()
    return hashlib.sha256("".join(lines).encode()).hexdigest(), len(lines), total


def main() -> int:
    render, sidecar_path, out_path = sys.argv[1:4]
    sidecar = json.load(open(sidecar_path))
    ct = sidecar["ct"]
    area = sidecar["area"]["raw_render_px"]
    rows = slice(area["row0"], area["row1"])
    cols = slice(area["col0"], area["col1"])

    group = zarr.open(render, mode="r")
    array = group["0"] if not hasattr(group, "shape") else group
    result: dict = {
        "render": render,
        "shape": list(array.shape),
        "dtype": str(array.dtype),
        "shape_matches": list(array.shape) == list(ct["shape"]),
    }

    valid = None
    layer_hashes = {}
    wanted = {int(k): v for k, v in ct["area_layers_sha256"].items()}
    for layer in range(array.shape[0]):
        data = np.ascontiguousarray(array[layer, rows, cols])
        if data.dtype != np.uint8:
            raise SystemExit(f"layer {layer} dtype {data.dtype}, expected uint8")
        positive = data > 0
        valid = positive if valid is None else (valid & positive)
        if layer in wanted:
            layer_hashes[layer] = hashlib.sha256(data.tobytes(order="C")).hexdigest()
    assert valid is not None
    mask_hash = hashlib.sha256(np.packbits(valid).tobytes()).hexdigest()

    result["area_layers_sha256"] = {
        str(k): {
            "ours": layer_hashes[k],
            "published": wanted[k],
            "match": layer_hashes[k] == wanted[k],
        }
        for k in sorted(wanted)
    }
    result["area_valid_mask_sha256"] = {
        "ours": mask_hash,
        "published": ct["area_valid_mask_sha256"],
        "match": mask_hash == ct["area_valid_mask_sha256"],
    }
    result["area_valid_fraction"] = {
        "ours": round(float(valid.mean()), 4),
        "published": sidecar["area"]["valid_fraction"],
    }
    tree, files, size = tree_hash(render)
    result["tree"] = {
        "ours": {"sha256": tree, "files": files, "bytes": size},
        "published": {
            "sha256": ct["tree_sha256"],
            "files": ct["files"],
            "bytes": ct["bytes"],
        },
        "match": tree == ct["tree_sha256"],
    }
    result["decoded_voxels_identical_where_published"] = bool(
        all(v["match"] for v in result["area_layers_sha256"].values())
        and result["area_valid_mask_sha256"]["match"]
    )
    with open(out_path, "w") as handle:
        json.dump(result, handle, indent=2)
        handle.write("\n")
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
