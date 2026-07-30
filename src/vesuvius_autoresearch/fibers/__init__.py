"""GPU-native fiber / ridge / vesselness detection (vendored, villa PR #1033)."""

from vesuvius_autoresearch.fibers.detection import (
    compute_eigenvalues_3x3_batch,
    compute_eigenvectors_3x3_batch,
    detect_ridges,
    detect_ridges_tiled,
    detect_vesselness,
    detect_vesselness_tiled,
    fiber_direction,
    hessian,
    symmetrize_upper,
)

__all__ = [
    "compute_eigenvalues_3x3_batch",
    "compute_eigenvectors_3x3_batch",
    "detect_ridges",
    "detect_vesselness",
    "detect_ridges_tiled",
    "detect_vesselness_tiled",
    "fiber_direction",
    "hessian",
    "symmetrize_upper",
]
