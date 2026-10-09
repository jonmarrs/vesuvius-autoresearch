#!/usr/bin/env python3
"""Prepare one pseudo-label batch from a declared teacher and region manifest.

Dry run is the default. --execute runs real inference and publishes a complete
batch. Training and scientific validation require separate, recorded runs;
this command never simulates learning or repeats an unchanged teacher as rounds.
"""

import argparse
import json
import math
import re
import shlex
import subprocess
import sys
from pathlib import Path

import numpy as np
from PIL import Image

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.candidate_artifacts import integer, write_json
from scripts.export_for_production import (
    CHECKPOINT_ERRORS,
    checkpoint_contract,
    sha256_file,
)
from scripts.generate_pseudo_labels import prob_to_pseudo_png
from scripts.labeling.label_artifacts import new_output, publish_new
from scripts.process_supervisor import ProcessSupervisor
from scripts.pseudo_label_artifacts import (
    MAX_LABEL_PIXELS,
    fragment_inputs,
    merge_labels,
    read_png,
)
from vesuvius_autoresearch.core.checkpoint_tools import load_tool_checkpoint


def segment_stem(value):
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]*", value) or value.endswith(
        "_mask"
    ):
        raise ValueError(f"unsafe or ambiguous segment basename: {value!r}")
    return value


def combine_labels(manual_dir, pseudo_dir, combined_dir, max_pixels=MAX_LABEL_PIXELS):
    """Merge immutable PNG batches using <segment>_mask.png for known labels."""
    manual_dir, pseudo_dir = Path(manual_dir), Path(pseudo_dir)
    output = new_output(combined_dir, manual_dir, pseudo_dir)
    if not manual_dir.is_dir() or not pseudo_dir.is_dir():
        raise ValueError("manual and pseudo inputs must be directories")
    manuals = {
        p.stem: p for p in manual_dir.glob("*.png") if not p.stem.endswith("_mask")
    }
    masks = {p.name.removesuffix("_mask.png") for p in manual_dir.glob("*_mask.png")}
    if masks - manuals.keys():
        raise ValueError("manual masks without corresponding labels are ambiguous")
    pseudos = {
        p.name.removesuffix("_pseudo.png"): p for p in pseudo_dir.glob("*_pseudo.png")
    }
    stems = sorted(manuals.keys() | pseudos.keys())
    if not stems:
        raise ValueError("no labels supplied")
    with publish_new(output) as staging:
        for stem in stems:
            segment_stem(stem)
            manual = known = None
            if stem in manuals:
                manual = read_png(manuals[stem], kind="binary", max_pixels=max_pixels)
                known = read_png(
                    manual_dir / f"{stem}_mask.png",
                    kind="binary",
                    shape=manual.shape,
                    max_pixels=max_pixels,
                )
            pseudo = (
                read_png(
                    pseudos[stem],
                    kind="pseudo",
                    shape=None if manual is None else manual.shape,
                    max_pixels=max_pixels,
                )
                if stem in pseudos
                else np.full(manual.shape, 128, np.uint8)
            )
            Image.fromarray(merge_labels(pseudo, manual, known)).save(
                staging / f"{stem}_pseudo.png"
            )
    return output


def manifest_regions(path):
    """Strict JSON and manifest-relative paths; no URI, mask, or scroll guessing."""

    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate manifest field: {key}")
            result[key] = value
        return result

    def reject_constant(value):
        raise ValueError(f"nonfinite JSON value: {value}")

    path = Path(path).resolve()
    data = json.loads(
        path.read_text(),
        object_pairs_hook=unique_object,
        parse_constant=reject_constant,
    )
    if (
        not isinstance(data, dict)
        or set(data) != {"regions"}
        or not isinstance(data["regions"], list)
        or not data["regions"]
    ):
        raise ValueError("manifest must contain only a nonempty regions list")
    records = []
    allowed = {
        "fragment",
        "region_mask",
        "manual_labels",
        "manual_mask",
        "holdout_mask",
    }
    for item in data["regions"]:
        if (
            not isinstance(item, dict)
            or not {"fragment", "region_mask"} <= item.keys()
            or item.keys() - allowed
        ):
            raise ValueError(
                "region requires fragment and region_mask; unknown fields are rejected"
            )
        if ("manual_labels" in item) != ("manual_mask" in item):
            raise ValueError("manual labels require an explicit known-pixel mask")
        record = {}
        for key, value in item.items():
            if not isinstance(value, str) or not value.strip() or "://" in value:
                raise ValueError(f"{key} must be an explicit local path")
            record[key] = (path.parent / value).resolve()
        records.append(record)
    return path, records


def generator_command(
    checkpoint, record, output, cache, tau_low, tau_high, device, max_pixels
):
    return [
        sys.executable,
        str(REPO_ROOT / "scripts/generate_pseudo_labels.py"),
        "--checkpoint",
        str(checkpoint),
        "--fragment",
        str(record["fragment"]),
        "--region-mask",
        str(record["region_mask"]),
        "--out",
        str(output),
        "--cache-dir",
        str(cache),
        "--tau-low",
        str(tau_low),
        "--tau-high",
        str(tau_high),
        "--device",
        str(device),
        "--max-pixels",
        str(max_pixels),
    ]


def prepare_round(
    checkpoint,
    manifest,
    output,
    *,
    execute=False,
    tau_low=0.15,
    tau_high=0.65,
    device="cpu",
    timeout=3600,
    max_pixels=MAX_LABEL_PIXELS,
):
    if isinstance(timeout, bool) or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    max_pixels = integer(max_pixels, "max_pixels", 1)
    prob_to_pseudo_png(np.zeros((1, 1)), np.ones((1, 1), bool), tau_high, tau_low)
    checkpoint = Path(checkpoint).resolve()
    manifest, records = manifest_regions(manifest)
    sources = [
        checkpoint,
        manifest,
        *(value for record in records for value in record.values()),
    ]
    output = new_output(output, *sources)
    hashes = {str(path): sha256_file(path) for path in sources if path.is_file()}
    model, settings, saved = load_tool_checkpoint(checkpoint, "cpu")
    checkpoint_contract(saved, verify_model=False)
    del model, saved
    names, volumes, prepared = set(), set(), []
    for record in records:
        stem = segment_stem(record["fragment"].name)
        uri, shape, region = fragment_inputs(
            record["fragment"], record["region_mask"], settings, max_pixels
        )
        new_output(output, uri)
        if stem in names or uri in volumes:
            raise ValueError(
                "duplicate segment basename or volume source would collide at training handoff"
            )
        names.add(stem)
        volumes.add(uri)
        manual = known = holdout = None
        if "manual_labels" in record:
            manual = read_png(
                record["manual_labels"],
                kind="binary",
                shape=region.shape,
                max_pixels=max_pixels,
            )
            known = read_png(
                record["manual_mask"],
                kind="binary",
                shape=region.shape,
                max_pixels=max_pixels,
            )
        if "holdout_mask" in record:
            holdout = read_png(
                record["holdout_mask"],
                kind="binary",
                shape=region.shape,
                max_pixels=max_pixels,
            )
            if np.any(holdout & (region if known is None else region | known)):
                raise ValueError(
                    "requested or known manual pixels overlap the declared holdout"
                )
        prepared.append((record, stem, uri, shape))

    # Re-read images per segment during execution to bound memory across the batch.
    def unchanged():
        if any(sha256_file(path) != digest for path, digest in hashes.items()):
            raise ValueError("a declared input changed during preparation")
        for record, _, uri, shape in prepared:
            current_uri, current_shape, _ = fragment_inputs(
                record["fragment"], record["region_mask"], settings, max_pixels
            )
            if current_uri != uri or current_shape != shape:
                raise ValueError("volume identity or shape changed during preparation")

    unchanged()
    commands = [
        generator_command(
            checkpoint,
            record,
            output / "raw" / f"{stem}_pseudo.png",
            output / "cache" / stem,
            tau_low,
            tau_high,
            device,
            max_pixels,
        )
        for record, stem, _, _ in prepared
    ]
    plan = {
        "status": "DRY_RUN",
        "scope": "pseudo_label_preparation",
        "training_executed": False,
        "output": str(output),
        "commands": commands,
    }
    if not execute:
        return plan
    supervisor = ProcessSupervisor()
    with publish_new(output) as staging:
        (staging / "raw").mkdir()
        (staging / "labels").mkdir()
        executed, artifacts = [], []
        for record, stem, uri, shape in prepared:
            unchanged()
            raw = staging / "raw" / f"{stem}_pseudo.png"
            cache = staging / "cache" / stem
            cache.mkdir(parents=True)
            command = generator_command(
                checkpoint, record, raw, cache, tau_low, tau_high, device, max_pixels
            )
            print(f"Running: {shlex.join(command)}", flush=True)
            supervisor.run(command, timeout=timeout, check=True, cwd=REPO_ROOT)
            pseudo = read_png(
                raw, kind="pseudo", shape=shape[1:], max_pixels=max_pixels
            )
            region = read_png(
                record["region_mask"],
                kind="binary",
                shape=shape[1:],
                max_pixels=max_pixels,
            )
            if np.any(pseudo[~region] != 128):
                raise ValueError("producer labeled pixels outside the declared region")
            if not np.any(pseudo[region] != 128):
                raise ValueError("producer supplied no confident requested pixels")
            manual = known = None
            if "manual_labels" in record:
                manual = read_png(
                    record["manual_labels"],
                    kind="binary",
                    shape=shape[1:],
                    max_pixels=max_pixels,
                )
                known = read_png(
                    record["manual_mask"],
                    kind="binary",
                    shape=shape[1:],
                    max_pixels=max_pixels,
                )
            merged = merge_labels(pseudo, manual, known)
            label = staging / "labels" / f"{stem}_pseudo.png"
            Image.fromarray(merged).save(label)
            artifacts.append(
                {
                    "segment": stem,
                    "volume": str(uri),
                    "shape_zyx": list(shape),
                    "inputs": {key: str(value) for key, value in record.items()},
                    "raw": f"raw/{raw.name}",
                    "raw_sha256": sha256_file(raw),
                    "labels": f"labels/{label.name}",
                    "labels_sha256": sha256_file(label),
                    "requested_pixels": int(region.sum()),
                    "confident_requested_pixels": int(((pseudo != 128) & region).sum()),
                    "manual_known_pixels": 0 if known is None else int(known.sum()),
                }
            )
            executed.append(command)
        unchanged()
        result = {
            "schema": "pseudo-label-handoff-v1",
            "status": "PREPARED",
            "scope": "pseudo_label_preparation",
            "training_executed": False,
            "accuracy_verified": False,
            "teacher_lineage_verified": False,
            "submittable": None,
            "checkpoint": str(checkpoint),
            "input_sha256": hashes,
            "model_settings": settings,
            "thresholds": {"low": tau_low, "high": tau_high},
            "max_pixels": max_pixels,
            "commands_executed": executed,
            "regions": artifacts,
            "training_requirements": {
                "uris": [str(uri) for _, _, uri, _ in prepared],
                "pseudo_label_dir": str(output / "labels"),
                "use_confidence_weight": True,
                "ignore_residual_weight": "1/255; no exact ignore mask in existing loss",
            },
            "volume_content_hashed": False,
        }
        write_json(staging / "handoff.json", result)
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--checkpoint", required=True, help="trusted local teacher checkpoint"
    )
    parser.add_argument("--manifest", required=True)
    parser.add_argument(
        "--out", required=True, help="new, source-disjoint batch directory"
    )
    parser.add_argument(
        "--execute", action="store_true", help="run label generation after validation"
    )
    parser.add_argument("--tau-low", type=float, default=0.15)
    parser.add_argument("--tau-high", type=float, default=0.65)
    parser.add_argument("--device", default="cpu")
    parser.add_argument("--timeout", type=float, default=3600)
    parser.add_argument("--max-pixels", type=int, default=MAX_LABEL_PIXELS)
    args = parser.parse_args(argv)
    try:
        result = prepare_round(
            args.checkpoint,
            args.manifest,
            args.out,
            execute=args.execute,
            tau_low=args.tau_low,
            tau_high=args.tau_high,
            device=args.device,
            timeout=args.timeout,
            max_pixels=args.max_pixels,
        )
    except (
        *CHECKPOINT_ERRORS,
        subprocess.CalledProcessError,
        subprocess.TimeoutExpired,
    ) as exc:
        parser.exit(1, f"pseudo-label preparation failed: {exc}\n")
    print(json.dumps(result, indent=2, allow_nan=False))


if __name__ == "__main__":
    main()
