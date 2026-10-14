"""Inference conventions shared with training, importable without torch.

Training reads num_layers + 2 * DEPTH_MARGIN slices, computes the ridge channel
over all of them, and gives the model num_layers of them: validation the centre
(offset DEPTH_MARGIN), training a random offset below 2 * DEPTH_MARGIN. The ridge
filter min-max normalizes the block it is given, so ridges computed over the
num_layers slices alone are a different input.

The recipe strings are recorded in inference metadata, so outputs made under
other recipes (the QC gate before 2026-10-13, window-only ridges) can be told
apart by tools that compare them.

A checkpoint's depth_band is likewise a convention of its own volumes; see
depth_band_for.
"""

import os
import sys
from urllib.parse import urlsplit

DEPTH_MARGIN = 4
INK_PROBABILITY = "sigmoid(ink)"


def _same_volume(a, b):
    if urlsplit(a).scheme or urlsplit(b).scheme:
        return a.rstrip("/") == b.rstrip("/")
    return os.path.realpath(a) == os.path.realpath(b)


def depth_band_for(saved_config, volume_uri):
    """The checkpoint's depth_band for volume_uri, or None (the whole depth).

    A band names slices of the volumes it was set for: the training fragments'
    zarrs start at surface-volume layer 16 (finding 87), so [1, 27) there is
    layers 17-42. A volume built another way numbers its slices differently, so
    the same numbers would name other layers, or lie past a shallower volume.
    The band therefore applies only to the volumes the checkpoint recorded
    (uri, uris, val_uri, unlabeled_uris; relative paths resolve against the
    working directory).
    """
    band = saved_config.get("depth_band")
    if band is None:
        return None
    recorded = [
        saved_config.get("uri"),
        *(saved_config.get("uris") or []),
        saved_config.get("val_uri"),
        *(saved_config.get("unlabeled_uris") or []),
    ]
    if any(
        isinstance(uri, str) and uri and _same_volume(uri, str(volume_uri))
        for uri in recorded
    ):
        return [int(band[0]), int(band[1])]
    print(
        f"depth_band {list(band)} is in the slice numbers of the checkpoint's own "
        f"volumes; {volume_uri} is not one of them, so the band is not applied",
        file=sys.stderr,
    )
    return None


def ridge_depth_context(use_ridges):
    """How the ridge channel's depth context was read, for recorded recipes."""
    if not use_ridges:
        return "none (no ridge channel)"
    return (
        f"up to num_layers + {2 * DEPTH_MARGIN} slices, window centred where the "
        "volume allows"
    )
