"""Explicit numeric geometry declarations and pinned transform validation."""

from pathlib import Path

import numpy as np

from scripts.validate_prize_artifact import _load_json

REPO_ROOT = Path(__file__).resolve().parents[1]
REGISTRATION_DIR = REPO_ROOT / "villa/foundation/volume-registration"


def finite_coordinates(values, name, *, positive=False):
    if len(values) != 3 or any(isinstance(value, (bool, np.bool_)) for value in values):
        raise ValueError(f"{name} must contain three real numbers")
    if np.iscomplexobj(values):
        raise ValueError(f"{name} must contain real coordinates")
    result = np.asarray(values, dtype=np.float64)
    if (
        result.shape != (3,)
        or not np.isfinite(result).all()
        or (positive and np.any(result <= 0))
    ):
        raise ValueError(
            f"{name} must contain three finite {'positive ' if positive else ''}numbers"
        )
    return result


def voxel_size(value):
    return float(finite_coordinates([value] * 3, "voxel size", positive=True)[0])


def validate_transform(path, fixed, fixed_shape, moving_shape):
    # Reuse the pinned format authority rather than inventing a JSON layout.
    import jsonschema

    data = _load_json(path)
    schema = _load_json(REGISTRATION_DIR / "transform_schema.json")
    try:
        jsonschema.validate(data, schema)
    except jsonschema.ValidationError as exc:
        raise ValueError(
            f"transform disagrees with pinned schema: {exc.message}"
        ) from exc
    matrix = np.asarray(data["transformation_matrix"], dtype=np.float64)
    if not np.isfinite(matrix).all() or np.linalg.matrix_rank(matrix[:, :3]) != 3:
        raise ValueError("transform must be a finite, nonsingular 3x4 XYZ affine")
    if data["fixed_volume"] != Path(fixed).stem:
        raise ValueError("saved transform identifies a different fixed volume")
    fixed_points, moving_points = [], []
    for name, shape, target in (
        ("fixed_landmarks", fixed_shape, fixed_points),
        ("moving_landmarks", moving_shape, moving_points),
    ):
        for point in data[name]:
            values = finite_coordinates(point, name)
            if np.any(values < 0) or np.any(values >= np.asarray(shape[::-1])):
                raise ValueError(
                    f"{name} must fit inside its source volume in XYZ order"
                )
            target.append(values)
    if len(fixed_points) != len(moving_points):
        raise ValueError("fixed and moving landmark counts must match")
    return data
