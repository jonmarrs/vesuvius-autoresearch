"""One centered depth-window rule for raw and extracted SOTA data."""

from numbers import Integral


def depth_window(depth, count, center=None):
    """Return [start, stop); explicit centers must fit without clipping.

    The default is floor((depth - count) / 2). For a supplied center, that
    plane occupies position count // 2 in the window.
    """
    for name, value, minimum in (("depth", depth, 1), ("count", count, 1)):
        if (
            not isinstance(value, Integral)
            or isinstance(value, bool)
            or value < minimum
        ):
            raise ValueError(f"{name} must be a positive integer")
    depth, count = int(depth), int(count)
    if count > depth:
        raise ValueError(f"need >= {count} depth layers, got {depth}")
    if center is None:
        start = (depth - count) // 2
    else:
        if not isinstance(center, Integral) or isinstance(center, bool):
            raise ValueError("center must be an integer depth index")
        start = int(center) - count // 2
        if start < 0 or start + count > depth:
            raise ValueError(
                "requested center cannot supply the whole depth window; no clipping is performed"
            )
    return start, start + count
