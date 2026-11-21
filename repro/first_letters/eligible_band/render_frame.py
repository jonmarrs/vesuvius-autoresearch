"""Where a layer of the 66-layer render frame sits in a centred render of fewer layers.

The renderer (vc_render_tifxyz, sampler 75c79ac5f) places layer i of an n-layer render at (i - (n - 1) / 2) along
the normal, so a render of an even n layers holds layers (66 - n) / 2 to (66 + n) / 2 - 1 of the 66-layer one, at
the same offsets. Finding 129's amendment 1 checked them byte-identical on three of PHerc. 0826's windings, flipped and not.
"""

from __future__ import annotations

FRAME = 66


def frame_index(n: int, k: int) -> int:
    """The index in an n-layer centred render of layer k of the 66-layer frame; ValueError if it is not there."""
    if n <= 0 or n > FRAME or n % 2:
        raise ValueError(
            f"a centred render in the {FRAME}-layer frame has an even count up to {FRAME}, not {n}"
        )
    index = k - (FRAME - n) // 2
    if not 0 <= index < n:
        raise ValueError(
            f"layer {k} is not in a {n}-layer render (it holds {(FRAME - n) // 2} to {(FRAME + n) // 2 - 1})"
        )
    return index
