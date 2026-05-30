#!/usr/bin/env python3
"""Cross-scroll consistency validation for the autoresearch model.

The current bandit's val_bpb measures performance against a held-out fragment
from the *same* scroll as the training pool (`PHercParis2Fr143` from PHerc
Paris 2, same as training fragment `PHercParis2Fr47`). That tells us nothing
about the model's behavior on the actual prize-target scrolls (Scroll 2 /
Scroll 3 / PHerc0125 / PHerc0332) — which have no manual ink labels to
compute a Dice / val_bpb against.

This script computes a *consistency* metric instead of a Dice-vs-ground-truth
metric: for each ranked Scroll 2 / Scroll 3 candidate region with both a
model ink prediction (from `predict.py`) and a CT-derived fiber label (from
PR #922's `generate_fiber_labels_from_ct.py`), measure whether the model's
ink predictions concentrate in *non-fiber* regions. Real ink sits on the
papyrus surface above the fiber bundles, so a model that frequently predicts
ink on fiber regions is making errors. The fiber label is purely Frangi
vesselness on CT — independent of the ink model — which makes this a real
*orthogonal* signal, not a circular self-check.

Output: per-candidate metrics + per-scroll / per-division aggregates in
`reports/cross_scroll_validation_summary.{json,md}`.

Usage::

    uv run python scripts/cross_scroll_validation.py
    uv run python scripts/cross_scroll_validation.py --auto-generate-fiber-labels
    uv run python scripts/cross_scroll_validation.py --top-n 12 --fiber-threshold 0.3

The `--auto-generate-fiber-labels` flag runs `scripts/generate_fiber_labels.py
--mode candidates` first to fill in any missing fiber labels in the evidence
directories before running the validation.
"""

from __future__ import annotations

import argparse
import json
import statistics
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import tifffile


@dataclass
class CandidateRecord:
    candidate_index: int
    artifact_stem: str
    scroll_id: str
    short_id: str
    division: str
    z: int
    y: int
    x: int
    review_score: float
    ink_pred_mean: float | None
    fiber_mean: float | None
    ink_mean_in_fiber_regions: float | None
    ink_mean_in_nonfiber_regions: float | None
    ink_anti_fiber_ratio: float | None
    fiber_region_pixel_count: int
    nonfiber_region_pixel_count: int
    status: str
    note: str


def _read_candidate_meta(candidate_dir: Path) -> dict | None:
    meta_path = candidate_dir / "candidate.json"
    if not meta_path.exists():
        return None
    try:
        return json.loads(meta_path.read_text())
    except Exception:
        return None


def _load_ink_prediction(candidate_dir: Path, artifact_stem: str) -> np.ndarray | None:
    """Load the 2D ink-probability surface for the candidate.

    The handoff writes the prediction to
    ``reports/scroll23_evidence/candidate_NNN/predictions/<artifact_stem>_ink.zarr``,
    layout (1, H, W) uint8 under ``/0``.
    """
    import zarr

    candidates = [
        candidate_dir / "predictions" / f"{artifact_stem}_ink.zarr" / "0",
        candidate_dir / "predictions" / f"{artifact_stem}_ink.zarr",
    ]
    for path in candidates:
        if path.exists():
            try:
                arr = zarr.open(str(path), mode="r")
                if hasattr(arr, "shape"):
                    raw = np.asarray(arr[0] if arr.ndim == 3 else arr)
                else:
                    raw = np.asarray(arr["0"][0])
                if raw.dtype == np.uint8:
                    return raw.astype(np.float32) / 255.0
                return raw.astype(np.float32)
            except Exception:
                continue
    return None


def _load_fiber_label(candidate_dir: Path) -> np.ndarray | None:
    """Load the 3D fiber-label volume produced by PR #922."""
    fiber_path = candidate_dir / "fiber_label.tif"
    if not fiber_path.exists():
        return None
    try:
        return tifffile.imread(str(fiber_path))
    except Exception:
        return None


def _project_fiber_to_surface(fiber_3d: np.ndarray) -> np.ndarray:
    """Project a 3D binary fiber-label volume to a 2D density map.

    Uses z-mean: each (y, x) pixel gets the fraction of z-depth occupied by
    fiber. Output is in [0, 1] and has the same (H, W) shape as the input's
    yx footprint.
    """
    if fiber_3d.ndim == 3:
        return fiber_3d.astype(np.float32).mean(axis=0)
    if fiber_3d.ndim == 2:
        return fiber_3d.astype(np.float32)
    raise ValueError(f"unexpected fiber-label ndim {fiber_3d.ndim}")


def _compute_metrics(
    ink_pred: np.ndarray,
    fiber_density: np.ndarray,
    fiber_threshold: float,
) -> dict:
    """Compute per-candidate consistency metrics."""
    if ink_pred.shape != fiber_density.shape:
        # Conservative align — fall back to common bbox if shapes mismatch.
        h = min(ink_pred.shape[0], fiber_density.shape[0])
        w = min(ink_pred.shape[1], fiber_density.shape[1])
        ink_pred = ink_pred[:h, :w]
        fiber_density = fiber_density[:h, :w]

    fiber_mask = fiber_density > fiber_threshold
    nonfiber_mask = ~fiber_mask

    ink_in_fiber = float(ink_pred[fiber_mask].mean()) if fiber_mask.any() else None
    ink_in_nonfiber = (
        float(ink_pred[nonfiber_mask].mean()) if nonfiber_mask.any() else None
    )

    if ink_in_fiber is not None and ink_in_fiber > 1e-8 and ink_in_nonfiber is not None:
        anti_fiber_ratio = ink_in_nonfiber / ink_in_fiber
    elif (
        ink_in_fiber is not None and ink_in_nonfiber is not None and ink_in_nonfiber > 0
    ):
        anti_fiber_ratio = float("inf")
    else:
        anti_fiber_ratio = None

    return {
        "ink_pred_mean": float(ink_pred.mean()),
        "fiber_mean": float(fiber_density.mean()),
        "ink_mean_in_fiber_regions": ink_in_fiber,
        "ink_mean_in_nonfiber_regions": ink_in_nonfiber,
        "ink_anti_fiber_ratio": anti_fiber_ratio,
        "fiber_region_pixel_count": int(fiber_mask.sum()),
        "nonfiber_region_pixel_count": int(nonfiber_mask.sum()),
    }


def _process_candidate(candidate_dir: Path, fiber_threshold: float) -> CandidateRecord:
    meta = _read_candidate_meta(candidate_dir)
    if meta is None:
        return CandidateRecord(
            candidate_index=-1,
            artifact_stem="?",
            scroll_id="?",
            short_id="?",
            division="?",
            z=-1,
            y=-1,
            x=-1,
            review_score=0.0,
            ink_pred_mean=None,
            fiber_mean=None,
            ink_mean_in_fiber_regions=None,
            ink_mean_in_nonfiber_regions=None,
            ink_anti_fiber_ratio=None,
            fiber_region_pixel_count=0,
            nonfiber_region_pixel_count=0,
            status="MISSING_META",
            note=f"no candidate.json in {candidate_dir}",
        )

    try:
        idx = int(candidate_dir.name.replace("candidate_", ""))
    except Exception:
        idx = -1

    artifact_stem = meta.get("artifact_stem", "?")
    base = CandidateRecord(
        candidate_index=idx,
        artifact_stem=artifact_stem,
        scroll_id=str(meta.get("scroll_id", "?")),
        short_id=str(meta.get("short_id", "?")),
        division=str(meta.get("division", "?")),
        z=int(float(meta.get("z", -1))),
        y=int(float(meta.get("y", -1))),
        x=int(float(meta.get("x", -1))),
        review_score=float(meta.get("review_score", 0.0)),
        ink_pred_mean=None,
        fiber_mean=None,
        ink_mean_in_fiber_regions=None,
        ink_mean_in_nonfiber_regions=None,
        ink_anti_fiber_ratio=None,
        fiber_region_pixel_count=0,
        nonfiber_region_pixel_count=0,
        status="PENDING",
        note="",
    )

    ink_pred = _load_ink_prediction(candidate_dir, artifact_stem)
    if ink_pred is None:
        base.status = "MISSING_INK_PREDICTION"
        base.note = "no <stem>_ink.zarr in predictions/"
        return base

    fiber_3d = _load_fiber_label(candidate_dir)
    if fiber_3d is None:
        base.status = "MISSING_FIBER_LABEL"
        base.note = "no fiber_label.tif (run scripts/generate_fiber_labels.py --mode candidates first)"
        return base

    fiber_density = _project_fiber_to_surface(fiber_3d)
    metrics = _compute_metrics(ink_pred, fiber_density, fiber_threshold)

    base.ink_pred_mean = metrics["ink_pred_mean"]
    base.fiber_mean = metrics["fiber_mean"]
    base.ink_mean_in_fiber_regions = metrics["ink_mean_in_fiber_regions"]
    base.ink_mean_in_nonfiber_regions = metrics["ink_mean_in_nonfiber_regions"]
    base.ink_anti_fiber_ratio = metrics["ink_anti_fiber_ratio"]
    base.fiber_region_pixel_count = metrics["fiber_region_pixel_count"]
    base.nonfiber_region_pixel_count = metrics["nonfiber_region_pixel_count"]
    base.status = "OK"
    return base


def _aggregate(records: list[CandidateRecord]) -> dict:
    """Aggregate metrics by scroll and division."""
    by_group: dict[tuple[str, str], list[CandidateRecord]] = {}
    for r in records:
        if r.status != "OK":
            continue
        key = (r.short_id, r.division)
        by_group.setdefault(key, []).append(r)

    groups = []
    for (short_id, division), members in sorted(by_group.items()):
        ratios = [
            r.ink_anti_fiber_ratio
            for r in members
            if r.ink_anti_fiber_ratio is not None
            and r.ink_anti_fiber_ratio != float("inf")
        ]
        ink_means = [r.ink_pred_mean for r in members if r.ink_pred_mean is not None]
        fiber_means = [r.fiber_mean for r in members if r.fiber_mean is not None]
        groups.append(
            {
                "short_id": short_id,
                "division": division,
                "n_candidates": len(members),
                "mean_ink_pred": statistics.mean(ink_means) if ink_means else None,
                "mean_fiber": statistics.mean(fiber_means) if fiber_means else None,
                "mean_anti_fiber_ratio": statistics.mean(ratios) if ratios else None,
                "stdev_anti_fiber_ratio": statistics.stdev(ratios)
                if len(ratios) >= 2
                else None,
                "candidate_indices": sorted(r.candidate_index for r in members),
            }
        )
    return {
        "groups": groups,
        "total_candidates_evaluated": sum(1 for r in records if r.status == "OK"),
    }


def _maybe_generate_fiber_labels(evidence_root: Path, top_n: int) -> None:
    """Run scripts/generate_fiber_labels.py if any candidate is missing fiber_label.tif."""
    missing = [
        d
        for d in sorted(evidence_root.glob("candidate_*"))
        if not (d / "fiber_label.tif").exists()
    ]
    if not missing:
        print("# All candidate dirs already have fiber_label.tif; skipping generator.")
        return
    print(
        f"# {len(missing)} candidate dirs missing fiber_label.tif; running generate_fiber_labels.py --mode candidates --top-n {top_n} ..."
    )
    cmd = [
        sys.executable,
        "scripts/generate_fiber_labels.py",
        "--mode",
        "candidates",
        "--top-n",
        str(top_n),
    ]
    subprocess.run(cmd, check=True)


def _fmt(value, spec: str = ".4f") -> str:
    """Format a number, returning 'n/a' for None / NaN / inf."""
    if value is None:
        return "n/a"
    try:
        if value != value or value in (float("inf"), float("-inf")):  # NaN check
            return "inf" if value == float("inf") else "n/a"
    except TypeError:
        return "n/a"
    return format(value, spec)


def _render_markdown(
    records: list[CandidateRecord], aggregate: dict, output_path: Path
) -> None:
    lines = [
        "# Cross-Scroll Consistency Validation",
        "",
        "This report measures the consistency between the autoresearch model's ink predictions "
        "and an independent CT-derived fiber-label signal (from PR ScrollPrize/villa#922's "
        "`generate_fiber_labels_from_ct.py`). For each ranked Scroll 2 / Scroll 3 candidate "
        "region, the metric `ink_anti_fiber_ratio` is the ratio of the model's mean ink "
        "prediction in non-fiber regions to its mean prediction in fiber regions. Real ink "
        "sits on the surface above fiber bundles, so a value greater than 1 indicates the "
        "model's predictions concentrate in non-fiber regions (consistent), while a value at "
        "or below 1 indicates predictions are uniform or biased toward fiber regions "
        "(inconsistent).",
        "",
        "This is a *consistency* metric, not a ground-truth Dice or `val_bpb`. There is no "
        "manual ink ground truth for Scroll 2 / Scroll 3 (that is the prize problem). The "
        "fiber label is purely Frangi vesselness on CT, independent of the ink model.",
        "",
        "## Aggregate (per scroll + division)",
        "",
        "| Scroll | Division | N | mean ink_pred | mean fiber | mean anti-fiber ratio | stdev ratio |",
        "| --- | --- | ---: | ---: | ---: | ---: | ---: |",
    ]
    for g in aggregate["groups"]:
        lines.append(
            f"| {g['short_id']} | {g['division']} | {g['n_candidates']} "
            f"| {_fmt(g.get('mean_ink_pred'))} | {_fmt(g.get('mean_fiber'))} "
            f"| {_fmt(g.get('mean_anti_fiber_ratio'), '.3f')} | {_fmt(g.get('stdev_anti_fiber_ratio'), '.3f')} |"
        )

    lines.extend(
        [
            "",
            "## Per-candidate",
            "",
            "| Idx | Stem | Scroll/Div | (z,y,x) | ink_pred_mean | fiber_mean | ink_in_fiber | ink_in_nonfiber | anti-fiber ratio | status |",
            "| ---: | --- | --- | --- | ---: | ---: | ---: | ---: | ---: | --- |",
        ]
    )
    for r in records:
        if r.status != "OK":
            lines.append(
                f"| {r.candidate_index} | {r.artifact_stem} | {r.short_id}/{r.division} "
                f"| ({r.z},{r.y},{r.x}) | — | — | — | — | — | {r.status} |"
            )
            continue
        lines.append(
            f"| {r.candidate_index} | {r.artifact_stem} | {r.short_id}/{r.division} "
            f"| ({r.z},{r.y},{r.x}) | {_fmt(r.ink_pred_mean)} | {_fmt(r.fiber_mean)} "
            f"| {_fmt(r.ink_mean_in_fiber_regions)} | {_fmt(r.ink_mean_in_nonfiber_regions)} "
            f"| {_fmt(r.ink_anti_fiber_ratio, '.3f')} | OK |"
        )

    lines.append("")
    output_path.write_text("\n".join(lines))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--evidence-root", type=Path, default=Path("reports/scroll23_evidence")
    )
    parser.add_argument(
        "--fiber-threshold",
        type=float,
        default=0.001,
        help=(
            "Threshold on the z-mean fiber density to classify a (y, x) pixel as "
            "'fiber region'. The first run on 12 Scroll 2/3 candidates showed actual "
            "fiber densities of 0.0001-0.0004 (sparse), so the default is 0.001 — "
            "i.e., any pixel with at least one fiber voxel across z counts as fiber."
        ),
    )
    parser.add_argument(
        "--auto-generate-fiber-labels",
        action="store_true",
        help="Run scripts/generate_fiber_labels.py first if any fiber labels are missing.",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=12,
        help="--top-n passed to generate_fiber_labels.py when auto-generating.",
    )
    parser.add_argument(
        "--output-json",
        type=Path,
        default=Path("reports/cross_scroll_validation_summary.json"),
    )
    parser.add_argument(
        "--output-md",
        type=Path,
        default=Path("reports/cross_scroll_validation_summary.md"),
    )
    args = parser.parse_args(argv)

    if not args.evidence_root.exists():
        print(
            f"error: evidence root not found at {args.evidence_root}", file=sys.stderr
        )
        return 1

    if args.auto_generate_fiber_labels:
        _maybe_generate_fiber_labels(args.evidence_root, args.top_n)

    candidate_dirs = sorted(args.evidence_root.glob("candidate_*"))
    if not candidate_dirs:
        print(
            f"error: no candidate_* directories under {args.evidence_root}",
            file=sys.stderr,
        )
        return 1

    records = [_process_candidate(d, args.fiber_threshold) for d in candidate_dirs]
    aggregate = _aggregate(records)

    summary = {
        "fiber_threshold": args.fiber_threshold,
        "evidence_root": str(args.evidence_root),
        "candidates": [asdict(r) for r in records],
        "aggregate": aggregate,
    }
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(json.dumps(summary, indent=2))

    args.output_md.parent.mkdir(parents=True, exist_ok=True)
    _render_markdown(records, aggregate, args.output_md)

    ok_count = sum(1 for r in records if r.status == "OK")
    print(f"# cross_scroll_validation: {ok_count}/{len(records)} candidates evaluated")
    print(f"# summary JSON: {args.output_json}")
    print(f"# summary MD:   {args.output_md}")
    for g in aggregate["groups"]:
        ratio = (
            f"{g['mean_anti_fiber_ratio']:.3f}"
            if g["mean_anti_fiber_ratio"] is not None
            else "n/a"
        )
        print(
            f"#   {g['short_id']}/{g['division']} (n={g['n_candidates']}): mean anti-fiber ratio = {ratio}"
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
