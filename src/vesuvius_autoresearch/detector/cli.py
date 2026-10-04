"""CLI: train / infer / eval / reproduce. `reproduce` runs convert (if needed) -> train ->
infer -> eval and asserts pixel-AUC >= 0.70 (proven recipe = 0.711)."""

import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np

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
    return evaluate(prob, label, mask, cfg, fragment_id=fragment_id)


def _reproduce(cfg):
    from .train import train

    repo = os.path.join(os.path.dirname(__file__), os.pardir, os.pardir, os.pardir)
    sys.path.append(os.path.abspath(os.path.join(repo, "repro", "gp_winner")))
    from convert_fragment import convert_fragment

    for fid in cfg.train_fragment_ids + [cfg.valid_fragment_id]:
        if not os.path.exists(os.path.join(cfg.data_root, fid, "layers")):
            convert_fragment(fid, "local_data", cfg.data_root)
    ckpt = train(cfg)
    card = _eval_fragment(cfg, ckpt, cfg.valid_fragment_id)
    print(
        f"reproduce: pixel_auc={card['pixel_auc']:.4f} threshold={card['threshold']:.2f}"
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
        "--output", required=True, help="path for the float32 NumPy probability map"
    )
    p_infer.add_argument("--batch-size", type=int, default=64)
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

        prob = infer(cfg, args.checkpoint, args.fragment, batch_size=args.batch_size)
        output = Path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("wb") as f:
            np.save(f, prob, allow_pickle=False)
        print(output)
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
