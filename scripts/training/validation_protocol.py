"""Validation protocol metadata shared by planning and promotion, without arrays."""

from __future__ import annotations

VALIDATION_PROTOCOL = "seeded-sample-400-v3"
# The same draw scored on its ink-containing patches only; kept so finding 86's
# and 88's measurements of it can be reproduced.
INK_ONLY_PROTOCOL = "seeded-sample-400-v2"
VALIDATION_SAMPLE_PATCHES = 400
VALIDATION_SAMPLE_SEED = 42


def validation_protocol(depth_band=None, base: str = VALIDATION_PROTOCOL) -> str:
    """The protocol a score is measured under. The depth band is part of it: the
    same patches read from other slices are a different sample. ``base`` is
    INK_ONLY_PROTOCOL only to reproduce a v2 measurement."""
    if depth_band is None:
        return base
    start, end = depth_band
    return f"{base}+z{start}-{end}"
