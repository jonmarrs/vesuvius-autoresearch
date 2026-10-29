"""CLI: train / infer / eval / reproduce. `reproduce` runs convert (if needed) -> train ->
infer -> eval and asserts pixel-AUC >= 0.70 (proven recipe = 0.711)."""

import argparse
import glob
import json
import os
import sys
from pathlib import Path

from .config import DetectorConfig
from .data import read_image_mask


def assert_auc(scorecard, target=0.70):
    auc = scorecard["pixel_auc"]
    if not auc >= target:
        raise AssertionError(f"pixel_auc {auc:.4f} below target {target:.2f}")


def _eval_fragment(cfg, ckpt, fragment_id):
    from .eval import evaluate
    from .infer import infer

    prob = infer(cfg, ckpt, fragment_id)
    _, label, mask = read_image_mask(cfg, fragment_id)
    # read_image_mask pads `mask` (frag_mask) to a tile multiple but leaves `label`
    # unpadded; crop both prob and mask to the label shape so all three align.
    h, w = label.shape
    prob = prob[:h, :w]
    mask = mask[:h, :w]
    return evaluate(prob, label, mask, cfg, fragment_id=fragment_id, checkpoint=ckpt)


def _is_converted(cfg, fragment_id):
    """Whether every file data.read_image_mask reads for fragment_id is there, found as
    it finds them: each layer in cfg's range, the mask, and exactly one *inklabels.*
    (under any name, so a villa-style <id>_inklabels.tiff counts)."""
    root = os.path.join(cfg.data_root, fragment_id)
    needed = [
        os.path.join(root, "layers", f"{i:02d}.tif")
        for i in range(cfg.start_idx, cfg.end_idx)
    ]
    needed.append(os.path.join(root, f"{fragment_id}_mask.png"))
    labels = glob.glob(os.path.join(root, "*inklabels.*"))
    return all(os.path.exists(p) for p in needed) and len(labels) == 1


def _ensure_converted(cfg, src_root="local_data"):
    """Convert each reproduce fragment unless every file it reads is already there.

    The check is per file, over cfg's own layer range: a conversion that was
    interrupted, or made for another start_idx/end_idx, is redone rather than
    trusted because its layers/ directory exists. Returns the fragments converted.
    """
    repo = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    gp_winner = os.path.abspath(os.path.join(repo, "repro", "gp_winner"))
    if gp_winner not in sys.path:
        sys.path.append(gp_winner)
    from convert_fragment import convert_fragment

    done = []
    for fid in cfg.train_fragment_ids + [cfg.valid_fragment_id]:
        if not _is_converted(cfg, fid):
            convert_fragment(fid, src_root, cfg.data_root, cfg.start_idx, cfg.end_idx)
            done.append(fid)
    return done


def _reproduce(cfg):
    """Convert, train, and score the checkpoint train() returns on the held-out fragment.

    That checkpoint is the epoch with the lowest mean training loss (train's
    ModelCheckpoint), not the best held-out epoch. REPRODUCTION.md's 0.7090 is
    epoch 7, the best of 12 by ROC-AUC on that same fragment, re-scored with the
    uniform blend; this does not repeat that selection. The checkpoint scored is
    printed, and named in the scorecard.
    """
    from .train import train

    _ensure_converted(cfg)
    ckpt = train(cfg)
    card = _eval_fragment(cfg, ckpt, cfg.valid_fragment_id)
    print(
        f"reproduce: checkpoint={ckpt} pixel_auc={card['pixel_auc']:.4f} "
        f"threshold={card['threshold']:.2f}"
    )
    assert_auc(card)
    return card


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--help-check"]:
        return 0
    ap = argparse.ArgumentParser(prog="detector")
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--config", help="JSON DetectorConfig overrides (defaults otherwise)"
    )
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reproduce", parents=[common])
    p_eval = sub.add_parser("eval", parents=[common])
    p_eval.add_argument("--checkpoint", required=True)
    p_eval.add_argument("--fragment", required=True)
    sub.add_parser("train", parents=[common])
    p_infer = sub.add_parser("infer", parents=[common])
    p_infer.add_argument("--checkpoint", required=True)
    p_infer.add_argument("--fragment", required=True)
    p_infer.add_argument(
        "--output", required=True, help="exact path for the prediction artifact"
    )
    p_infer.add_argument("--batch-size", type=int, default=64)
    p_infer.add_argument(
        "--output-format",
        choices=("npy", "npz"),
        default="npy",
        help="npy probability map (default) or npz probability/coverage/fragment-mask bundle",
    )
    p_infer.add_argument(
        "--require-full-coverage",
        action="store_true",
        help="fail without replacing output if any fragment pixel has no prediction",
    )
    p_measure = sub.add_parser("measure", parents=[common])
    p_measure.add_argument(
        "--checkpoint", default="models/detector/detector_epoch=7.ckpt"
    )
    p_measure.add_argument("--same", default="PHercParis2Fr143")
    p_measure.add_argument("--cross", default="20230702185753")
    args = ap.parse_args(argv)
    try:
        overrides = {}
        if args.config:
            with open(args.config) as f:
                overrides = json.load(f)
            if not isinstance(overrides, dict):
                raise ValueError("configuration must be a JSON object")
        cfg = DetectorConfig(**overrides)
        cfg.validate()
    except (OSError, TypeError, ValueError) as exc:
        ap.error(f"invalid detector configuration: {exc}")
    if args.cmd == "reproduce":
        _reproduce(cfg)
    elif args.cmd == "train":
        from .train import train

        print(train(cfg))
    elif args.cmd == "eval":
        print(_eval_fragment(cfg, args.checkpoint, args.fragment))
    elif args.cmd == "infer":
        from .infer import infer
        from .prediction import prediction_inputs, validate_output, write_prediction

        output = Path(args.output)
        inputs = prediction_inputs(cfg, args.checkpoint, args.fragment, args.config)
        validate_output(output, inputs)
        result = infer(
            cfg,
            args.checkpoint,
            args.fragment,
            batch_size=args.batch_size,
            return_details=True,
            require_full_coverage=args.require_full_coverage,
        )
        write_prediction(output, result, args.output_format, inputs)
        print(output)
        summary = result.summary
        print(
            f"coverage: {summary['predicted_pixels']}/{summary['valid_pixels']} "
            f"fragment pixels ({summary['coverage_fraction']:.2%}); "
            f"{summary['uncovered_pixels']} uncovered"
        )
    elif args.cmd == "measure":
        from .measure import measure

        targets = [(args.same, "scroll2_same"), (args.cross, "scroll1_cross")]
        rows = measure(cfg, args.checkpoint, targets)
        for fid, m in rows.items():
            if "error" in m:
                print(
                    f"{fid} [{m.get('scroll_label')}]: ERROR: {m['error']}",
                    file=sys.stderr,
                )
                continue
            print(
                f"{fid} [{m.get('scroll_label')}]: "
                f"val_f1={m.get('val_f1')} ap={m.get('average_precision')} "
                f"lift={m.get('ap_prevalence_lift')}"
            )
        return int(any("error" in m for m in rows.values()))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
