"""Read-only patch membership captures for mechanical input checks."""

from pathlib import Path

from scripts.patch_dataset_artifacts import (
    distinct_patch_targets,
    entries,
    fingerprint,
    patch_id,
)

INPUT_ERRORS = (OSError, ValueError, TypeError, OverflowError, KeyError, RuntimeError)


def read_arm(dataset, scored=None):
    """Patch ID -> resolved directory. No two IDs may share a directory; with
    scored, only among those IDs: a FULL dataset's unscored patches are outside
    the comparison, as the builders treat them."""
    root = Path(dataset).resolve(strict=True)
    directory = root / "verified_patches"
    targets = {}
    for path in entries(directory):
        pid = patch_id(path.name)
        if not path.is_dir():
            raise ValueError(f"patch is missing or is not a directory: {path}")
        targets[pid] = str(path.resolve(strict=True))
    distinct_patch_targets(
        targets
        if scored is None
        else {pid: target for pid, target in targets.items() if pid in scored}
    )
    return {
        "path": str(root),
        "container": str(directory.resolve(strict=True)),
        "targets": targets,
    }


def distinct_arms(captures):
    boot = Path(captures["BOOTSTRAP"]["container"])
    control = Path(captures["RANDOM"]["container"])
    if boot.samefile(control):
        raise ValueError("BOOTSTRAP and control must use distinct patch containers")
    if captures["BOOTSTRAP"]["targets"] == captures["RANDOM"]["targets"]:
        raise ValueError(
            "BOOTSTRAP and control select the same patches; the control is not an independent draw"
        )


def verify_arm(captured, scored=None):
    if read_arm(captured["path"], scored) != captured:
        raise ValueError(
            f"patch membership or link targets changed: {captured['path']}"
        )


def arm_provenance(captured):
    return {
        "path": captured["path"],
        "patch_count": len(captured["targets"]),
        "ids_sha256": fingerprint(sorted(captured["targets"])),
        "link_targets_sha256": fingerprint(captured["targets"]),
    }
