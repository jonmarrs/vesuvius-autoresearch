"""Inference conventions shared with training, importable without torch.

Training reads num_layers + 2 * DEPTH_MARGIN slices, computes the ridge channel
over all of them, and gives the model num_layers of them: validation the centre
(offset DEPTH_MARGIN), training a random offset below 2 * DEPTH_MARGIN. The ridge
filter min-max normalizes the block it is given, so ridges computed over the
num_layers slices alone are a different input.

The recipe strings are recorded in inference metadata, so outputs made under
other recipes (the QC gate before 2026-10-13, window-only ridges) can be told
apart by tools that compare them.
"""

DEPTH_MARGIN = 4
INK_PROBABILITY = "sigmoid(ink)"


def ridge_depth_context(use_ridges):
    """How the ridge channel's depth context was read, for recorded recipes."""
    if not use_ridges:
        return "none (no ridge channel)"
    return (
        f"up to num_layers + {2 * DEPTH_MARGIN} slices, window centred where the "
        "volume allows"
    )
