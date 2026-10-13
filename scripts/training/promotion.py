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
"""

from __future__ import annotations

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
    """The stored val_f1 a candidate must beat.

    -inf when there is no incumbent, so the first run bootstraps one. Raises
    IncumbentUnavailable when the file exists but cannot be compared: unreadable,
    no finite val_f1, or scored under another validation protocol than
    ``protocol`` (see validation_protocol). Treating those
    as -inf would let any candidate, including one trained from random weights
    because the same file could not be warm-started, replace the incumbent.
    """
    if not os.path.exists(path):
        return float("-inf")
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
    return float(val_f1)


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
