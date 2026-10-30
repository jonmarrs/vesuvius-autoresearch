#!/usr/bin/env python3
"""Evaluate an explicitly aligned, bounded binary reference/prediction pair.

Publish a new report directory with captured Villa metric sources, per-metric
statuses and finite JSON. Matching shapes and caller-declared alignment do not
verify physical registration, label quality, held-out lineage or prize eligibility.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata
import io
import json
import math
import os
import platform
import shutil
import sys
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from types import SimpleNamespace

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
for import_root in (REPO_ROOT, REPO_ROOT / "src"):
    if str(import_root) not in sys.path:
        sys.path.insert(0, str(import_root))

from scripts.candidate_artifacts import ARTIFACT_ERRORS, write_json
from scripts.evaluation_artifacts import VolumeSource, binary_reference, probabilities
from scripts.labeling.label_artifacts import (
    MAX_FRAGMENT_VOXELS,
    bounded_number,
    new_output,
    publish_new,
)
from scripts.text_snapshot import Snapshot
from vesuvius_autoresearch.core.villa_modules import load_villa_leaf

DEFAULT_METRICS = ("dice", "centerline_dice", "connected_components", "mean_ap")
CORE_METRICS = {"dice", "centerline_dice", "connected_components"}
METRICS = (
    *DEFAULT_METRICS,
    "dice_multiclass",
    "skeleton_distance_length",
    "critical_components_multiclass",
)


class UndefinedMetricValue(ValueError):
    """A metric returned no finite numeric result."""


def _finite_value(value):
    if isinstance(value, dict):
        if not value:
            raise UndefinedMetricValue("metric returned no values")
        if any(not isinstance(key, str) for key in value):
            raise UndefinedMetricValue("metric dictionary keys must be strings")
        return {key: _finite_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        if not value:
            raise UndefinedMetricValue("metric returned no values")
        return [_finite_value(item) for item in value]
    if isinstance(value, (int, float, np.integer, np.floating)) and not isinstance(
        value, (bool, np.bool_)
    ):
        if not math.isfinite(value):
            raise UndefinedMetricValue("metric returned a nonfinite value")
        return value.item() if isinstance(value, np.generic) else value
    raise UndefinedMetricValue("metric must return finite numeric values")


@contextlib.contextmanager
def _temporary_modules(modules):
    try:
        yield
    finally:
        for module in modules.values():
            if sys.modules.get(module.__name__) is module:
                sys.modules.pop(module.__name__)


def _call_metric(name, module, gt, probability, hard, args, staging):
    # An in-place operation in one metric cannot alter another metric's inputs.
    gt, hard = gt.copy(), hard.copy()
    if name == "dice":
        return module.compute(gt, hard, threshold=0.5)
    if name == "centerline_dice":
        return module.compute(gt, hard, tolerance_radius=args.tolerance)
    if name == "connected_components":
        return module.compute(gt, hard, num_classes=2, ignore_index=0, connectivity=26)
    if name == "mean_ap":
        return module.compute(
            gt,
            probability.copy() if args.ap_input == "probability" else hard,
            ignore_index=0,
        )
    if name == "dice_multiclass":
        return module.compute(gt, hard, num_classes=2, ignore_index=0)
    if name == "skeleton_distance_length":
        # Disable only this module's optional tracking. Do not start a global run.
        module.wandb = None
        if hasattr(module, "kimimaro"):
            upstream = module.kimimaro.skeletonize

            def one_worker(*args, **kwargs):
                kwargs["parallel"] = 1
                return upstream(*args, **kwargs)

            # The pinned metric hardcodes parallel=0 (all CPUs). Replace only
            # its module-local reference, not the shared kimimaro package.
            module.kimimaro = SimpleNamespace(skeletonize=one_worker)
        return module.compute(
            gt, hard, output_folder=str(staging / "artifacts/skeleton")
        )
    return module.compute(gt, hard, num_classes=2)


def _metric_artifacts(name, staging):
    if name != "skeleton_distance_length":
        return {}
    paths = list((staging / "artifacts/skeleton").glob("*.png"))
    if len(paths) != 1:
        raise RuntimeError("skeleton metric must produce one histogram PNG")
    path = paths[0]
    if not path.is_file() or path.is_symlink() or path.stat().st_size > 16 * 1024**2:
        raise RuntimeError("skeleton histogram must be a regular PNG within 16 MiB")
    with path.open("rb") as stream:
        captured = stream.read(16 * 1024**2 + 1)
    if len(captured) > 16 * 1024**2:
        raise RuntimeError("skeleton histogram exceeds 16 MiB")
    with Image.open(io.BytesIO(captured)) as image:
        if image.format != "PNG":
            raise RuntimeError("skeleton histogram is not a PNG")
        image.verify()
    return {
        str(path.relative_to(staging)): {
            "sha256": hashlib.sha256(captured).hexdigest(),
            "bytes": len(captured),
        }
    }


def _render_markdown(report, path):
    def cell(value):
        return (
            escape(str(value)).replace("|", "\\|").replace("\n", " ").replace("\r", " ")
        )

    settings = report["settings"]
    lines = [
        "# Binary Villa evaluation",
        "",
        f"Status: **{report['status']}**.",
        "",
        "Alignment is caller-declared. Physical registration, label quality and held-out lineage are unverified.",
        "",
        f"Hard prediction rule: probability >= {settings['threshold']:g}. "
        f"Prediction encoding: {settings['prediction_encoding']}; AP input: {settings['ap_input']}.",
        "",
        f"Selected source bbox (z0/z1/y0/y1/x0/x1): {report['reference']['bbox_zyx']}.",
        "",
        f"Slices predicted without reference foreground: {report['centerline_slices_predicted_without_ground_truth']}.",
        "",
        "| Metric | Status | Values | Note |",
        "| --- | --- | --- | --- |",
    ]
    for name, item in report["metrics"].items():
        value = (
            "n/a"
            if item["values"] is None
            else json.dumps(item["values"], allow_nan=False)
        )
        lines.append(
            f"| {cell(name)} | {cell(item['status'])} | {cell(value)} | {cell(item.get('reason', ''))} |"
        )
    lines += [
        "",
        "summary.json records input digests, settings, source captures, per-metric logs and artifact hashes.",
        "",
    ]
    path.write_text("\n".join(lines))


def _runtime_versions():
    packages = {}
    for name in (
        "numpy",
        "torch",
        "scipy",
        "scikit-image",
        "scikit-learn",
        "connected-components-3d",
        "kimimaro",
        "cupy-cuda12x",
    ):
        try:
            packages[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            packages[name] = None
    return {"python": platform.python_version(), "packages": packages}


def evaluate(args):
    threshold = bounded_number(args.threshold, "threshold", 0, 1)
    args.tolerance = bounded_number(args.tolerance, "tolerance", 0, sys.float_info.max)
    if not args.aligned_inputs and not args.dry_run:
        raise ValueError(
            "declare --aligned-inputs after verifying the same voxel grid; shape equality is insufficient"
        )
    if args.num_classes != 2:
        raise ValueError(
            "this wrapper evaluates binary labels only; multiclass IDs must not be collapsed"
        )
    if args.hist_dir is not None:
        raise ValueError(
            "--hist_dir is retired; histograms are published inside the new --out bundle"
        )
    if args.soft_pred and args.ap_input != "probability":
        raise ValueError("--soft_pred conflicts with --ap-input binary")
    selected = args.metric or list(DEFAULT_METRICS)
    if len(set(selected)) != len(selected):
        raise ValueError("each metric may be selected only once")
    if "critical_components_multiclass" in selected and args.device != "cuda":
        raise ValueError(
            "critical_components_multiclass requires explicit --device cuda"
        )
    gt_source = VolumeSource.inspect(args.gt, args.max_voxels)
    pred_source = VolumeSource.inspect(args.pred, args.max_voxels)
    if gt_source.header["shape_zyx"] != pred_source.header["shape_zyx"]:
        raise ValueError(
            "reference/prediction shapes must match exactly; implicit cropping is retired"
        )
    gt_source.select(args.bbox)
    pred_source.select(args.bbox)
    root = Path(args.villa_root).expanduser().resolve()
    sources = {
        name: Snapshot.read(
            root / f"segmentation/evaluation/metrics/{name}.py", 512 * 1024
        )
        for name in selected
    }
    adapters = {
        name: Snapshot.read(Path(__file__).with_name(name), 512 * 1024)
        for name in ("evaluate_villa_metrics.py", "evaluation_artifacts.py")
    }
    output = new_output(
        args.out,
        gt_source.path,
        pred_source.path,
        root,
        *(s.path for s in sources.values()),
        *(s.path for s in adapters.values()),
    )
    settings = {
        "threshold": threshold,
        "threshold_rule": ">=",
        "tolerance_radius_voxels": args.tolerance,
        "prediction_encoding": args.prediction_encoding,
        "ap_input": args.ap_input,
        "device": args.device,
        "max_voxels": args.max_voxels,
        "metrics": selected,
        "alignment_basis": "caller-declared matching voxel grids"
        if args.aligned_inputs
        else "not declared; execution requires --aligned-inputs",
        "skeleton_parallel": 1 if "skeleton_distance_length" in selected else None,
        "mask_policy": "all selected voxels; no ignore mask",
    }
    if args.dry_run:
        print(
            json.dumps(
                {
                    "status": "PLANNED",
                    "output": str(output),
                    "settings": settings,
                    "reference": gt_source.provenance(),
                    "prediction": pred_source.provenance(),
                    "scope": "headers/settings/source-file checks; values, metric dependencies and CUDA not checked",
                },
                allow_nan=False,
            )
        )
        return 0
    if args.device == "cuda":
        import torch

        if not torch.cuda.is_available():
            raise ValueError("CUDA requested but no usable device is available")
    records, modules, provenance = {}, {}, {}
    with publish_new(output) as staging, _temporary_modules(modules):
        for name, source in adapters.items():
            source.copy_into(staging, name)
        for name, source in sources.items():
            relative = f"sources/villa_{name}.py"
            source.copy_into(staging, f"villa_{name}.py")
            provenance[name] = {**source.provenance(), "captured_source": relative}
            log = io.StringIO()
            try:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    modules[name] = load_villa_leaf(relative, villa_root=staging)
            except Exception as exc:
                if name in CORE_METRICS:
                    raise RuntimeError(
                        f"Required Villa metric {name} unavailable: {exc}"
                    ) from exc
                records[name] = {
                    "status": "UNAVAILABLE",
                    "values": None,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
        if not modules:
            raise RuntimeError("none of the requested Villa metrics could be loaded")
        gt = binary_reference(gt_source.read())
        probability = probabilities(pred_source.read(), args.prediction_encoding)
        hard = (probability >= threshold).astype(np.uint8)
        unlabelled = int(np.count_nonzero(hard.any(axis=(1, 2)) & ~gt.any(axis=(1, 2))))
        for name, module in modules.items():
            log = io.StringIO()
            if name == "mean_ap" and not gt.any():
                records[name] = {
                    "status": "UNDEFINED",
                    "values": None,
                    "reason": "no positive reference voxels",
                }
                continue
            try:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    values = _call_metric(
                        name, module, gt, probability, hard, args, staging
                    )
                if (
                    name == "mean_ap"
                    and "Error computing AP for class" in log.getvalue()
                ):
                    raise RuntimeError(
                        "upstream mean_ap reported an internal failure; see metric log"
                    )
                values = _finite_value(values)
                records[name] = {
                    "status": "OK",
                    "values": values,
                    "artifacts": _metric_artifacts(name, staging),
                }
                if name == "centerline_dice":
                    warnings = []
                    if unlabelled:
                        warnings.append(
                            "pinned Villa treats predicted skeletons on reference-empty slices as within tolerance"
                        )
                    score = (
                        values.get("centerline_dice")
                        if isinstance(values, dict)
                        else values
                    )
                    if isinstance(score, (int, float)) and score > 1:
                        warnings.append(
                            "upstream centerline score exceeds one; this is not a bounded Dice definition"
                        )
                    if warnings:
                        records[name]["status"] = "WARNING"
                        records[name]["reason"] = "; ".join(warnings)
            except UndefinedMetricValue as exc:
                records[name] = {
                    "status": "UNDEFINED",
                    "values": None,
                    "reason": str(exc),
                }
            except Exception as exc:
                records[name] = {
                    "status": "FAILED",
                    "values": None,
                    "reason": f"{type(exc).__name__}: {exc}",
                }
            text = log.getvalue()
            if text:
                records[name]["log"] = text[-8192:]
                records[name]["log_truncated"] = len(text) > 8192
            if name == "skeleton_distance_length" and records[name]["status"] != "OK":
                shutil.rmtree(staging / "artifacts/skeleton", ignore_errors=True)
        # Unique staged module paths prevent reuse of stale code and metric globals.
        shutil.rmtree(staging / "sources/__pycache__", ignore_errors=True)
        complete = all(item["status"] == "OK" for item in records.values())
        report = {
            "schema": "villa-binary-evaluation-v1",
            "status": "COMPLETE" if complete else "PARTIAL",
            "created_at_utc": datetime.now(timezone.utc).isoformat(),
            "settings": settings,
            "reference": gt_source.provenance(),
            "prediction": pred_source.provenance(),
            "metric_sources": provenance,
            "adapter_sources": {
                name: {**source.provenance(), "captured_source": f"sources/{name}"}
                for name, source in adapters.items()
            },
            "runtime": _runtime_versions(),
            "metrics": {name: records[name] for name in selected},
            "centerline_slices_predicted_without_ground_truth": unlabelled,
            "reference_positive_voxels": int(gt.sum()),
            "prediction_positive_voxels": int(hard.sum()),
            "alignment_verified": False,
            "label_quality_verified": False,
            "heldout_lineage_verified": False,
        }
        write_json(staging / "summary.json", report)
        if json.loads((staging / "summary.json").read_text()) != report:
            raise ValueError(
                "serialized evaluation report differs from computed results"
            )
        _render_markdown(report, staging / "summary.md")
        gt_source.verify()
        pred_source.verify()
        for source in (*sources.values(), *adapters.values()):
            source.verify()
        for name, source in sources.items():
            if (staging / f"sources/villa_{name}.py").read_bytes() != source.data:
                raise ValueError("captured metric source changed during evaluation")
        for name, source in adapters.items():
            if (staging / "sources" / name).read_bytes() != source.data:
                raise ValueError("captured adapter source changed during evaluation")
        for name, record in records.items():
            if (
                record["status"] == "OK"
                and _metric_artifacts(name, staging) != record["artifacts"]
            ):
                raise ValueError("metric artifact changed before publication")
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(output),
                "metrics_ok": sum(r["status"] == "OK" for r in records.values()),
                "metrics_requested": len(selected),
            },
            allow_nan=False,
        )
    )
    return 0 if complete else 2


def _parser():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--gt", type=Path, required=True, help="binary reference Zarr/TIFF"
    )
    parser.add_argument("--pred", type=Path, required=True, help="prediction Zarr/TIFF")
    parser.add_argument(
        "--out", type=Path, required=True, help="new source-disjoint report directory"
    )
    parser.add_argument(
        "--aligned-inputs",
        action="store_true",
        help="declare matching source voxel coordinates",
    )
    parser.add_argument(
        "--bbox", type=int, nargs=6, metavar=("Z0", "Z1", "Y0", "Y1", "X0", "X1")
    )
    parser.add_argument("--max-voxels", type=int, default=MAX_FRAGMENT_VOXELS)
    parser.add_argument("--threshold", type=float, default=0.5)
    parser.add_argument(
        "--prediction-encoding",
        choices=("probability", "binary", "uint8"),
        default="probability",
    )
    parser.add_argument(
        "--ap-input", choices=("probability", "binary"), default="probability"
    )
    parser.add_argument(
        "--soft_pred",
        action="store_true",
        help="legacy alias for probability AP (now default)",
    )
    parser.add_argument(
        "--num_classes",
        "--num-classes",
        type=int,
        default=2,
        help="binary wrapper; must be 2",
    )
    parser.add_argument(
        "--hist_dir", type=Path, help="retired; use artifacts inside --out"
    )
    parser.add_argument(
        "--metric",
        action="append",
        choices=METRICS,
        help="repeat to select metrics; default is four CPU metrics",
    )
    parser.add_argument("--tolerance", type=float, default=3.0)
    parser.add_argument("--device", choices=("cpu", "cuda"), default="cpu")
    parser.add_argument(
        "--villa-root",
        type=Path,
        default=REPO_ROOT / "villa",
        help="explicit trusted Villa source checkout",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="validate a plan without metric imports, CUDA probes or writes",
    )
    return parser


def main(argv=None):
    args = _parser().parse_args(argv)
    if args.device == "cpu":
        os.environ["CUDA_VISIBLE_DEVICES"] = ""
    os.environ["MPLBACKEND"] = "Agg"
    try:
        return evaluate(args)
    except (*ARTIFACT_ERRORS, ImportError, MemoryError) as exc:
        print(f"Villa binary evaluation failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
