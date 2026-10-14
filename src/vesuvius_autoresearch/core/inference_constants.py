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


# config.json's relative paths are relative to the checkout the loop trains in.
_REPO = os.path.dirname(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
)


def _volume_keys(uri, bases):
    """Comparable spellings of one volume: resolved against each base directory,
    file:// as its path, and an OME-Zarr group the same as its level 0 array
    (FastVesuviusVolume opens either)."""
    parts = urlsplit(uri)
    if parts.scheme and parts.scheme != "file":
        uri = uri.rstrip("/")
        return {uri[:-2] if uri.endswith("/0") else uri}
    path = parts.path if parts.scheme == "file" else uri
    keys = set()
    for base in bases:
        resolved = os.path.realpath(os.path.join(base, path))
        if os.path.basename(resolved) == "0":
            resolved = os.path.dirname(resolved)
        keys.add(resolved)
    return keys


def depth_band_for(saved_config, volume_uri):
    """The checkpoint's depth_band for volume_uri, or None (the whole depth).

    A band names slices of the volumes it was set for: the training fragments'
    zarrs start at surface-volume layer 16 (finding 87), so [1, 27) there is
    layers 17-42. A volume built another way numbers its slices differently, so
    the same numbers would name other layers, or lie past a shallower volume.
    The band therefore applies only to the labeled volumes the checkpoint
    recorded (uri, uris, val_uri); recorded relative paths resolve against the
    working directory or this checkout. unlabeled_uris are left out: UA-MT
    bands an unlabeled volume only when it is one of these (train.unlabeled_dataset
    applies this function) and reads any other over its whole depth.
    """
    band = saved_config.get("depth_band")
    if not band:
        return None
    if (
        not isinstance(band, (list, tuple))
        or len(band) != 2
        or not all(isinstance(v, int) and not isinstance(v, bool) for v in band)
    ):
        raise ValueError(f"checkpoint depth_band must be [start, end), not {band!r}")
    recorded = []
    for key in ("uri", "uris", "val_uri"):
        value = saved_config.get(key)
        recorded.extend([value] if isinstance(value, str) else value or [])
    target = _volume_keys(str(volume_uri), [os.getcwd()])
    if any(
        isinstance(uri, str)
        and uri
        and target & _volume_keys(uri, [os.getcwd(), _REPO])
        for uri in recorded
    ):
        return [band[0], band[1]]
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
