"""What a promotion compares: the validation sample and the incumbent's stored score.

Kept free of training imports (torch is imported lazily) so the loop controller can
check the incumbent before it starts a shift.

A candidate is promoted when its val_f1 beats the val_f1 stored in best_model.pt.
That is only meaningful when both were measured on the same patches. Protocol v1
read the first 100 *batches* of the validation catalogue in raster order: 400
patches at batch_size 4, 800 at 8, all from the top of the fragment, so a
batch_size tweak was scored on a different set from the incumbent. Protocol v2
scores a fixed, seeded sample spread over the whole catalogue, whatever the batch
size. A score from another protocol is not comparable and is refused, not
bootstrapped; ``scripts/reevaluate_best_model.py --update-stored`` re-scores it.

The protocol string names how the sample is drawn, not what it is drawn from:
another label file beside the fragment (``inklabels_refined.png`` is preferred
when present), mask, patch catalogue or validation fragment keeps the string and
changes the patches or targets. Each score therefore also records a fingerprint
of those inputs (``validation_diag["inputs_sha256"]``,
validation_inputs_fingerprint), and an incumbent whose fingerprint differs from
config.json's inputs is refused the same way, by the loop before each cycle and
by train.py before a promotion.
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import tempfile

import numpy as np

VALIDATION_PROTOCOL = "seeded-sample-400-v2"
VALIDATION_SAMPLE_PATCHES = 400
VALIDATION_SAMPLE_SEED = 42

RESCORE_COMMAND = "uv run python scripts/reevaluate_best_model.py --update-stored"


def validation_protocol(depth_band=None) -> str:
    """The protocol a score is measured under. The depth band is part of it: the
    same patches read from other slices are a different sample."""
    if depth_band is None:
        return VALIDATION_PROTOCOL
    start, end = depth_band
    return f"{VALIDATION_PROTOCOL}+z{start}-{end}"


# The label file validation reads: the first of these beside the volume.
VALIDATION_LABEL_FILES = (
    "inklabels_refined.png",
    "inklabels_filled.png",
    "inklabels.png",
)


def validation_label_path(val_uri: str) -> str:
    """The label file validation reads (inklabels.png when none exists)."""
    parent = os.path.dirname(val_uri.rstrip("/"))
    for name in VALIDATION_LABEL_FILES:
        path = os.path.join(parent, name)
        if os.path.exists(path):
            return path
    return path


def _file_sha256(path: str) -> str | None:
    if not os.path.isfile(path):
        return None
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def validation_inputs_fingerprint(val_uri: str, depth_band=None) -> str:
    """A sha256 of what the protocol's sample is drawn from.

    The protocol (sample size, seed, depth band); the fragment and volume names;
    the label file validation reads and its contents; the mask; and patches.json,
    which replaces the catalogue when present. Paths are named, not resolved, so
    a checkout elsewhere or an absolute path gives the same fingerprint. The CT
    is not hashed, and neither is the model's geometry (patch size, depth): the
    loop pins those, and the incumbent is re-scored at its own.
    """
    parent = os.path.dirname(val_uri.rstrip("/"))
    labels = validation_label_path(val_uri)
    record = {
        "protocol": validation_protocol(depth_band),
        "fragment": os.path.basename(os.path.normpath(parent)),
        "volume": os.path.basename(os.path.normpath(val_uri)),
        "labels": [os.path.basename(labels), _file_sha256(labels)],
        "mask": _file_sha256(os.path.join(parent, "mask.png")),
        "patches_json": _file_sha256(os.path.join(parent, "patches.json")),
    }
    return hashlib.sha256(json.dumps(record, sort_keys=True).encode()).hexdigest()


class IncumbentUnavailable(RuntimeError):
    """best_model.pt exists, but its score cannot be compared with a candidate's."""


def validation_indices(
    catalogue_size: int,
    sample_size: int = VALIDATION_SAMPLE_PATCHES,
    seed: int = VALIDATION_SAMPLE_SEED,
) -> np.ndarray:
    """The catalogue entries every candidate and the incumbent are scored on."""
    if catalogue_size < 1:
        raise ValueError("the validation catalogue is empty")
    order = np.random.RandomState(seed).permutation(catalogue_size)
    return np.sort(order[: min(sample_size, catalogue_size)])


def read_incumbent_val_f1(path: str, protocol: str) -> float:
    """The stored val_f1 a candidate must beat (see read_incumbent)."""
    return read_incumbent(path, protocol)[0]


def read_incumbent(path: str, protocol: str) -> tuple[float, str | None]:
    """The stored val_f1 a candidate must beat, and the fingerprint of the
    validation inputs it was measured on (validation_inputs_fingerprint; None when
    the incumbent predates fingerprints).

    -inf when there is no incumbent, so the first run bootstraps one. Raises
    IncumbentUnavailable when the file exists but cannot be compared: unreadable,
    no finite val_f1, or scored under another validation protocol than
    ``protocol`` (see validation_protocol). Treating those
    as -inf would let any candidate, including one trained from random weights
    because the same file could not be warm-started, replace the incumbent.
    """
    if not os.path.exists(path):
        return float("-inf"), None
    import torch

    try:
        checkpoint = torch.load(path, map_location="cpu", weights_only=False)
    except Exception as exc:
        raise IncumbentUnavailable(
            f"{path} cannot be read ({type(exc).__name__}: {exc}); "
            f"restore it (e.g. `git checkout -- {path}`) before promoting"
        ) from exc
    if not isinstance(checkpoint, dict):
        raise IncumbentUnavailable(f"{path} is not a checkpoint dictionary")
    recorded = checkpoint.get("val_protocol")
    if recorded != protocol:
        raise IncumbentUnavailable(
            f"{path} was scored under validation protocol "
            f"{recorded or 'v1 (unrecorded)'}, not {protocol}; re-score it with "
            f"`{RESCORE_COMMAND}`"
        )
    val_f1 = checkpoint.get("val_f1")
    if not isinstance(val_f1, (int, float)) or not math.isfinite(val_f1):
        raise IncumbentUnavailable(
            f"{path} has no finite val_f1; re-score it with `{RESCORE_COMMAND}`"
        )
    diag = checkpoint.get("validation_diag")
    inputs = diag.get("inputs_sha256") if isinstance(diag, dict) else None
    if inputs is not None and (
        not isinstance(inputs, str) or diag.get("protocol") != protocol
    ):
        raise IncumbentUnavailable(
            f"{path} records validation inputs that do not belong to its "
            f"{protocol} score; re-score it with `{RESCORE_COMMAND}`"
        )
    return float(val_f1), inputs


def check_incumbent(path: str, val_uri: str, depth_band=None) -> float:
    """The incumbent's val_f1, if a candidate scored on these validation inputs
    can be compared with it; IncumbentUnavailable otherwise.

    An incumbent scored before fingerprints were recorded is compared on its
    protocol alone; the loop says so when it starts.
    """
    val_f1, inputs = read_incumbent(path, validation_protocol(depth_band))
    if inputs is not None and inputs != validation_inputs_fingerprint(
        val_uri, depth_band
    ):
        raise IncumbentUnavailable(
            f"the validation inputs beside {val_uri} (label file, mask or "
            f"patches.json) changed since {path} was scored; re-score it with "
            f"`{RESCORE_COMMAND}`"
        )
    return val_f1


def save_checkpoint_atomic(payload, path: str) -> None:
    """torch.save to a sibling temporary file, then rename over ``path``.

    A writer stopped mid-save (stop.sh, the supervisor's timeout) leaves the
    previous file intact instead of a truncated one.
    """
    import torch

    directory = os.path.dirname(os.path.abspath(path))
    fd, temporary = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
