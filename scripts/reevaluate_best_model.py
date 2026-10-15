"""
Re-score best_model.pt under the loop's current validation protocol.

Why this exists: a cycle is promoted when its val_f1 beats the val_f1 stored in
best_model.pt, so both must come from the same validation patches. When the
protocol changes (scripts/training/promotion.py), the stored score is no longer
comparable; train.py and the loop then refuse to promote or start until this
script has re-scored the incumbent.

It runs validation only (no training), through the same code the loop uses
(train.build_validation_dataset, train.collect_validation_predictions,
train.pooled_segmentation_metrics), with the input settings the checkpoint was
trained with and the validation fragment from config.json. The legacy
Dice/topology numbers are re-measured on the same patches.

Usage:
    uv run python scripts/reevaluate_best_model.py
    uv run python scripts/reevaluate_best_model.py --update-stored  # rewrites best_model.pt's stored scores
    uv run python scripts/reevaluate_best_model.py --update-stored --unwarped
        # scores without a recorded lasagna warp that never ran (finding 86), and
        # corrects the record

--update-stored rewrites best_model.pt, so it refuses while work holds this
checkout's lock (the loop, the noise probe or the augmentation ablation): a cycle
would compare its candidate with the score the re-score replaces, and a promotion
made meanwhile would be written over with the old model. Stop the loop with ./stop.sh (which also pauses the watchdog) and
restart it with ./start.sh. The write is also refused if best_model.pt changed
while it was being scored.
"""

import argparse
import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import torch

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _REPO_ROOT)
# train.py lives in scripts/training/ (moved); keep it importable as `train`.
sys.path.insert(0, os.path.join(_REPO_ROOT, "scripts", "training"))

from train import (
    ExperimentConfig,
    build_validation_dataset,
    collect_validation_predictions,
    compute_cc_diff,
    compute_centerline_dice,
    compute_official_dice,
    compute_skeleton_dist,
    pooled_segmentation_metrics,
    select_topology_threshold,
)

from scripts.loop_control import running_pid
from scripts.training.promotion import save_checkpoint_atomic, validation_protocol
from vesuvius_autoresearch.core.checkpoint_tools import (
    ink_probabilities,
    load_tool_checkpoint,
    validate_batch,
)

# Input settings that change what the model sees; scored as the model was trained.
RECORDED_INPUT_SETTINGS = ("use_lasagna",)


def _file_sha256(path: str) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def refuse_beside_running_loop(when: str) -> None:
    """--update-stored writes best_model.pt, which a running cycle reads, holds
    and may replace: not while work holds this checkout's lock."""
    pid = running_pid(Path.cwd())
    if pid is not None:
        raise RuntimeError(
            f"autoresearch work is running in this checkout (PID {pid}) {when}; "
            "best_model.pt was not updated. Stop it with ./stop.sh (which also "
            "pauses the watchdog), re-score, then restart it with ./start.sh"
        )


def reevaluate(update_stored: bool = False, unwarped: bool = False) -> None:
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    # The validation fragment is the loop's current one (candidates are scored on
    # it); everything the model sees is the checkpoint's own.
    config = (
        ExperimentConfig.load("config.json")
        if os.path.exists("config.json")
        else ExperimentConfig()
    )

    if update_stored:
        # Before any GPU time is spent; checked again before the write.
        refuse_beside_running_loop("at the start")
        loaded_sha256 = _file_sha256("best_model.pt")
    print("Loading best_model.pt...")
    model, settings, chk = load_tool_checkpoint("best_model.pt", device)
    for name, value in settings.items():
        setattr(config, name, value)
    stored = chk.get("config", {})
    for name in RECORDED_INPUT_SETTINGS:
        if name in stored:
            setattr(config, name, stored[name])
    # A checkpoint can record use_lasagna: true although the warp never ran: on a
    # host without nvcc the loader fell back to unwarped patches (finding 86), and
    # strict reads now refuse the warp. Such a model was trained unwarped.
    overridden = {}
    if unwarped and config.use_lasagna:
        overridden["use_lasagna"] = config.use_lasagna
        config.use_lasagna = False
        print("  recorded use_lasagna: true; scoring unwarped (--unwarped)")
    stored_arch = stored.get("architecture", "?")

    print(f"  stored architecture: {stored_arch!r}")
    print(f"  stored protocol:     {chk.get('val_protocol', 'v1 (unrecorded)')}")
    print(f"  stored val_f1:       {chk.get('val_f1')}")
    print(f"  stored val_bpb:      {chk.get('val_bpb')}")
    print(f"  stored skel_dist:    {chk.get('avg_skel_dist')}")
    print(f"  stored cd_dice:     {chk.get('avg_centerline_dice')}")
    print(f"  stored cc_diff:     {chk.get('avg_cc_diff')}")
    print()

    # The loop's protocol: config.json's depth band, not the checkpoint's.
    protocol = validation_protocol(config.depth_band)
    print(f"  scoring protocol:    {protocol}")
    val_ds = build_validation_dataset(config)

    def probabilities(net, x):
        return ink_probabilities(net, validate_batch(x, settings))

    torch.manual_seed(42)
    all_probs, all_targets, diag = collect_validation_predictions(
        model,
        val_ds,
        config.num_layers,
        device,
        batch_size=config.batch_size,
        amp_enabled=device.type == "cuda",
        probabilities=probabilities,
        protocol=protocol,
    )
    if not diag["complete"]:
        raise RuntimeError(
            f"{diag['batch_errors']} validation batches failed; the protocol's "
            "sample is incomplete and the checkpoint was not updated"
        )
    if not all_probs:
        raise ValueError("zero usable validation patches")

    seg = pooled_segmentation_metrics(all_probs, all_targets)
    f1_metrics = {
        "val_f1": float(seg.get("val_f1", float("nan"))),
        "val_f1_threshold": float(seg.get("best_threshold", float("nan"))),
        "ap_prevalence_lift": float(seg.get("ap_prevalence_lift", float("nan"))),
        "roc_auc": float(seg.get("roc_auc", float("nan"))),
        "val_positive_rate": float(seg.get("positive_rate", float("nan"))),
    }
    if not all(np.isfinite(value) for value in f1_metrics.values()):
        raise ValueError(
            f"nonfinite promotion metrics {f1_metrics}; checkpoint was not updated"
        )

    probs_cat = torch.cat(all_probs)
    targets_cat = torch.cat(all_targets)

    best_dice, best_threshold = 0.0, 0.5
    for t in np.linspace(0.01, 0.8, 40):
        d = compute_official_dice(targets_cat, probs_cat, threshold=t)
        if d > best_dice:
            best_dice, best_threshold = d, t
    print(f"  best dice: {best_dice:.6f} at threshold {best_threshold:.3f}")

    # Topology gates are evaluated at the centerline_dice-optimal threshold (see
    # train.select_topology_threshold), matching the loop's validation.
    topo_threshold, topo_cd = select_topology_threshold(all_probs, all_targets)
    print(f"  topology threshold: {topo_threshold:.3f} (centerline_dice {topo_cd:.6f})")

    val_losses, val_skel, val_cd, val_cc = [], [], [], []
    for i in range(len(all_probs)):
        prob_2d = all_probs[i]
        tgt = all_targets[i]
        val_losses.append(
            1.0 - compute_official_dice(tgt, prob_2d, threshold=best_threshold)
        )
        try:
            gt = (tgt > 0.5).numpy().astype(bool)
            pred = (prob_2d > topo_threshold).numpy().astype(bool)
            for b in range(gt.shape[0]):
                val_cc.append(compute_cc_diff(gt[b, 0], pred[b, 0]))
        except Exception as exc:
            raise RuntimeError("connected-component measurement failed") from exc
        if i % 10 == 0:
            gt3 = np.squeeze((tgt > 0.5).numpy().astype(bool))
            pred3 = np.squeeze((prob_2d > topo_threshold).numpy().astype(bool))
            if gt3.ndim == 2:
                gt3 = gt3[np.newaxis, ...]
            if pred3.ndim == 2:
                pred3 = pred3[np.newaxis, ...]
            try:
                sd = compute_skeleton_dist(gt3, pred3)
                if not np.isfinite(sd):
                    raise ValueError("nonfinite skeleton-distance measurement")
                val_skel.append(sd)
            except Exception as exc:
                raise RuntimeError("topology measurement failed") from exc
            try:
                cd = compute_centerline_dice(gt3, pred3, tolerance_radius=3.0)[
                    "centerline_dice"
                ]
                if not np.isfinite(cd):
                    raise ValueError("nonfinite centerline measurement")
                val_cd.append(cd)
            except Exception as exc:
                raise RuntimeError("topology measurement failed") from exc

    val_bpb = float(np.mean(val_losses))
    skel = float(np.mean(val_skel)) if val_skel else float("nan")
    cd = float(np.mean(val_cd)) if val_cd else 0.0
    cc = float(np.mean(val_cc)) if val_cc else 0.0

    metrics = {
        "val_bpb": val_bpb,
        "avg_skel_dist": skel,
        "avg_centerline_dice": cd,
        "avg_cc_diff": cc,
    }
    if (
        not val_cc
        or not val_skel
        or not val_cd
        or not all(np.isfinite(value) for value in metrics.values())
    ):
        raise ValueError(
            "incomplete or nonfinite re-evaluation metrics; checkpoint was not updated"
        )

    print()
    print("=== TODAY'S MEASUREMENT (eval only, no training) ===")
    print(f"  val_bpb:             {val_bpb:.16f}")
    print(f"  avg_skel_dist:       {skel:.6f}")
    print(f"  avg_centerline_dice: {cd:.6f}")
    print(f"  avg_cc_diff:         {cc:.3f}")
    print(f"  val_f1:              {f1_metrics['val_f1']:.6f} (protocol {protocol})")
    print(f"  ap_prevalence_lift:  {f1_metrics['ap_prevalence_lift']:.4f}")
    print(f"  roc_auc:             {f1_metrics['roc_auc']:.4f}")
    # Calling every pixel ink scores F1 = 2p/(1+p) at every swept threshold, so
    # val_f1 means nothing until it clears this; it moves with the sample.
    prevalence = f1_metrics["val_positive_rate"]
    all_ink_f1 = 2 * prevalence / (1 + prevalence)
    print(
        f"  all-ink baseline F1: {all_ink_f1:.6f} (ink prevalence {prevalence:.4f}; "
        f"val_f1 margin {f1_metrics['val_f1'] - all_ink_f1:+.6f})"
    )
    print(
        f"  usable / requested:  {diag['usable_patches']}/{diag['requested_patches']} "
        f"(empty={diag['empty_target_patches']})"
    )

    print()
    print("=== DIFF: today vs stored ===")
    for name, today_val, stored_val in [
        ("val_f1", f1_metrics["val_f1"], chk.get("val_f1")),
        ("val_bpb", val_bpb, chk.get("val_bpb")),
        ("avg_skel_dist", skel, chk.get("avg_skel_dist")),
        ("avg_centerline_dice", cd, chk.get("avg_centerline_dice")),
        ("avg_cc_diff", cc, chk.get("avg_cc_diff")),
    ]:
        if stored_val is None:
            print(f"  {name}: today={today_val} stored=<MISSING>")
        else:
            delta = today_val - stored_val
            print(
                f"  {name}: today={today_val:.6f} stored={stored_val:.6f} delta={delta:+.6f}"
            )
    # Different samples have different all-ink floors; the margins are what compare.
    stored_f1, stored_p = chk.get("val_f1"), chk.get("val_positive_rate")
    stored_margin = (
        f"{stored_f1 - 2 * stored_p / (1 + stored_p):+.6f}"
        if stored_f1 is not None and stored_p is not None
        else "<MISSING>"
    )
    print(
        f"  val_f1 margin over all-ink: today={f1_metrics['val_f1'] - all_ink_f1:+.6f} "
        f"stored={stored_margin}"
    )

    if update_stored:
        print()
        print("Updating best_model.pt's stored metrics to today's values...")
        chk.update(f1_metrics)
        chk["val_protocol"] = protocol
        chk["validation_diag"] = diag
        chk["val_bpb"] = val_bpb
        chk["avg_skel_dist"] = skel
        chk["avg_centerline_dice"] = cd
        chk["avg_cc_diff"] = cc
        chk["reevaluation"] = {
            "methodology": protocol,
            "validation_uri": config.val_uri,
            # The slices the stored score was measured on; the model's own
            # training band, if any, stays in chk["config"].
            "depth_band": config.depth_band,
            "model_settings": settings,
            "input_settings": {
                name: getattr(config, name) for name in RECORDED_INPUT_SETTINGS
            },
            # What the checkpoint recorded before --unwarped corrected it.
            "overridden_input_settings": overridden,
            "requested_patches": diag["requested_patches"],
            "usable_patches": diag["usable_patches"],
            "dice_threshold": float(best_threshold),
            "topology_threshold": float(topo_threshold),
        }
        if overridden:
            chk["config"] = {**stored, "use_lasagna": config.use_lasagna}
        # The watchdog can start the loop while this runs, and anything may have
        # replaced best_model.pt since it was loaded (a promotion): writing the
        # loaded model back would undo it.
        refuse_beside_running_loop("at the end of the re-score")
        if _file_sha256("best_model.pt") != loaded_sha256:
            raise RuntimeError(
                "best_model.pt changed while it was being re-scored; it was not "
                "updated. Re-score the new file"
            )
        save_checkpoint_atomic(chk, "best_model.pt")
        print("Done.")


def main(argv=None) -> None:
    p = argparse.ArgumentParser()
    p.add_argument(
        "--update-stored",
        action="store_true",
        help="rewrite best_model.pt's stored scores (val_f1 and protocol included) to today's values",
    )
    p.add_argument(
        "--unwarped",
        action="store_true",
        help="score without a recorded lasagna warp that never ran; with "
        "--update-stored, record use_lasagna: false",
    )
    args = p.parse_args(argv)
    reevaluate(update_stored=args.update_stored, unwarped=args.unwarped)


if __name__ == "__main__":
    main()
