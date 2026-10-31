"""Publish small report sets with a completion marker last; readers must serialize."""

import hashlib
import json
import os
import re
import shutil
import stat
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from .file_modes import replacement_mode
from .prediction_artifacts import prediction_stem, validate_plan_paths

MAX_FILE_BYTES = 32 * 1024**2
MAX_TOTAL_BYTES = 64 * 1024**2
MAX_MARKER_BYTES = 64 * 1024


def _directory(value):
    if not isinstance(value, (str, os.PathLike)) or not str(value).strip():
        raise ValueError("reports_dir must be a nonempty local filesystem directory")
    if "://" in str(value) or re.match(r"^[A-Za-z][A-Za-z0-9+.-]*:/", str(value)):
        raise ValueError("reports_dir must be a local filesystem directory")
    path = Path(value).absolute()
    if path.is_symlink() or path.exists() and not path.is_dir():
        raise ValueError("reports_dir must be a nonsymlink directory")
    return path


def _names(marker, kind):
    prediction_stem(marker)
    if kind == "detector_evaluation" and marker.endswith("_scorecard.json"):
        stem = prediction_stem(marker.removesuffix("_scorecard.json"))
        return [stem + "_metrics_by_threshold.csv", stem + "_pred_thumb.png"]
    if (
        kind == "cross_scroll_measurement"
        and marker == "cross_scroll_measurement_manifest.json"
    ):
        return ["cross_scroll_measurement.md", "cross_scroll_measurement.json"]
    raise ValueError("unknown report kind or completion marker name")


def _identity(data):
    return {"bytes": len(data), "sha256": hashlib.sha256(data).hexdigest()}


def _reject_constant(value):
    raise ValueError(f"nonfinite JSON: {value}")


def _status(record):
    if not isinstance(record.get("created_at_utc"), str) or datetime.fromisoformat(
        record["created_at_utc"]
    ).utcoffset() != timezone.utc.utcoffset(None):
        raise ValueError("report creation time must be an ISO timestamp in UTC")
    status = record.get("report_status")
    if not isinstance(status, str) or status not in {"COMPLETE", "PARTIAL", "FAILED"}:
        raise ValueError("invalid report status")
    if record["report_kind"] == "detector_evaluation":
        if status != "COMPLETE":
            raise ValueError("a detector scorecard must be complete")
    else:
        counts = [
            record.get(key)
            for key in ("target_count", "success_count", "failure_count")
        ]
        if (
            any(type(value) is not int or value < 0 for value in counts)
            or counts[0] < 1
            or counts[1] + counts[2] != counts[0]
        ):
            raise ValueError("invalid measurement target counts")
        expected = (
            "COMPLETE" if counts[2] == 0 else "FAILED" if counts[1] == 0 else "PARTIAL"
        )
        if status != expected:
            raise ValueError("measurement status disagrees with target counts")


def _capture(path, maximum=MAX_FILE_BYTES):
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise ValueError(f"report artifact must be a regular nonsymlink file: {path}")
    if path.stat().st_size > maximum:
        raise ValueError(f"report artifact exceeds {maximum} bytes: {path}")
    with path.open("rb") as stream:
        data = stream.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError(f"report artifact exceeds {maximum} bytes: {path}")
    return data


def _snapshot(path):
    if not os.path.lexists(path):
        return None
    return {**_identity(_capture(path)), "mode": stat.S_IMODE(path.stat().st_mode)}


def _write(path, data):
    with path.open("xb") as stream:
        if stream.write(data) != len(data):
            raise OSError(f"short report write: {path}")
        stream.flush()
        os.fsync(stream.fileno())
    if _capture(path) != data:
        raise OSError(f"report readback failed: {path}")


def _restore(directory, previous, names, marker, originals):
    # Hide a newly installed marker until all old payloads are restored.
    if (previous / marker).exists() or originals[marker] is None:
        (directory / marker).unlink(missing_ok=True)
    for name in [*names, marker]:
        old, target = previous / name, directory / name
        if old.exists():
            os.replace(old, target)
        elif originals[name] is None:
            target.unlink(missing_ok=True)
        elif _snapshot(target) != originals[name]:
            raise OSError(f"previous report artifact cannot be restored: {name}")
    if any(
        _snapshot(directory / name) != expected for name, expected in originals.items()
    ):
        raise OSError("report rollback readback failed")


def report_output(directory, marker, kind, *, inputs=()):
    """Validate paths and existing file types/sizes without writes or payload reads."""
    directory = _directory(directory)
    names = _names(marker, kind)
    validate_plan_paths(
        [(directory / name, name) for name in [*names, marker]],
        [(path, "report input") for path in inputs],
    )
    for name in [*names, marker]:
        path = directory / name
        if os.path.lexists(path) and (
            path.is_symlink()
            or not stat.S_ISREG(path.stat().st_mode)
            or path.stat().st_size > MAX_FILE_BYTES
        ):
            raise ValueError(
                f"report target must be a bounded regular nonsymlink file: {path}"
            )
    return directory, names


def publish_report(directory, payloads, marker, metadata, kind, *, inputs=()):
    """Stage/read back all files, invalidate old marker first, install new marker last.

    Caught publication errors restore the previous set. Failed rollback preserves
    its private recovery directory. This is not a concurrent-reader or power-loss
    transaction; serialize readers/writers and verify hashes before using a report.
    """
    directory, names = report_output(directory, marker, kind, inputs=inputs)
    if (
        set(payloads) != set(names)
        or any(
            type(data) is not bytes or len(data) > MAX_FILE_BYTES
            for data in payloads.values()
        )
        or sum(map(len, payloads.values())) > MAX_TOTAL_BYTES
    ):
        raise ValueError("unexpected report payloads or byte budget exceeded")
    record = {
        **metadata,
        "artifact_contract": 1,
        "report_kind": kind,
        "created_at_utc": datetime.now(timezone.utc).isoformat(),
        "artifacts": {name: _identity(payloads[name]) for name in names},
    }
    _status(record)
    encoded = (json.dumps(record, indent=2, allow_nan=False) + "\n").encode("utf-8")
    if len(encoded) > MAX_MARKER_BYTES:
        raise ValueError("report completion marker exceeds byte budget")
    all_names = [*names, marker]
    originals = {name: _snapshot(directory / name) for name in all_names}
    directory.mkdir(parents=True, exist_ok=True)
    workspace = Path(tempfile.mkdtemp(prefix=".detector-report-", dir=directory))
    staged, previous = workspace / "staged", workspace / "previous"
    preserve = False
    try:
        staged.mkdir()
        previous.mkdir()
        for name, data in {**payloads, marker: encoded}.items():
            _write(staged / name, data)
            os.chmod(staged / name, replacement_mode(directory / name))
        if any(
            _snapshot(directory / name) != expected
            for name, expected in originals.items()
        ):
            raise ValueError("existing report changed during staging")
        for name, data in {**payloads, marker: encoded}.items():
            if _capture(staged / name) != data:
                raise ValueError(f"staged report changed: {name}")
        try:
            for name in [marker, *names]:
                if originals[name] is not None:
                    os.replace(directory / name, previous / name)
            for name in names:
                os.replace(staged / name, directory / name)
            for name, data in {**payloads, marker: encoded}.items():
                path = staged / name if name == marker else directory / name
                if _capture(path) != data:
                    raise ValueError(f"report changed during publication: {name}")
            os.replace(staged / marker, directory / marker)
            for name, data in {**payloads, marker: encoded}.items():
                if _capture(directory / name) != data:
                    raise ValueError(f"report changed after completion marker: {name}")
        except BaseException:
            try:
                _restore(directory, previous, names, marker, originals)
            except BaseException as exc:
                preserve = True
                raise RuntimeError(
                    f"report rollback failed; retain recovery files at {workspace}"
                ) from exc
            raise
    finally:
        if not preserve:
            shutil.rmtree(workspace)
    return record


def check_report(marker_path):
    """Verify the observed report files; does not recalculate scientific metrics."""
    marker_path = Path(marker_path).absolute()
    directory = _directory(marker_path.parent)
    data = _capture(marker_path, MAX_MARKER_BYTES)
    try:
        record = json.loads(data, parse_constant=_reject_constant)
        if (
            type(record["artifact_contract"]) is not int
            or record["artifact_contract"] != 1
        ):
            raise ValueError(
                "unsupported report contract; legacy reports need regeneration"
            )
        names = _names(marker_path.name, record["report_kind"])
        if not isinstance(record["artifacts"], dict) or set(record["artifacts"]) != set(
            names
        ):
            raise ValueError("report artifact list does not match its kind")
        for name in names:
            expected = record["artifacts"][name]
            if (
                not isinstance(expected, dict)
                or set(expected) != {"bytes", "sha256"}
                or type(expected["bytes"]) is not int
                or not 0 <= expected["bytes"] <= MAX_FILE_BYTES
                or not isinstance(expected["sha256"], str)
                or not re.fullmatch("[0-9a-f]{64}", expected["sha256"])
            ):
                raise ValueError("invalid report artifact identity")
            if _identity(_capture(directory / name)) != expected:
                raise ValueError(f"report artifact changed: {name}")
        if _capture(marker_path, MAX_MARKER_BYTES) != data:
            raise ValueError("report marker changed during verification")
        _status(record)
        return record
    except (KeyError, TypeError, AttributeError) as exc:
        raise ValueError("invalid or legacy report completion marker") from exc
