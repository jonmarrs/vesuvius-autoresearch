# Augmentation Ablation (none vs full) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decide whether the production regime's heavy augmentation suppresses the learnable ink signal, by training a fresh resenc with augmentation fully off vs full and comparing train+val pooled pixel AUC.

**Architecture:** Add one gated `disable_augmentation` master switch to `train.py` (default off → loop byte-identical) that short-circuits the three unconditional augmentation sites (apply_augmentations, z-compression, mixup/cutmix). Run two fresh `checkpoint_out`-isolated arms (full vs none, ~2h each) with the existing `eval_every_steps` hook, then measure train+val pooled pixel AUC post-hoc and classify.

**Tech Stack:** Python, PyTorch, NumPy, scikit-learn, pytest. Reuses the `eval_every_steps` hook, `checkpoint_out`, `scripts/pixel_auc.py`, `build_inference_model`.

**Spec:** `docs/superpowers/specs/2026-06-14-augmentation-ablation-design.md`

---

## File Structure

- `scripts/training/train.py` (modify) — `disable_augmentation` field + gates at 3 sites.
- `tests/test_disable_augmentation.py` (create) — `apply_augmentations` identity test.
- `experiments/aug_ablation/cfg_aug_full.json`, `cfg_aug_none.json` (create).
- `experiments/aug_ablation/*.pt`, `*.csv`, `*.log` (runtime, gitignored).
- `FINDINGS.md`, memory (modify).

---

## Task 1: `disable_augmentation` master switch (TDD)

**Files:**
- Modify: `scripts/training/train.py` (config dataclass; `apply_augmentations` ~line 819; z-compression ~line 1531; mixup ~line 1588)
- Test: `tests/test_disable_augmentation.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_disable_augmentation.py
import os
import sys
from types import SimpleNamespace

import torch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts", "training"))

from train import apply_augmentations  # noqa: E402


def test_disable_augmentation_is_identity():
    x = torch.rand(2, 1, 16, 64, 64)
    ti = torch.rand(2, 1, 64, 64)
    tf = torch.rand(2, 1, 1, 64, 64)
    cfg = SimpleNamespace(disable_augmentation=True)
    ox, oti, otf = apply_augmentations(x, ti, tf, 0, 1000, config=cfg)
    # identity: same tensor objects returned, untouched
    assert ox is x and oti is ti and otf is tf
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch && PYTHONPATH=. .venv/bin/python -m pytest tests/test_disable_augmentation.py -v`
Expected: FAIL — without the early return, `apply_augmentations` runs transforms (and likely errors or returns altered tensors; the `is` identity assertion fails).

- [ ] **Step 3: Add the config field**

In the `ExperimentConfig` dataclass, find:
```python
    eval_every_steps: int = 0
    eval_sample_patches: int = 250
```
Replace with:
```python
    eval_every_steps: int = 0
    eval_sample_patches: int = 250
    disable_augmentation: bool = False
```

- [ ] **Step 4: Add the early return in `apply_augmentations`**

Find (the end of the docstring + the first body line):
```python
    x: (B, 1, D, H, W); target_ink: (B, 1, H, W); target_fiber: (B, 1, 1, H, W).
    """
    aug_mode = getattr(config, "aug_mode", "albumentations")
```
Replace with:
```python
    x: (B, 1, D, H, W); target_ink: (B, 1, H, W); target_fiber: (B, 1, 1, H, W).
    """
    if getattr(config, "disable_augmentation", False):
        # Ablation master switch: return inputs untouched (no rot90/flip/scroll/etc).
        return x, target_ink, target_fiber

    aug_mode = getattr(config, "aug_mode", "albumentations")
```

- [ ] **Step 5: Gate the z-compression branch**

Find (unique — `z_start` appears only here):
```python
            z_start = np.random.randint(0, 8)
            if np.random.rand() > 0.8:
```
Replace with:
```python
            z_start = np.random.randint(0, 8)
            if (
                not getattr(config, "disable_augmentation", False)
            ) and np.random.rand() > 0.8:
```
(When disabled, the `else` branch — the plain `x_orig = x_raw[:, :, z_start:z_start+config.num_layers]` central slice — always runs; the random z-compression resize is skipped. The mild `z_start` window selection is retained per spec.)

- [ ] **Step 6: Gate the mixup/cutmix block**

Find:
```python
        if x_orig.size(0) > 1:
            r = np.random.rand()
            if r < 0.2:
                x_orig, target_ink, target_fiber, _ = mixup_data(
```
Replace the first line only (keep the body) so it reads:
```python
        if (not getattr(config, "disable_augmentation", False)) and x_orig.size(0) > 1:
            r = np.random.rand()
            if r < 0.2:
                x_orig, target_ink, target_fiber, _ = mixup_data(
```

- [ ] **Step 7: Run the test to verify it passes**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_disable_augmentation.py -v`
Expected: PASS (1 passed)

- [ ] **Step 8: Verify the default path is unchanged (import + existing tests)**

Run: `PYTHONPATH=. .venv/bin/python -m pytest tests/test_confidence_weighted_loss.py tests/test_disable_augmentation.py -v`
Expected: 4 passed. (Confirms train.py still imports and the gated change didn't break the loss path.)

- [ ] **Step 9: Commit**

```bash
git add scripts/training/train.py tests/test_disable_augmentation.py
git commit -m "feat(train): disable_augmentation master switch for ablation"
```
(ruff-format may reformat+abort; re-add and re-run if so.)

---

## Task 2: Configs + smoke gate

**Files:**
- Create: `experiments/aug_ablation/cfg_aug_full.json`, `cfg_aug_none.json`

- [ ] **Step 1: Write both configs**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p experiments/aug_ablation
.venv/bin/python - <<'PYEOF'
import json, copy
c = json.load(open("config.json"))
base = {
    "uris": ["local_data/PHercParis2Fr47/surface_volume.zarr"],
    "val_uri": "local_data/PHercParis2Fr143_Vregion/surface_volume.zarr",
    "time_budget": 7200, "pinned": False, "pseudo_label_dir": None,
    "use_uamt": False, "use_wandb": False, "use_confidence_weight": False,
    "architecture": "resenc_unet", "eval_every_steps": 1000, "eval_sample_patches": 250,
}
full = copy.deepcopy(c); full.update(base)
full.update({"disable_augmentation": False, "checkpoint_out": "experiments/aug_ablation/full_model.pt"})
none = copy.deepcopy(c); none.update(base)
none.update({"disable_augmentation": True, "checkpoint_out": "experiments/aug_ablation/none_model.pt"})
json.dump(full, open("experiments/aug_ablation/cfg_aug_full.json","w"), indent=2)
json.dump(none, open("experiments/aug_ablation/cfg_aug_none.json","w"), indent=2)
print("wrote cfg_aug_full.json (disable_augmentation=False) and cfg_aug_none.json (=True)")
PYEOF
```

- [ ] **Step 2: Gitignore runtime artifacts**

Append to `.gitignore`:
```
experiments/aug_ablation/*.pt
experiments/aug_ablation/*.curve.csv
experiments/aug_ablation/*.log
experiments/aug_ablation/cfg_smoke*.json
```

- [ ] **Step 3: Pause the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 6
nvidia-smi --query-gpu=memory.used --format=csv,noheader
```
Expected: GPU near-idle.

- [ ] **Step 4: Smoke-test the `none` arm (tiny budget) — verifies the switch trains + loop state untouched**

```bash
.venv/bin/python -c "import json; c=json.load(open('experiments/aug_ablation/cfg_aug_none.json')); c['time_budget']=90; c['eval_every_steps']=10; c['checkpoint_out']='experiments/aug_ablation/smoke_model.pt'; json.dump(c, open('experiments/aug_ablation/cfg_smoke.json','w'), indent=2)"
echo "BEFORE: best_model.pt $(stat -c %Y best_model.pt 2>/dev/null || echo NONE) ; history.tsv $(wc -l < history.tsv)"
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/aug_ablation/cfg_smoke.json > experiments/aug_ablation/smoke.log 2>&1
echo "exit=$?"
echo "AFTER:  best_model.pt $(stat -c %Y best_model.pt 2>/dev/null || echo NONE) ; history.tsv $(wc -l < history.tsv)"
echo "=== curve rows ==="; cat experiments/aug_ablation/smoke_model.pt.curve.csv 2>&1 | head
grep -iE "Traceback|Error|disable" experiments/aug_ablation/smoke.log | head
```
Expected: trains to completion; `smoke_model.pt.curve.csv` has a header + ≥1 finite-AUC rows; **`best_model.pt` mtime + `history.tsv` UNCHANGED**; no traceback. If it errors (e.g., the gated z-compression/mixup paths broke a tensor shape), stop and fix before the long arms.

- [ ] **Step 5: Clean smoke artifacts + commit configs**

```bash
rm -f experiments/aug_ablation/cfg_smoke.json experiments/aug_ablation/smoke_model.pt* experiments/aug_ablation/smoke.log
git add .gitignore experiments/aug_ablation/cfg_aug_full.json experiments/aug_ablation/cfg_aug_none.json
git commit -m "chore(aug-ablation): full/none configs + gitignore artifacts"
```

---

## Task 3: Run both arms, measure, classify, restore

- [ ] **Step 1: Fresh init**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
test -f best_model.pt.prebkup_pseudolabel || cp best_model.pt best_model.pt.prebkup_pseudolabel
mv best_model.pt best_model.pt.HOLD_aug
test -f best_model.pt && echo "WARN present" || echo "fresh-init OK"
```

- [ ] **Step 2: Run the FULL arm (~2h, background) and confirm fresh init**

```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/aug_ablation/cfg_aug_full.json > experiments/aug_ablation/full.log 2>&1 &
echo "full PID $!"; sleep 40
grep -iE "Loading weights from best_model|Budget-Aware" experiments/aug_ablation/full.log | head
```
Expected: NO best_model load line (fresh); `Budget-Aware ... max_steps=...`. Wait for it to finish (poll `kill -0 <PID>` or watch `full_model.pt` appear). Use a background watcher: `while kill -0 <PID> 2>/dev/null; do sleep 600; done` with `run_in_background`.

- [ ] **Step 3: Run the NONE arm (~2h, background) after FULL completes**

```bash
PYTHONPATH=. .venv/bin/python -u scripts/training/train.py --config experiments/aug_ablation/cfg_aug_none.json > experiments/aug_ablation/none.log 2>&1 &
echo "none PID $!"
```
Wait for completion the same way. (Run sequentially, not concurrently — one GPU.)

- [ ] **Step 4: Post-hoc measure train + val pooled pixel AUC for BOTH arms**

```bash
PYTHONPATH=. PYTHONWARNINGS=ignore .venv/bin/python - <<'PYEOF' 2>&1 | grep -iE "ARM|train|val"
import sys, numpy as np, torch, random
sys.path.insert(0,'.'); sys.path.insert(0,'scripts/training'); sys.path.insert(0,'scripts')
from train import ExperimentConfig, load_shape_compatible_state
from vesuvius_autoresearch.core.model_wrappers import build_inference_model
from vesuvius_autoresearch.core.vesuvius_loader import VesuviusLabeledDataset
from measure_ink_auc import _volume_uri
from sklearn.metrics import roc_auc_score
dev=torch.device('cuda'); cfg=ExperimentConfig.load('config.json')
def pooled(ckpt, frag):
    chk=torch.load(ckpt,map_location='cpu',weights_only=False); s=chk['config']
    nl=s.get('num_layers',16); ps=s.get('patch_size',64)
    m=build_inference_model(architecture='resenc_unet',patch_size=ps,num_layers=nl,base_feat=64,num_blocks=16,num_heads=8,dropout=0.0,use_ridges=s.get('use_ridges',True),multi_task_heads=False).to(dev)
    load_shape_compatible_state(m,chk['model_state_dict'],'x'); m.eval()
    ds=VesuviusLabeledDataset(_volume_uri(frag), frag+'/inklabels.png', frag+'/mask.png', ps, nl+8, seed=7, cache_dir=cfg.cache_dir, use_ridges=s.get('use_ridges',True), ridge_sigma=2.0, use_lasagna=False, require_ink=False, jitter=False)
    idxs=list(range(len(ds))); random.seed(1); random.shuffle(idxs); P=[];I=[]
    with torch.no_grad():
        for i in idxs[:250]:
            x_raw,t,_=ds[i]; x=x_raw[:,4:4+nl].unsqueeze(0).to(dev)
            o=m(x); o=o[0] if isinstance(o,tuple) else o
            P.append(torch.sigmoid(o).squeeze().float().cpu().numpy().ravel()); I.append((t.numpy()>0.5).astype(int).ravel())
    P=np.concatenate(P); I=np.concatenate(I); return roc_auc_score(I,P)
for name,ck in [("FULL","experiments/aug_ablation/full_model.pt"),("NONE","experiments/aug_ablation/none_model.pt")]:
    tr=pooled(ck,'local_data/PHercParis2Fr47'); va=pooled(ck,'local_data/PHercParis2Fr143_Vregion')
    print(f"ARM {name}: train(Fr47) pixel AUC={tr:.4f}  val(V-region) pixel AUC={va:.4f}")
PYEOF
```
Record the four numbers.

- [ ] **Step 5: Classify per the decision table**

| Observation | Conclusion → next lever |
| --- | --- |
| none val > full val by ≥ +0.03 | augmentation was suppressing signal → de-augment / isolate the harmful family |
| none train ≫ full train but none val ≈ full val | pure generalization gap → regularization/data, or 64px limits generalization |
| none val ≈ full val (or worse) | augmentation is not the bottleneck → keep aug, look elsewhere |

- [ ] **Step 6: Update FINDINGS.md + memory**

Add a FINDINGS bullet with the four AUCs, the classification, and the implied lever (honest framing). Write memory `aug-ablation-result.md` (type project) + a `MEMORY.md` pointer; link `[[overfit-probe-result]]`, `[[scroll-augmentations-unified-library]]`.

```bash
git add FINDINGS.md
git commit -m "docs(findings): augmentation ablation result"
git push origin main
```

- [ ] **Step 7: Restore best_model.pt + the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mv best_model.pt.HOLD_aug best_model.pt
cmp -s best_model.pt best_model.pt.prebkup_pseudolabel && echo "model intact" || echo "DIFFERS — investigate"
rm -f .loop_paused
bash start.sh
sleep 20
ps -eo pid,etime,cmd | grep run_autoresearch_loop | grep -v grep
```
Expected: `best_model.pt` intact; loop running. The arms only wrote to `experiments/aug_ablation/*` (checkpoint_out), so loop state was never touched.

---

## Self-Review

**Spec coverage:**
- `disable_augmentation` master switch gating all 3 unconditional sites (apply_augmentations + z-compression + mixup/cutmix), default off → Task 1. ✓
- TDD: apply_augmentations identity when disabled → Task 1 Step 1/7. ✓
- cfg_aug_full / cfg_aug_none (fresh, ~2h, checkpoint_out, eval hook) → Task 2 Step 1. ✓
- Smoke gate (none arm trains + loop state untouched) → Task 2 Step 4. ✓
- Run both arms, post-hoc train+val pooled pixel AUC → Task 3 Steps 2-4. ✓
- Decision table classification → Task 3 Step 5. ✓
- Operational safety (loop paused, fresh init, best_model untouched, restore) → Tasks 2-3. ✓

**Placeholder scan:** None. `time_budget=7200`, `eval_every_steps=1000` are concrete; the eval cadence is the corrected value from the long-schedule lesson (real throughput ~13k steps/12h → ~1000 gives multiple curve points in a 2h arm).

**Type consistency:** `disable_augmentation` (bool, default False) is referenced identically via `getattr(config, "disable_augmentation", False)` at all three gated sites and set in both configs; the post-hoc `pooled(ckpt, frag)` helper matches the Probe-0 measurement pattern already validated this session; `checkpoint_out`/`eval_every_steps`/`eval_sample_patches` fields all exist from prior committed work.

**Loop-safety:** `disable_augmentation` defaults False → the gates are no-ops for the running loop; combined with `checkpoint_out`, the loop's training and persistence stay byte-identical until an experiment config opts in.
