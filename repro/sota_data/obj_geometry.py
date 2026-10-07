"""Read the vertex/UV correspondence of an OBJ, including face texture indices."""

import hashlib
import os
import tempfile

import numpy as np


def fetch_obj(obj):
    """Cache a remote mesh by its complete S3 key and publish only finished downloads."""
    obj = os.fspath(obj)
    if not obj.startswith("s3://") and not obj.startswith("vesuvius-challenge"):
        return obj
    import s3fs

    key = obj.removeprefix("s3://")
    identity = hashlib.sha256(key.encode()).hexdigest()
    dst = os.path.join("local_data/rendered_obj", identity, os.path.basename(key))
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst):
        fd, staged = tempfile.mkstemp(prefix=".download-", dir=os.path.dirname(dst))
        os.close(fd)
        try:
            s3fs.S3FileSystem(anon=True).get(key, staged)
            if os.path.getsize(staged) == 0:
                raise ValueError(f"downloaded OBJ is empty: {key}")
            os.replace(staged, dst)
        finally:
            if os.path.exists(staged):
                os.unlink(staged)
    return dst


def read_obj_uv(path):
    vertices, uvs, pairs = [], [], {}
    with open(path) as stream:
        for line in stream:
            fields = line.split("#", 1)[0].split()
            if not fields:
                continue
            if fields[0] == "v":
                if len(fields) < 4:
                    raise ValueError("OBJ vertex requires three coordinates")
                vertices.append([float(x) for x in fields[1:4]])
            elif fields[0] == "vt":
                if len(fields) < 3:
                    raise ValueError("OBJ texture vertex requires two coordinates")
                uvs.append([float(x) for x in fields[1:3]])
            elif fields[0] == "f":
                if len(fields) < 4:
                    raise ValueError("OBJ face requires at least three vertices")
                for token in fields[1:]:
                    indices = token.split("/")
                    if len(indices) < 2 or not indices[1]:
                        raise ValueError("OBJ faces must include texture indices")
                    vi, ti = int(indices[0]), int(indices[1])
                    vi = vi - 1 if vi > 0 else len(vertices) + vi if vi < 0 else -1
                    ti = ti - 1 if ti > 0 else len(uvs) + ti if ti < 0 else -1
                    if not 0 <= vi < len(vertices) or not 0 <= ti < len(uvs):
                        raise ValueError("OBJ face vertex/texture index out of bounds")
                    if ti in pairs and vertices[pairs[ti]] != vertices[vi]:
                        raise ValueError("OBJ UV maps to multiple 3D vertices")
                    pairs[ti] = vi
    if pairs:
        ordered = sorted(pairs)
        v = np.asarray([vertices[pairs[i]] for i in ordered], np.float64)
        vt = np.asarray([uvs[i] for i in ordered], np.float64)
    else:
        # Legacy point-cloud fixtures and positionally paired mesh exports.
        if len(vertices) != len(uvs):
            raise ValueError(
                "OBJ without faces requires positionally paired v/vt arrays"
            )
        v, vt = np.asarray(vertices, np.float64), np.asarray(uvs, np.float64)
    return v, vt
