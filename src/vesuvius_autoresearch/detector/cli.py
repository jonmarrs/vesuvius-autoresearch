"""CLI: train / infer / eval / reproduce. `reproduce` runs convert (if needed) -> train ->
infer -> eval and asserts pixel-AUC >= 0.70 (proven recipe = 0.711)."""
import argparse
import os
import sys

import numpy as np

from .config import DetectorConfig
from .data import read_image_mask


def assert_auc(scorecard, target=0.70):
    auc = scorecard["pixel_auc"]
    assert auc >= target, f"pixel_auc {auc:.4f} below target {target:.2f}"


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
    label = (label > 0.5).astype(np.uint8)
    return evaluate(prob, label, mask.astype(bool), cfg, fragment_id=fragment_id)


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
    print(f"reproduce: pixel_auc={card['pixel_auc']:.4f} threshold={card['threshold']:.2f}")
    assert_auc(card)
    return card


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if argv == ["--help-check"]:
        return 0
    ap = argparse.ArgumentParser(prog="detector")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("reproduce")
    p_eval = sub.add_parser("eval")
    p_eval.add_argument("--checkpoint", required=True)
    p_eval.add_argument("--fragment", required=True)
    sub.add_parser("train")
    args = ap.parse_args(argv)
    cfg = DetectorConfig()
    if args.cmd == "reproduce":
        _reproduce(cfg)
    elif args.cmd == "train":
        from .train import train
        print(train(cfg))
    elif args.cmd == "eval":
        print(_eval_fragment(cfg, args.checkpoint, args.fragment))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
