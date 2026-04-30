#!/usr/bin/env python3
"""
Rank Scroll 2/3 candidate windows for First Letters / First Title review.

Inputs are the deterministic queue plus optional prediction artifacts. This is a
cheap metadata/statistics pass: it does not download data or run inference.
"""
import argparse
import csv
import json
from pathlib import Path

import numpy as np


def _float(row, key, default=0.0):
    try:
        return float(row.get(key, default))
    except (TypeError, ValueError):
        return default


def _artifact_stem(row):
    width = int(_float(row, "width", _float(row, "patch_size", 64)))
    height = int(_float(row, "height", _float(row, "patch_size", 64)))
    return f"pred_{int(_float(row, 'z'))}_{int(_float(row, 'y'))}_{int(_float(row, 'x'))}_{width}x{height}"


def _load_prediction_stats(prediction_dir, row):
    pred_dir = Path(prediction_dir)
    stem = _artifact_stem(row)
    ink_path = pred_dir / f"{stem}_ink.npy"
    fiber_path = pred_dir / f"{stem}_fiber.npy"
    meta_path = pred_dir / f"{stem}_meta.json"

    stats = {
        "prediction_found": ink_path.exists(),
        "ink_mean": 0.0,
        "ink_std": 0.0,
        "ink_max": 0.0,
        "ink_hot_fraction": 0.0,
        "fiber_mean": 0.0,
        "metadata_found": meta_path.exists(),
    }

    if ink_path.exists():
        arr = np.load(ink_path)
        stats["ink_mean"] = float(arr.mean())
        stats["ink_std"] = float(arr.std())
        stats["ink_max"] = float(arr.max())
        stats["ink_hot_fraction"] = float((arr >= 0.5).mean())

    if fiber_path.exists():
        fiber = np.load(fiber_path)
        stats["fiber_mean"] = float(fiber.mean())

    if meta_path.exists():
        try:
            with open(meta_path, "r") as f:
                meta = json.load(f)
            ink_stats = meta.get("ink_stats", {})
            stats["ink_mean"] = float(ink_stats.get("mean", stats["ink_mean"]))
            stats["ink_std"] = float(ink_stats.get("std", stats["ink_std"]))
            stats["ink_max"] = float(ink_stats.get("max", stats["ink_max"]))
        except (OSError, ValueError, TypeError):
            pass

    return stats


def score_row(row, prediction_dir="predictions"):
    stats = _load_prediction_stats(prediction_dir, row)
    base_priority = _float(row, "priority", 1.0)
    div = row.get("division", "")
    core_bonus = 0.35 if div in {"div_90", "div_100"} else 0.0
    local_bonus = 0.15 if row.get("local_uri") else 0.0
    submittable_bonus = 0.25 if row.get("submittable_window") == "true" else -1.0
    prediction_bonus = 0.0
    if stats["prediction_found"]:
        # Favor sparse, high-confidence signal over broad foggy activations.
        prediction_bonus = (
            2.0 * stats["ink_max"]
            + 1.5 * stats["ink_std"]
            + 1.0 * stats["ink_hot_fraction"]
            - 0.5 * stats["ink_mean"]
        )

    review_score = base_priority + core_bonus + local_bonus + submittable_bonus + prediction_bonus
    out = dict(row)
    out.update(
        {
            "review_score": f"{review_score:.6f}",
            "prediction_found": str(stats["prediction_found"]).lower(),
            "metadata_found": str(stats["metadata_found"]).lower(),
            "ink_mean": f"{stats['ink_mean']:.6f}",
            "ink_std": f"{stats['ink_std']:.6f}",
            "ink_max": f"{stats['ink_max']:.6f}",
            "ink_hot_fraction": f"{stats['ink_hot_fraction']:.6f}",
            "fiber_mean": f"{stats['fiber_mean']:.6f}",
            "artifact_stem": _artifact_stem(row),
        }
    )
    return out


def rank_candidates(queue_path, out_path, prediction_dir="predictions", limit=None):
    with open(queue_path, "r", newline="") as f:
        rows = list(csv.DictReader(f, delimiter="\t"))

    ranked = [score_row(row, prediction_dir=prediction_dir) for row in rows]
    ranked.sort(key=lambda row: float(row["review_score"]), reverse=True)
    if limit is not None:
        ranked = ranked[:limit]

    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if ranked:
        with open(out_path, "w", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(ranked[0].keys()), delimiter="\t")
            writer.writeheader()
            writer.writerows(ranked)
    else:
        out_path.write_text("")
    return ranked


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--queue", default="reports/scroll23_search_queue.tsv")
    parser.add_argument("--out", default="reports/scroll23_ranked_candidates.tsv")
    parser.add_argument("--prediction-dir", default="predictions")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    ranked = rank_candidates(args.queue, args.out, args.prediction_dir, args.limit)
    print(f"Wrote {len(ranked)} ranked candidates to {args.out}")
    if ranked:
        print(f"Top candidate: {ranked[0]['scroll_id']} {ranked[0]['division']} score={ranked[0]['review_score']}")


if __name__ == "__main__":
    main()
