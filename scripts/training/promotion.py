"""What a promotion compares: the validation sample and the incumbent's stored score.

Kept free of training imports (torch is imported lazily) so the loop controller can
check the incumbent before it starts a shift.

A candidate is promoted when its val_f1 beats the val_f1 stored in best_model.pt.
That is only meaningful when both were measured on the same patches. Protocol v1
read the first 100 *batches* of the validation catalogue in raster order: 400
patches at batch_size 4, 800 at 8, all from the top of the fragment, so a
batch_size tweak was scored on a different set from the incumbent. Protocol v2
scored a fixed, seeded sample spread over the whole catalogue, whatever the batch
size, but only its ink-containing patches (97 of 400 on Fr143, 58% ink). There F1
could not tell the project's detector from calling every pixel ink (finding 88).
Protocol v3 scores every patch of the same draw, ink-free ones included. A score
from another protocol is not comparable and is refused, not bootstrapped;
``scripts/reevaluate_best_model.py --update-stored`` re-scores it.

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

from vesuvius_autoresearch.core.file_modes import replacement_mode

VALIDATION_PROTOCOL = "seeded-sample-400-v3"
# The same draw scored on its ink-containing patches only; kept so finding 86's
# and 88's measurements of it can be reproduced.
INK_ONLY_PROTOCOL = "seeded-sample-400-v2"
VALIDATION_SAMPLE_PATCHES = 400
VALIDATION_SAMPLE_SEED = 42

RESCORE_COMMAND = "uv run python scripts/reevaluate_best_model.py --update-stored"


def validation_protocol(depth_band=None, base: str = VALIDATION_PROTOCOL) -> str:
    """The protocol a score is measured under. The depth band is part of it: the
    same patches read from other slices are a different sample. ``base`` is
    INK_ONLY_PROTOCOL only to reproduce a v2 measurement."""
    if depth_band is None:
        return base
    start, end = depth_band
    return f"{base}+z{start}-{end}"


def scores_ink_free_patches(protocol: str) -> bool:
    """Whether ``protocol`` scores the draw's ink-free patches (v3) or drops
    them (v2). The protocol string is the one record of which patches count."""
    base = protocol.split("+", 1)[0]
    if base == VALIDATION_PROTOCOL:
        return True
    if base == INK_ONLY_PROTOCOL:
        return False
    raise ValueError(f"unknown validation protocol {protocol!r}")


# The label file validation (and training) reads: the first of these beside
# the volume.
VALIDATION_LABEL_FILES = (
    "inklabels_refined.png",
    "inklabels_filled.png",
    "inklabels.png",
)
# A zarr's metadata (shape, dtype, chunks), at its root and its level 0: small,
# and changed by a volume rebuilt in place.
ZARR_METADATA_FILES = (".zarray", ".zgroup", ".zattrs", "zarr.json")


def validation_label_path(val_uri: str) -> str:
    """The label file read for this volume (inklabels.png when none exists)."""
    parent = os.path.dirname(val_uri.rstrip("/"))
    for name in VALIDATION_LABEL_FILES:
        path = os.path.join(parent, name)
        if os.path.exists(path):
            return path
    return path


def validation_input_paths(val_uri: str) -> dict[str, str]:
    """The files beside the volume that validation reads, by role. The one
    definition build_validation_dataset and the fingerprint both use."""
    parent = os.path.dirname(val_uri.rstrip("/"))
    return {
        "labels": validation_label_path(val_uri),
        "mask": os.path.join(parent, "mask.png"),
        "patches_json": os.path.join(parent, "patches.json"),
    }


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
    the volume's zarr metadata (shape, dtype, chunks); the label file validation
    reads and its contents; the mask; and patches.json, which replaces the
    catalogue when present. Paths are named, not resolved, so a checkout elsewhere
    or an absolute path gives the same fingerprint. The CT itself is not hashed,
    and neither is the model's geometry (patch size, depth): the loop pins those,
    and the incumbent is re-scored at its own.
    """
    if not isinstance(val_uri, str) or not val_uri:
        raise ValueError("the validation inputs need a val_uri")
    paths = validation_input_paths(val_uri)
    volume = val_uri.rstrip("/")
    record = {
        "protocol": validation_protocol(depth_band),
        "fragment": os.path.basename(os.path.dirname(volume)),
        "volume": os.path.basename(volume),
        "volume_metadata": {
            f"{level}{name}": _file_sha256(os.path.join(volume, level, name))
            for level in ("", "0/")
            for name in ZARR_METADATA_FILES
        },
        "labels": [os.path.basename(paths["labels"]), _file_sha256(paths["labels"])],
        "mask": _file_sha256(paths["mask"]),
        "patches_json": _file_sha256(paths["patches_json"]),
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


def first_use_record(path: str) -> str:
    """Where the loop records the validation inputs it found for an incumbent
    scored before fingerprints (see check_incumbent)."""
    return f"{path}.inputs.json"


def read_incumbent(path: str, protocol: str) -> tuple[float, str | None]:
    """The stored val_f1 a candidate must beat, and the fingerprint of the
    validation inputs it is compared on (see _read_incumbent)."""
    val_f1, inputs, _source = _read_incumbent(path, protocol)
    return val_f1, inputs


def _read_incumbent(path: str, protocol: str) -> tuple[float, str | None, str | None]:
    """The stored val_f1 a candidate must beat, the fingerprint of the
    validation inputs it is compared on (validation_inputs_fingerprint), and its
    source: the checkpoint's own ("checkpoint"), else the loop's record for this
    exact file ("first use"), else None.

    -inf when there is no incumbent, so the first run bootstraps one. Raises
    IncumbentUnavailable when the file exists but cannot be compared: unreadable,
    no finite val_f1, or scored under another validation protocol than
    ``protocol`` (see validation_protocol). Treating those
    as -inf would let any candidate, including one trained from random weights
    because the same file could not be warm-started, replace the incumbent.
    """
    if not os.path.exists(path):
        return float("-inf"), None, None
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
    if inputs is not None:
        return float(val_f1), inputs, "checkpoint"
    inputs = _first_use_inputs(path, protocol)
    return float(val_f1), inputs, None if inputs is None else "first use"


def _first_use_inputs(path: str, protocol: str) -> str | None:
    try:
        with open(first_use_record(path)) as handle:
            record = json.load(handle)
    except (OSError, ValueError):
        return None
    if (
        isinstance(record, dict)
        and record.get("protocol") == protocol
        and isinstance(record.get("inputs_sha256"), str)
        and record.get("checkpoint_sha256") == _file_sha256(path)
    ):
        return record["inputs_sha256"]
    return None  # another incumbent's record: it has been replaced since


def check_incumbent(
    path: str, val_uri: str, depth_band=None
) -> tuple[float, str | None]:
    """The incumbent's val_f1 if a candidate scored on these validation inputs can
    be compared with it, and how its inputs are known; IncumbentUnavailable
    otherwise.

    The second value is "checkpoint" (recorded with its score), "first use" (a
    record this loop made earlier), "recorded now", or None (no incumbent). An
    incumbent scored before fingerprints has none of its own: the first check
    records the inputs it finds (first_use_record, kept beside the checkpoint
    and tied to its hash), and later checks hold it to them. That trusts the
    inputs at first use; re-scoring replaces the record with the checkpoint's own.
    """
    protocol = validation_protocol(depth_band)
    val_f1, known, source = _read_incumbent(path, protocol)
    try:
        current = validation_inputs_fingerprint(val_uri, depth_band)
    except (OSError, ValueError) as exc:
        raise IncumbentUnavailable(
            f"the validation inputs for {val_uri} cannot be read "
            f"({type(exc).__name__}: {exc})"
        ) from exc
    if val_f1 == float("-inf"):
        return val_f1, None
    if known is None:
        try:
            with open(first_use_record(path), "w") as handle:
                json.dump(
                    {
                        "checkpoint_sha256": _file_sha256(path),
                        "protocol": protocol,
                        "inputs_sha256": current,
                        "val_uri": val_uri,
                    },
                    handle,
                    indent=2,
                )
                handle.write("\n")
        except OSError as exc:
            raise IncumbentUnavailable(
                f"cannot record the validation inputs for {path} "
                f"({type(exc).__name__}: {exc})"
            ) from exc
        return val_f1, "recorded now"
    if known != current:
        raise IncumbentUnavailable(
            f"the validation inputs for {val_uri} (fragment, volume metadata, "
            f"label file, mask or patches.json) differ from those {path} is "
            f"compared on; re-score it with `{RESCORE_COMMAND}`"
        )
    return val_f1, source


def save_checkpoint_atomic(payload, path: str) -> None:
    """torch.save to a sibling temporary file, then rename over ``path``.

    A writer stopped mid-save (stop.sh, the supervisor's timeout) leaves the
    previous file intact instead of a truncated one. The file keeps the mode of
    the one it replaces (a new one gets the umask's): the temporary file is
    created 0600, and renamed as it was it left every promoted best_model.pt and
    every last_model.pt readable by its owner alone.
    """
    import torch

    directory = os.path.dirname(os.path.abspath(path))
    mode = replacement_mode(path)
    fd, temporary = tempfile.mkstemp(
        prefix=f".{os.path.basename(path)}.", suffix=".tmp", dir=directory
    )
    try:
        with os.fdopen(fd, "wb") as handle:
            os.fchmod(handle.fileno(), mode)
            torch.save(payload, handle)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


# train.py's TSV row schemas and promotion gates, for code that promotes without importing train.py (an import
# patches wandb for the whole process): scripts/promote_loop_candidate.py and scripts/training/replicate_rule.py.
# tests/test_promote_loop_candidate.py compares them with train.py's.
HISTORY_COLUMNS = (
    "timestamp",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "avg_mean_ap",
    "train_loss",
    "throughput_Mvps",
    "num_params_M",
    "peak_vram_mb",
    "config",
)
RESULTS_COLUMNS = tuple(c for c in HISTORY_COLUMNS if c != "avg_mean_ap")
PRIZE_READINESS_COLUMNS = (
    "timestamp",
    "submittable",
    "window_ok",
    "window_mm",
    "villa_metrics_ok",
    "patch_size",
    "val_bpb",
    "avg_skel_dist",
    "avg_centerline_dice",
    "avg_cc_diff",
    "avg_crit_comp",
    "config",
)
LIFT_MARGIN = 0.02
F1_NOISE_TOLERANCE = 1e-2
