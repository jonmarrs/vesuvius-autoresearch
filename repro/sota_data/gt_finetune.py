"""Ground-truth fine-tuning POC (operational): register human labels for 2 Scroll-1 segments
onto SOTA geometry, fine-tune the best distilled model (arm C) on them, and measure on the
held-out 20231210121321 GT -- a before/after test of whether ground-truth supervision reads
held-out ink where distillation-from-canon (arm C, 0.558) could not."""
import glob
import json
import os
import sys

import cv2
import numpy as np

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.gt_register import gt_prep_fragment

TRAIN_REGIONS = [("20230702185753", 4000, 2500), ("20230702185753", 7000, 4000),
                 ("20231005123336", 4000, 2500), ("20231005123336", 7000, 4000)]
SIZE = 4096
GT_ROOT = "local_data/sota_gt"
MODEL_DIR = "models/detector_gt_finetune"
ARM_C_CKPT = "models/detector_xscroll_c/detector_epoch=11.ckpt"
HELDOUT_LABEL = "local_data/sota_registration/heldout/registered_label_l2region.png"
HELDOUT_FRAG_ROOT = "local_data/sota_distill"
HELDOUT_FRAG_ID = "20231210121321_y4000_x2500"
PREP_JSON = "reports/detector/gt_finetune_prep.json"
REPORT_MD = "reports/detector/gt_finetune_heldout.md"
REPORT_JSON = "reports/detector/gt_finetune_heldout.json"
FT_LR = 8e-6
FT_EPOCHS = 6


def cmd_prep():
    os.makedirs("reports/detector", exist_ok=True)
    infos = [gt_prep_fragment(seg, y0, x0, SIZE, GT_ROOT) for (seg, y0, x0) in TRAIN_REGIONS]
    kept = [i["frag_id"] for i in infos if i["passed"]]
    with open(PREP_JSON, "w") as f:
        json.dump({"regions": infos, "kept": kept}, f, indent=2)
    print(f"kept {len(kept)}/{len(infos)} GT training regions: {kept}", flush=True)
    if not kept:
        raise ValueError("no GT training region passed the alignment gate")


def cmd_finetune():
    import pytorch_lightning as pl
    import torch
    from pytorch_lightning.callbacks import ModelCheckpoint
    from pytorch_lightning.loggers import CSVLogger
    from torch.utils.data import DataLoader
    from vesuvius_autoresearch.detector.config import DetectorConfig
    from vesuvius_autoresearch.detector.data import build_datasets
    from vesuvius_autoresearch.detector.model import DetectorModel
    with open(PREP_JSON) as f:
        kept = json.load(f)["kept"]
    if not kept:
        raise ValueError(f"{PREP_JSON} has no kept regions; run prep")
    cfg = DetectorConfig(data_root=GT_ROOT, model_dir=MODEL_DIR, lr=FT_LR, epochs=FT_EPOCHS,
                         train_fragment_ids=kept, valid_fragment_id=kept[0])
    cfg.validate_window()
    pl.seed_everything(cfg.seed, workers=True)
    torch.set_float32_matmul_precision("medium")
    os.makedirs(MODEL_DIR, exist_ok=True)
    train_ds, valid_ds, _, pred_shape = build_datasets(cfg)
    tl = DataLoader(train_ds, batch_size=cfg.train_batch_size, shuffle=True,
                    num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    vl = DataLoader(valid_ds, batch_size=cfg.train_batch_size, shuffle=False,
                    num_workers=cfg.num_workers, pin_memory=True, drop_last=True)
    # init from arm C (distilled); configure_optimizers rebuilds AdamW(lr=cfg.lr=FT_LR)
    model = DetectorModel.load_from_checkpoint(ARM_C_CKPT, cfg=cfg, pred_shape=pred_shape,
                                               weights_only=False)
    ckpt_cb = ModelCheckpoint(filename="ft_{epoch}", dirpath=MODEL_DIR,
                              monitor="train/total_loss", mode="min", save_top_k=-1)
    trainer = pl.Trainer(max_epochs=cfg.epochs, accelerator="auto", devices=1,
                         logger=CSVLogger(save_dir=MODEL_DIR, name="logs"),
                         precision="16-mixed" if torch.cuda.is_available() else "32-true",
                         gradient_clip_val=1.0, gradient_clip_algorithm="norm",
                         callbacks=[ckpt_cb], enable_progress_bar=False)
    trainer.fit(model, train_dataloaders=tl, val_dataloaders=vl)
    print("finetune done:", ckpt_cb.best_model_path, flush=True)


def _score_ckpt(ckpt):
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics
    prob = dr._measure(ckpt, HELDOUT_FRAG_ID, data_root=HELDOUT_FRAG_ROOT)[1]
    gt = (cv2.imread(HELDOUT_LABEL, 0) > 127).astype(np.uint8)
    h, w = gt.shape
    m = segmentation_metrics(prob[:h, :w], gt, np.ones((h, w), bool))
    m.pop("metrics_by_threshold", None)
    return m


def cmd_score():
    if not os.path.exists(HELDOUT_LABEL):
        raise ValueError(f"{HELDOUT_LABEL} missing; the slice-6 held-out registration is "
                         "required (run register_run warp_obj heldout first)")
    fts = sorted(glob.glob(os.path.join(MODEL_DIR, "ft_epoch=*.ckpt")),
                 key=lambda p: int(p.split("epoch=")[1].split(".")[0]))
    if not fts:
        raise ValueError(f"no fine-tuned checkpoints in {MODEL_DIR}; run finetune")
    # final epoch (no selection on the held-out test set)
    ft_ckpt = fts[-1]
    before = _score_ckpt(ARM_C_CKPT)
    after = _score_ckpt(ft_ckpt)
    cols = dr.COLS

    def row(name, m):
        return f"| {name} | " + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in cols) + " |"

    with open(PREP_JSON) as f:
        prep = json.load(f)
    lines = ["# Ground-truth fine-tuning vs distillation (held-out 20231210121321 GT)", "",
             "**Before/after fine-tuning the best distilled model (arm C) on human "
             "ground-truth labels** registered onto SOTA geometry for 2 Scroll-1 segments "
             f"({len(prep['kept'])}/4 regions passed the teacher-free alignment gate). All "
             "rows scored against the held-out registered ground truth of a segment NO "
             "model trained on. POC: only 2 training segments -- a near-chance 'after' is "
             "confounded by data thinness, a clear lift is not.", "",
             f"Fine-tune: init arm C `{os.path.basename(ARM_C_CKPT)}`, lr {FT_LR}, "
             f"{FT_EPOCHS} epochs, final epoch `{os.path.basename(ft_ckpt)}`.", "",
             "| model (vs held-out GT) | " + " | ".join(cols) + " |",
             "|---|" + "|".join(["---"] * len(cols)) + "|",
             row("arm C (distilled, before)", before),
             row("arm C + GT fine-tune (after)", after)]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump({"before_armC": before, "after_gt_finetune": after,
                   "finetune_ckpt": os.path.basename(ft_ckpt), "prep": prep},
                  f, indent=2, default=float)
    print(f"BEFORE arm C roc_auc={before.get('roc_auc', float('nan')):.4f}  "
          f"AFTER gt-finetune roc_auc={after.get('roc_auc', float('nan')):.4f}", flush=True)


if __name__ == "__main__":
    cmds = {"prep": cmd_prep, "finetune": cmd_finetune, "score": cmd_score}
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(f"usage: python -m repro.sota_data.gt_finetune {{{'|'.join(cmds)}}}")
    cmds[sys.argv[1]]()
