# Multi-Scroll / Cross-Scroll Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure the true cross-scroll generalization gap (held-out PHerc1667Fr3) and test whether multi-scroll training of the 64px resenc CNN closes it.

**Architecture:** Fix the over-filled labels, measure the baseline cross-scroll AUC of the current model, then warm-start resenc from best_model and train on 3 scrolls (ConcatDataset, already supported), validating on the held-out scroll. Staged smoke → probe → full run. Config-only except a small reusable measurement script.

**Tech Stack:** PyTorch, the existing `train.py` multi-URI pipeline, a new `scripts/measure_ink_auc.py`. Interpreter: `.venv` via `PYTHONPATH=. .venv/bin/python`.

**Context for the implementer:**
- **URI layout matters.** Fragments with `surface_volume.zarr/` use `local_data/<frag>/surface_volume.zarr`. Fragments with the bare OME-Zarr `0/` layout (Fr34/Fr39/Fr8/Fr3) MUST use **`local_data/<frag>/0`** — this makes both the loader (finds `0/.zarray` directly) and train.py's label resolution (`os.path.dirname(uri)` → the fragment dir) work.
- **Loop:** continuously running (watchdog). To pause: `touch .loop_paused`, kill PIDs. Resume: `bash start.sh`. Check GPU via `nvidia-smi` (~6 MiB = idle); do NOT trust `pgrep -f` (self-matches).
- Resenc baseline (same-scroll): AUC 0.74 train / 0.61 val. `best_model.pt` must be recoverable (backed up in Task 1).
- Held-out scroll = **PHerc1667Cr1Fr3**. Training scrolls = PHercParis2Fr47, PHercParis1Fr34, PHercParis1Fr39, PHerc51Cr4Fr8.

## File Structure

- `scripts/measure_ink_auc.py` (create) — per-patch ink AUC on arbitrary fragment dirs.
- `local_data/{PHercParis1Fr34,PHercParis1Fr39,PHerc51Cr4Fr8,PHerc1667Cr1Fr3}/inklabels_filled.png` → `.overfilled.bak` (move).
- `best_model.pt.prebkup_multiscroll` (create) — baseline backup.
- `/tmp/cfg_multiscroll.json` (ephemeral) — experiment config.
- `FINDINGS.md` (modify, Task 6) — record result.

---

## Task 1: Prerequisites — label fix, backup, measurement script

**Files:** Create `scripts/measure_ink_auc.py`; move 4 label files; back up best_model.

- [ ] **Step 1: Move the over-filled labels aside (reversible)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
for d in PHercParis1Fr34 PHercParis1Fr39 PHerc51Cr4Fr8 PHerc1667Cr1Fr3; do
  mv "local_data/$d/inklabels_filled.png" "local_data/$d/inklabels_filled.png.overfilled.bak"
done
echo "remaining inklabels_filled.png (expect 0): $(ls local_data/{PHercParis1Fr34,PHercParis1Fr39,PHerc51Cr4Fr8,PHerc1667Cr1Fr3}/inklabels_filled.png 2>/dev/null | wc -l)"
```
Expected: 0. (Now the pipeline resolves these to the good `inklabels.png`.)

- [ ] **Step 2: Back up best_model**

```bash
cp best_model.pt best_model.pt.prebkup_multiscroll
ls -la best_model.pt.prebkup_multiscroll | awk '{print $5, $9}'
```

- [ ] **Step 3: Write the reusable measurement script** `scripts/measure_ink_auc.py`:

```python
"""Per-patch ink-vs-background AUC of a checkpoint on one or more fragment dirs.

A fragment dir holds the CT volume (either `surface_volume.zarr/` or the bare
OME-Zarr `0/` layout) plus `inklabels.png` and `mask.png`. AUC is the honest
ink-discrimination signal (0.5 = chance).

Usage:
    python scripts/measure_ink_auc.py --checkpoint best_model.pt \
        --fragments local_data/PHerc1667Cr1Fr3 [more dirs...] [--device cuda]
"""
import argparse, os, sys
import numpy as np
import torch
from sklearn.metrics import roc_auc_score

_R = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _R)
sys.path.insert(0, os.path.join(_R, "scripts", "training"))
from torch.utils.data import DataLoader
from train import ExperimentConfig, load_shape_compatible_state
from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset


def _volume_uri(frag_dir):
    if os.path.exists(os.path.join(frag_dir, "surface_volume.zarr")):
        return os.path.join(frag_dir, "surface_volume.zarr")
    return os.path.join(frag_dir, "0")  # bare OME-Zarr level 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--fragments", nargs="+", required=True)
    ap.add_argument("--device", default="cuda" if torch.cuda.is_available() else "cpu")
    ap.add_argument("--n", type=int, default=30)
    args = ap.parse_args()

    device = torch.device(args.device)
    chk = torch.load(args.checkpoint, map_location="cpu", weights_only=False)
    s = chk.get("config", {})
    arch = s.get("architecture", "resenc_unet")
    ps, nl = s.get("patch_size", 64), s.get("num_layers", 16)
    config = ExperimentConfig.load("config.json")
    model = build_inference_model(
        architecture=arch, patch_size=ps, num_layers=nl,
        base_feat=s.get("base_feat", 64), num_blocks=s.get("num_blocks", 16),
        num_heads=s.get("num_heads", 8), dropout=s.get("dropout", 0.0),
        use_ridges=s.get("use_ridges", config.use_ridges),
        multi_task_heads=s.get("multi_task_heads", False),
    ).to(device)
    load_shape_compatible_state(model, chk["model_state_dict"], args.checkpoint)
    model.eval()
    print(f"ckpt={args.checkpoint} arch={arch} use_ridges={s.get('use_ridges')}")

    for frag in args.fragments:
        uri = _volume_uri(frag)
        ds = VesuviusLabeledDataset(
            uri, os.path.join(frag, "inklabels.png"), os.path.join(frag, "mask.png"),
            ps, nl + 8, seed=7, cache_dir=config.cache_dir,
            use_ridges=s.get("use_ridges", config.use_ridges),
            ridge_sigma=getattr(config, "ridge_sigma", 2.0), use_lasagna=False, require_ink=True)
        dl = iter(DataLoader(ds, batch_size=8, num_workers=0))
        aucs = []
        with torch.no_grad():
            while len(aucs) < args.n:
                try:
                    x_raw, target, _ = next(dl)
                except StopIteration:
                    break
                x = x_raw[:, :, 4:4 + nl].to(device)
                if target is None or target.numel() == 0:
                    continue
                target = target.to(device)
                if target.dim() == 3:
                    target = target.unsqueeze(1)
                if torch.sum(target.float()) < 1.0:
                    continue
                out = model(x)
                if isinstance(out, tuple):
                    out = out[0]
                prob = torch.sigmoid(out).float().cpu().numpy()
                tgt = (target.cpu().numpy() > 0.5).astype(int)
                for bi in range(prob.shape[0]):
                    p, t = prob[bi].ravel(), tgt[bi].ravel()
                    if t.min() != t.max():
                        aucs.append(roc_auc_score(t, p))
        a = np.array(aucs)
        name = os.path.basename(frag.rstrip("/"))
        print(f"{name}: AUC mean={a.mean():.3f} median={np.median(a):.3f} n={len(a)}" if len(a) else f"{name}: no usable patches")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Verify labels resolve to the good ones**

```bash
for d in PHercParis1Fr34 PHerc1667Cr1Fr3; do
  .venv/bin/python -c "from PIL import Image;import numpy as np;Image.MAX_IMAGE_PIXELS=None;print('$d inklabels frac', round(float((np.array(Image.open('local_data/$d/inklabels.png').convert('L'))>127).mean()),3))"
done
test -f local_data/PHerc1667Cr1Fr3/0/.zarray && echo "Fr3 zarr OK"
```
Expected: ink fractions ~0.057–0.079 (not 0.9); `Fr3 zarr OK`.

- [ ] **Step 5: Commit the measurement script** (the label moves/backup are local-only, not committed)

```bash
git add scripts/measure_ink_auc.py
git commit -m "feat(eval): per-fragment ink AUC measurement script (cross-scroll)"
```

---

## Task 2: Pause loop + cross-scroll baseline

- [ ] **Step 1: Pause the loop**

```bash
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|training/train.py" | grep -v grep | awk '{print $1}' | xargs -r kill -9
sleep 4
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~6 MiB
```
Expected ~6 MiB. (Kill any orphan train.py too.)

- [ ] **Step 2: Measure the current model's TRUE cross-scroll AUC (held-out PHerc1667Fr3) and a same-scroll reference**

```bash
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py --checkpoint best_model.pt --device cuda \
  --fragments local_data/PHerc1667Cr1Fr3 local_data/PHercParis2Fr143 2>&1 | grep -E "ckpt=|AUC|no usable" | tail -4
```
Expected: a `PHerc1667Cr1Fr3: AUC mean=…` (the true cross-scroll number — likely well below the same-scroll 0.61) and `PHercParis2Fr143: AUC mean=…` (~0.61 reference). **Record both** — the Fr3 number is the baseline to beat.

---

## Task 3: Build multi-scroll config + smoke gate

- [ ] **Step 1: Build the config**

```bash
.venv/bin/python - <<'PYEOF'
import json
c = json.load(open("config.json"))
c["uris"] = [
    "local_data/PHercParis2Fr47/surface_volume.zarr",
    "local_data/PHercParis1Fr34/0",
    "local_data/PHercParis1Fr39/0",
    "local_data/PHerc51Cr4Fr8/0",
]
c["val_uri"] = "local_data/PHerc1667Cr1Fr3/0"
c["unlabeled_uris"] = ["local_data/PHercParis2Fr47/surface_volume.zarr"]
c["architecture"] = "resenc_unet"
c["loss_ink_bce"] = 0.6; c["loss_ink_dice"] = 0.2
c["use_uamt"] = False; c["use_betti_loss"] = False; c["use_cldice"] = False
c["time_budget"] = 60
json.dump(c, open("/tmp/cfg_multiscroll.json", "w"), indent=2)
print("uris:", len(c["uris"]), "| val:", c["val_uri"], "| arch:", c["architecture"])
PYEOF
```
Expected: `uris: 4 | val: local_data/PHerc1667Cr1Fr3/0 | arch: resenc_unet`.

- [ ] **Step 2: Smoke (build + ConcatDataset + warm-start + fwd/bwd)**

```bash
PYTHONPATH=. timeout 400 .venv/bin/python scripts/training/train.py --smoke --config /tmp/cfg_multiscroll.json > /tmp/ms_smoke.log 2>&1
echo "exit $?"; grep -iE "PREFLIGHT|Error|Traceback|Loading weights from best_model|Initializing" /tmp/ms_smoke.log | grep -ivE "warn|fft" | tail -5
```
Expected: `PREFLIGHT OK`. **GATE:** if it fails (e.g. a fragment fails to load, label-path error, or ConcatDataset error), inspect `/tmp/ms_smoke.log`; fix if small and well-understood (e.g. a URI path), else STOP and report.

---

## Task 4: Probe gate (~20 min)

- [ ] **Step 1: Raise budget and run the probe**

```bash
.venv/bin/python -c "import json;c=json.load(open('/tmp/cfg_multiscroll.json'));c['time_budget']=1200;json.dump(c,open('/tmp/cfg_multiscroll.json','w'),indent=2)"
PYTHONPATH=. nohup .venv/bin/python scripts/training/train.py --config /tmp/cfg_multiscroll.json > /tmp/ms_probe.log 2>&1 &
echo "probe PID $!"
until grep -qE "Step 0000|Traceback|Error" /tmp/ms_probe.log 2>/dev/null; do sleep 5; done
grep -iE "Initializing LOCAL|Loading weights from best_model|Step 0000|Traceback" /tmp/ms_probe.log | grep -ivE "warn|fft" | head -5
```
Expected: it warm-starts from best_model, initializes on the 4 URIs, and reaches `Step 0000`. If `Traceback`, STOP and report.

- [ ] **Step 2: Wait for the probe, GATE on learning + finite cross-scroll metrics** (replace `<PID>`)

```bash
until ! kill -0 <PID> 2>/dev/null; do sleep 20; done; echo "probe done"
grep -oE "Step [0-9]+ \| Loss: [0-9.]+" /tmp/ms_probe.log | sed -n '1p;$p'
grep -iE "val_bpb \(Off|avg_centerline|Instability|NaN|RESULT" /tmp/ms_probe.log | grep -ivE "warn" | tail -4
```
**GATE:** end loss below start; `val_bpb` on Fr3 is a real number (not 1.0); no NaN. If it fails, STOP and report (multi-scroll training isn't healthy — likely a data/label issue on one fragment).

---

## Task 5: Full run + cross-scroll AUC comparison

- [ ] **Step 1: Full run**

```bash
.venv/bin/python -c "import json;c=json.load(open('/tmp/cfg_multiscroll.json'));c['time_budget']=3600;json.dump(c,open('/tmp/cfg_multiscroll.json','w'),indent=2)"
PYTHONPATH=. nohup .venv/bin/python scripts/training/train.py --config /tmp/cfg_multiscroll.json > /tmp/ms_full.log 2>&1 &
echo "full PID $!"
until ! kill -0 <PID> 2>/dev/null; do sleep 30; done; echo "full run done"
grep -iE "val_bpb \(Off|avg_centerline|RESULT|NEW BEST" /tmp/ms_full.log | grep -ivE "warn" | tail -4
```

- [ ] **Step 2: Identify the trained model** (best_model.pt if it "improved" vs the stored Fr143 criterion, else last_model.pt)

```bash
.venv/bin/python -c "import torch;c=torch.load('last_model.pt',map_location='cpu',weights_only=False);print('last_model arch',c.get('config',{}).get('architecture'),'val_uri',c.get('config',{}).get('val_uri'))"
# pick the checkpoint whose stored config.val_uri == the Fr3 path; that is the multi-scroll model
```

- [ ] **Step 3: Measure the multi-scroll model's cross-scroll AUC on the held-out scroll**

```bash
# use whichever of last_model.pt / best_model.pt is the multi-scroll run (Step 2):
PYTHONPATH=. .venv/bin/python scripts/measure_ink_auc.py --checkpoint <multiscroll_ckpt> --device cuda \
  --fragments local_data/PHerc1667Cr1Fr3 2>&1 | grep -E "AUC|no usable" | tail -2
```
Compare to the Task 2 baseline. **Win:** Fr3 AUC ≥ baseline + 0.03. **Neutral/negative:** ≤ baseline.

---

## Task 6: Record result, restore baseline + loop

- [ ] **Step 1: Decide on best_model** — if the full run overwrote `best_model.pt` (different val_uri/criterion) and you do NOT want the multi-scroll model as the loop's resenc baseline, restore it:

```bash
.venv/bin/python -c "import torch;print('current best_model val_uri', torch.load('best_model.pt',map_location='cpu',weights_only=False).get('config',{}).get('val_uri'))"
# If it shows the Fr3 path (multi-scroll overwrote it) and the experiment was neutral/negative:
cp best_model.pt.prebkup_multiscroll best_model.pt   # restore the original resenc baseline
```
(If the experiment WON and you want multi-scroll as the new baseline, keep it and tell the user — that's a loop-direction change to confirm separately.)

- [ ] **Step 2: Record in FINDINGS.md** under "What we learned":

```markdown
  - *Cross-scroll generalization (held-out PHerc1667Fr3):* the single-scroll
    (Fr47-trained) model scores AUC <B> on the held-out scroll vs ~0.61
    same-scroll — the real gap. Training on 3 scrolls (Fr47+Fr34+Fr39+Fr8)
    changes held-out AUC to <M> (<helped / did not close the gap>).
```

- [ ] **Step 3: Restore the loop**

```bash
rm -f /tmp/cfg_multiscroll.json
bash start.sh; sleep 10
grep -c ModuleNotFoundError autoresearch.out   # expect 0
tail -2 autoresearch.out
```
Expected: 0 import crashes; a cycle running. (Note: the loop's `config.json` still has the single-scroll Fr47/Fr143 setup unless you intentionally changed it; the experiment used a temp config, so the loop is unchanged.)

- [ ] **Step 4: Commit FINDINGS + push**

```bash
git add FINDINGS.md
git commit -m "docs(findings): cross-scroll generalization experiment (baseline <B> -> multi-scroll <M>)"
git push origin main
```

---

## Verification (whole experiment)

- [ ] Over-filled labels moved aside; the 4 fragments resolve to `inklabels.png` (~0.06–0.08 ink).
- [ ] Baseline: best_model's PHerc1667Fr3 AUC recorded (the true cross-scroll gap).
- [ ] Smoke + probe gates passed (multi-URI builds, warm-starts, learns, finite Fr3 val), or stopped with a report.
- [ ] Full run completed; multi-scroll model's Fr3 AUC measured and compared; recorded in FINDINGS.md.
- [ ] `best_model.pt` is the intended one (original restored if experiment was neutral/negative; backup retained either way).
- [ ] Loop restarted clean (0 import crashes), `.loop_paused` cleared.
