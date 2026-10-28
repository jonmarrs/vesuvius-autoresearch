"""Read-only patch membership captures for mechanical input checks."""

from pathlib import Path

from scripts.patch_dataset_artifacts import entries, fingerprint, patch_id

INPUT_ERRORS = (OSError, ValueError, TypeError, OverflowError, KeyError, RuntimeError)


def read_arm(dataset):
    root = Path(dataset).resolve(strict=True)
    directory = root / "verified_patches"
    targets = {}
    for path in entries(directory):
        pid = patch_id(path.name)
        if not path.is_dir():
            raise ValueError(f"patch is missing or is not a directory: {path}")
        targets[pid] = str(path.resolve(strict=True))
    return {
        "path": str(root),
        "container": str(directory.resolve(strict=True)),
        "targets": targets,
    }


def verify_arm(captured):
    if read_arm(captured["path"]) != captured:
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
