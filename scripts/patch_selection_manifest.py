"""Bind prepared selection records to the inputs being checked (stdlib only).

These checks validate manifest fields, reference bytes and path mappings. They
do not replay random generation, hash payloads or certify scientific validity.
"""

from pathlib import Path

from scripts.patch_check_inputs import distinct_arms
from scripts.patch_dataset_artifacts import (
    MANIFEST,
    MAX_REFERENCE_BYTES,
    capture_json,
    fingerprint,
    number,
)


def manifest_identity(binding):
    """Stable dependency fields, independent of derived report-field additions."""
    if not isinstance(binding, dict):
        raise ValueError("bootstrap manifest dependency must be an object")
    identity = {key: binding.get(key) for key in ("status", "path")}
    if "record" in binding:
        record = binding["record"]
        if not isinstance(record, dict):
            raise ValueError("bootstrap manifest record identity must be an object")
        identity["record"] = {
            key: record.get(key) for key in ("path", "sha256", "bytes")
        }
    return identity


def selection_manifest(
    captured, reference, rows, *, modes, required=False, threshold=None, full=None
):
    path = Path(captured["path"]) / MANIFEST
    if not path.exists() and not path.is_symlink():
        if required:
            raise ValueError(f"selection manifest is required: {path}")
        return {"status": "absent", "path": str(path)}
    source, data = capture_json(path, MAX_REFERENCE_BYTES)
    if not isinstance(data, dict):
        raise ValueError(f"selection manifest must be an object: {path}")
    mode = data.get("mode")
    if (
        data.get("schema") != "patch-dataset-selection-v1"
        or data.get("status") != "PREPARED"
        or data.get("payloads_copied") is not False
        or not isinstance(mode, str)
        or mode not in modes
    ):
        raise ValueError(
            f"selection manifest has an unsupported schema, status or mode: {path}"
        )
    recorded_reference = data.get("reference")
    if not isinstance(recorded_reference, dict) or any(
        recorded_reference.get(key) != reference[key] for key in ("sha256", "bytes")
    ):
        raise ValueError(
            f"selection manifest reference bytes differ from the supplied reference: {path}"
        )
    ids = sorted(captured["targets"])
    if (
        data.get("selected_ids") != ids
        or data.get("selected_ids_sha256") != fingerprint(ids)
        or type(data.get("selected_count")) is not int
        or data["selected_count"] != len(ids)
        or type(data.get("scored_patches")) is not int
        or data["scored_patches"] != len(rows)
        or set(ids) - rows.keys()
    ):
        raise ValueError(
            f"selection manifest membership/count/hash differs from the dataset: {path}"
        )
    declared = data.get("source")
    if not isinstance(declared, str) or not Path(declared).is_absolute():
        raise ValueError(
            f"selection manifest source must be an absolute directory: {path}"
        )
    root = Path(declared).resolve(strict=True)
    if not (root / "verified_patches").is_dir():
        raise ValueError(
            f"selection manifest source has no verified_patches directory: {path}"
        )
    if full is not None and root != Path(full).resolve(strict=True):
        raise ValueError(
            f"selection manifest source differs from the supplied full dataset: {path}"
        )
    for pid, target in captured["targets"].items():
        expected = root / "verified_patches" / pid
        if not expected.is_dir() or str(expected.resolve(strict=True)) != target:
            raise ValueError(
                f"selection manifest source target differs for patch {pid}: {path}"
            )
    selected_area = number(data.get("selected_area"), "manifest selected area")
    if selected_area != sum(rows[pid][1] for pid in ids):
        raise ValueError(
            f"selection manifest selected area differs from the reference: {path}"
        )
    recorded_threshold = None
    if mode in ("bootstrap", "random"):
        recorded_threshold = number(
            data.get("threshold"), "manifest threshold", upper=1
        )
        if threshold is not None and recorded_threshold != threshold:
            raise ValueError(
                f"selection manifest threshold differs from the supplied threshold: {path}"
            )
        if mode == "bootstrap" and set(ids) != {
            pid for pid, (fraction, _) in rows.items() if fraction >= recorded_threshold
        }:
            raise ValueError(
                f"selection manifest bootstrap is not the threshold selection: {path}"
            )
    return {
        "status": "checked",
        "path": str(path),
        "record": source.provenance(),
        "mode": mode,
        "source": str(root),
        "threshold": recorded_threshold,
        "selected_ids_sha256": fingerprint(ids),
        "bootstrap_ids": data.get("bootstrap_ids") if mode == "stripmatch" else None,
        "bootstrap_path": data.get("bootstrap") if mode == "stripmatch" else None,
        "bootstrap_manifest": manifest_identity(data["bootstrap_manifest"])
        if mode == "stripmatch" and data.get("bootstrap_manifest") is not None
        else None,
    }


def selection_manifests(
    captures, reference, rows, *, required=False, threshold=None, full=None
):
    distinct_arms(captures)
    bindings = {
        name: selection_manifest(
            captures[name],
            reference,
            rows,
            modes={"bootstrap"} if name == "BOOTSTRAP" else {"random", "stripmatch"},
            required=required,
            threshold=threshold,
            full=full,
        )
        for name in ("BOOTSTRAP", "RANDOM")
    }
    boot, control = bindings["BOOTSTRAP"], bindings["RANDOM"]
    if boot["status"] == control["status"] == "checked":
        if boot["source"] != control["source"]:
            raise ValueError("selection manifests name different full datasets")
        if control["mode"] == "random" and boot["threshold"] != control["threshold"]:
            raise ValueError("selection manifests use different bootstrap thresholds")
    if control.get("mode") == "stripmatch":
        if control["bootstrap_ids"] != sorted(captures["BOOTSTRAP"]["targets"]):
            raise ValueError(
                "STRIPMATCH manifest names a different bootstrap selection"
            )
        path = control["bootstrap_path"]
        if (
            not isinstance(path, str)
            or str(Path(path).resolve(strict=True)) != captures["BOOTSTRAP"]["path"]
        ):
            raise ValueError("STRIPMATCH manifest names a different bootstrap dataset")
        if control["bootstrap_manifest"] is not None and control[
            "bootstrap_manifest"
        ] != manifest_identity(boot):
            raise ValueError("STRIPMATCH bootstrap manifest changed since preparation")
    return bindings
