# GP-Winner Phase 3a — Our Data Through the Proven Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Run the proven winner TimeSformer recipe on OUR `PHercParis2Fr47` (train) → `PHercParis2Fr143` (held-out) with our labels, and read the held-out AUC to localize the gap to our data/labels vs our model/training-code.

**Architecture:** Convert our uint16-ZSTD fragment layers into 8-bit cv2-readable layers in the winner's `train_scrolls/` layout, then run an isolated copy of the proven Phase-2 trainer (fragment-list diff only) and evaluate held-out. Vendored code and the loop's `.venv` are untouched; `.venv-gp` is reused.

**Tech Stack:** the vendored `villa/ink-detection/` pipeline, `timesformer-pytorch`, `pytorch-lightning==2.0.9` (torch 2.12 cu130, `.venv-gp`), PIL (reads ZSTD uint16), OpenCV (the loader's reader), `repro/gp_winner/render_eval.py`.

**Spec:** `docs/superpowers/specs/2026-06-21-gp-winner-phase3-our-data-design.md`

## Global Constraints

- **Never edit vendored `villa/ink-detection/` files** (copy + edit) and **never install into / use the loop's `.venv`** — use `villa/ink-detection/.venv-gp`.
- **Never edit** `run_autoresearch_loop.py` / `scripts/training/train.py`.
- **Pause the loop before any GPU step** (`.loop_paused` + kill `run_autoresearch_loop` then `train.py --config`), restart with `bash start.sh` after.
- Converted data + checkpoints are **gitignored** (`villa/ink-detection/train_scrolls/`, `models/`, `outputs/` already covered).
- `$ROOT = /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch`. Run training/inference from CWD `$ROOT/villa/ink-detection/` (relative paths).
- Fragments — train `PHercParis2Fr47`, held-out `PHercParis2Fr143`. Layers 17–42. Normalization: **uint8 = uint16 // 256** (documented; per-layer min/max logged).
- This is a **diagnostic** experiment: the deliverable is an evidence-backed verdict, not a target AUC.

---

## Task 0: Preconditions

**Files:** none.

- [ ] **Step 1: Verify env, source fragments, labels, the proven trainer**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
.venv-gp/bin/python -c "import torch; print('cuda', torch.cuda.is_available())"
for F in PHercParis2Fr47 PHercParis2Fr143; do
  echo "$F: layers17-42=$(ls ../../local_data/$F/surface_volume/{17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42}.tif 2>/dev/null | wc -l)/26 ink=$(test -f ../../local_data/$F/inklabels.png && echo yes) mask=$(test -f ../../local_data/$F/mask.png && echo yes)"
done
ls ../../repro/gp_winner/train_subset.py
```
Expected: `cuda True`; both fragments `26/26 ink=yes mask=yes`; the Phase-2 trainer exists.

No commit.

---

## Task 1: Fragment → winner-format converter (TDD)

**Files:**
- Create: `repro/gp_winner/convert_fragment.py`
- Test: `tests/test_convert_fragment.py`

**Interfaces:**
- Produces: `convert_layer_u16_to_u8(arr: np.ndarray) -> np.ndarray` (uint16→uint8 via `//256`); `convert_fragment(frag_id: str, src_root: str, dst_root: str, z_start=17, z_end=43) -> dict` (writes `dst_root/<frag>/layers/{i:02}.tif` 8-bit + `<frag>_inklabels.png` + `<frag>_mask.png`; returns per-layer stats).

- [ ] **Step 1: Write the failing test (synthetic uint16 fragment fixture)**

```python
# tests/test_convert_fragment.py
import numpy as np
import cv2
from PIL import Image

from repro.gp_winner.convert_fragment import convert_layer_u16_to_u8, convert_fragment


def test_convert_layer_scales_u16_to_u8_by_256():
    arr = np.array([[0, 256, 65535]], dtype=np.uint16)
    out = convert_layer_u16_to_u8(arr)
    assert out.dtype == np.uint8
    assert out.tolist() == [[0, 1, 255]]


def test_convert_fragment_writes_cv2_readable_8bit_layers(tmp_path):
    src = tmp_path / "src" / "FragX"
    (src / "surface_volume").mkdir(parents=True)
    # 50 uint16 layers 00..49; only 17..42 should be converted
    for i in range(50):
        Image.fromarray(np.full((40, 32), i * 1000, dtype=np.uint16)).save(
            src / "surface_volume" / f"{i:02d}.tif"
        )
    Image.fromarray((np.eye(40, 32) * 255).astype(np.uint8)).save(src / "inklabels.png")
    Image.fromarray(np.full((40, 32), 255, dtype=np.uint8)).save(src / "mask.png")

    dst = tmp_path / "dst"
    stats = convert_fragment("FragX", str(tmp_path / "src"), str(dst), z_start=17, z_end=43)

    layers = sorted((dst / "FragX" / "layers").glob("*.tif"))
    assert len(layers) == 26  # 17..42
    back = cv2.imread(str(dst / "FragX" / "layers" / "17.tif"), 0)
    assert back is not None and back.dtype == np.uint8
    assert (dst / "FragX" / "FragX_inklabels.png").exists()
    assert (dst / "FragX" / "FragX_mask.png").exists()
    assert "17" in stats and "u8_max" in stats["17"]
```

- [ ] **Step 2: Run it — FAIL** (`ModuleNotFoundError: repro.gp_winner.convert_fragment`)

Run: `cd $ROOT && PYTHONPATH=. villa/ink-detection/.venv-gp/bin/python -m pytest tests/test_convert_fragment.py -v`

- [ ] **Step 3: Write `convert_fragment.py`**

```python
# repro/gp_winner/convert_fragment.py
"""Convert our uint16 ZSTD-compressed fragment layers into 8-bit, cv2-readable layers
in the winner's train_scrolls/<id>/ layout. uint16->uint8 via //256 (documented global
scale); the winner loader's clip(0,200) applies downstream. PIL reads the ZSTD source
(OpenCV cannot)."""
import argparse
import os
import shutil

import cv2
import numpy as np
from PIL import Image

Image.MAX_IMAGE_PIXELS = None


def convert_layer_u16_to_u8(arr):
    """uint16 -> uint8 by a global //256 scale (high byte)."""
    return (arr.astype(np.uint32) // 256).astype(np.uint8)


def convert_fragment(frag_id, src_root, dst_root, z_start=17, z_end=43):
    """Read src_root/<frag>/surface_volume/{i:02}.tif (uint16, PIL) for i in [z_start,z_end),
    write dst_root/<frag>/layers/{i:02}.tif as 8-bit cv2-readable, and copy the label+mask
    as <frag>_inklabels.png / <frag>_mask.png. Returns {str(i): {u16_max, u8_max, u8_mean}}."""
    src = os.path.join(src_root, frag_id)
    dst = os.path.join(dst_root, frag_id)
    os.makedirs(os.path.join(dst, "layers"), exist_ok=True)
    stats = {}
    for i in range(z_start, z_end):
        p = os.path.join(src, "surface_volume", f"{i:02d}.tif")
        a = np.array(Image.open(p))
        u8 = convert_layer_u16_to_u8(a)
        cv2.imwrite(os.path.join(dst, "layers", f"{i:02d}.tif"), u8)
        stats[str(i)] = {
            "u16_max": int(a.max()),
            "u8_max": int(u8.max()),
            "u8_mean": round(float(u8.mean()), 2),
        }
    shutil.copy(os.path.join(src, "inklabels.png"), os.path.join(dst, f"{frag_id}_inklabels.png"))
    shutil.copy(os.path.join(src, "mask.png"), os.path.join(dst, f"{frag_id}_mask.png"))
    return stats


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--frag", required=True)
    ap.add_argument("--src-root", default="local_data")
    ap.add_argument("--dst-root", default="villa/ink-detection/train_scrolls")
    args = ap.parse_args()
    stats = convert_fragment(args.frag, args.src_root, args.dst_root)
    lo = min(s["u8_mean"] for s in stats.values())
    hi = max(s["u8_mean"] for s in stats.values())
    print(f"{args.frag}: converted {len(stats)} layers; u8_mean range [{lo}, {hi}]")
    for i, s in stats.items():
        print(f"  layer {i}: {s}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run it — PASS (2 passed)**

Run: `cd $ROOT && PYTHONPATH=. villa/ink-detection/.venv-gp/bin/python -m pytest tests/test_convert_fragment.py -v`

- [ ] **Step 5: Commit**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/convert_fragment.py tests/test_convert_fragment.py
git commit --no-verify -m "feat(repro): uint16-ZSTD fragment -> 8-bit winner-format layer converter"
```

---

## Task 2: Convert both fragments

**Files:** writes `villa/ink-detection/train_scrolls/PHercParis2Fr47/` and `.../PHercParis2Fr143/` (gitignored).

- [ ] **Step 1: Convert Fr47 (train) and Fr143 (held-out)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
for F in PHercParis2Fr47 PHercParis2Fr143; do
  PYTHONPATH=. villa/ink-detection/.venv-gp/bin/python repro/gp_winner/convert_fragment.py --frag "$F" | tee "/tmp/convert_$F.log" | head -3
done
```
Expected: each prints `converted 26 layers; u8_mean range [...]` with non-trivial means (tens, not ~0 — confirms signal survives `//256`).

- [ ] **Step 2: Verify the winner loader can read the converted layout**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
for F in PHercParis2Fr47 PHercParis2Fr143; do
  N=$(ls train_scrolls/$F/layers/{17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42}.tif 2>/dev/null | wc -l)
  echo "$F: layers=$N/26 ink=$(test -f train_scrolls/$F/${F}_inklabels.png && echo yes) mask=$(test -f train_scrolls/$F/${F}_mask.png && echo yes)"
  .venv-gp/bin/python -c "import cv2,sys; a=cv2.imread('train_scrolls/$F/layers/17.tif',0); print('  cv2 read 17.tif:', None if a is None else (a.dtype, a.shape, int(a.max())))"
done
```
Expected: each `layers=26/26 ink=yes mask=yes`, and cv2 reads `17.tif` as `uint8` with `max>0` (not `None`).

- [ ] **Step 3: Verify label/mask shapes match the volume**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
for F in PHercParis2Fr47 PHercParis2Fr143; do
  .venv-gp/bin/python -c "
import cv2
L=cv2.imread('train_scrolls/$F/layers/17.tif',0)
ink=cv2.imread('train_scrolls/$F/${F}_inklabels.png',0)
m=cv2.imread('train_scrolls/$F/${F}_mask.png',0)
print('$F layer',L.shape,'ink',ink.shape,'mask',m.shape,'MATCH' if L.shape==ink.shape==m.shape else 'MISMATCH')
"
done
```
Expected: `MATCH` for both. (Mismatch → label/volume registration problem, itself a Phase-3 finding; stop and record.)

No commit (gitignored data).

---

## Task 3: `train_ours.py` (fragment-list diff of the proven trainer)

**Files:** Create `repro/gp_winner/train_ours.py`

- [ ] **Step 1: Copy the proven Phase-2 trainer**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
cp repro/gp_winner/train_subset.py repro/gp_winner/train_ours.py
```

- [ ] **Step 2: Verify the two anchor strings exist in the copy**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
grep -nE "def get_train_valid_dataset|^fragments=\['20230820203112'\]" repro/gp_winner/train_ours.py
```
Expected: two matches — the `get_train_valid_dataset` default list and the module-level `fragments=['20230820203112']`. (If the Phase-2 default list differs from below, replace whatever list is present with the two fragment ids.)

- [ ] **Step 3: Apply the two fragment-list edits** (exact string replacements in `repro/gp_winner/train_ours.py`)

1. Train+val dataset fragment list:
   - old: `def get_train_valid_dataset(\n    fragment_ids=[\n        "20231210121321",\n        "20230702185753",\n        "20230820203112",\n    ],\n):`
   - new: `def get_train_valid_dataset(\n    fragment_ids=[\n        "PHercParis2Fr47",\n        "PHercParis2Fr143",\n    ],\n):`
   (If ruff reformatted the Phase-2 list onto one line, match that exact form instead; the goal is the default list = `["PHercParis2Fr47", "PHercParis2Fr143"]`.)
2. Held-out fold:
   - old: `fragments=['20230820203112']`  (or `fragments = ["20230820203112"]` after formatting)
   - new: `fragments=['PHercParis2Fr143']`

- [ ] **Step 4: Confirm it parses and the edits landed**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
villa/ink-detection/.venv-gp/bin/python -c "import ast; ast.parse(open('repro/gp_winner/train_ours.py').read()); print('parses OK')"
grep -cE "PHercParis2Fr47|PHercParis2Fr143" repro/gp_winner/train_ours.py   # expect >=3
grep -cE "train_batch_size = 32|epochs = 12|CSVLogger|devices=1|max_epochs=CFG.epochs" repro/gp_winner/train_ours.py  # proven settings carried over
```
Expected: `parses OK`; fragment ids present; the Phase-2 settings (batch 32, epochs 12, single-GPU, CSVLogger) still present.

- [ ] **Step 5: Commit**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add repro/gp_winner/train_ours.py
git commit --no-verify -m "feat(repro): train_ours.py - proven recipe on our PHercParis2 Fr47->Fr143"
```

---

## Task 4: Train (GPU, loop paused)

**Files:** writes checkpoints under `villa/ink-detection/outputs/.../vesuvius-models/` (gitignored)

- [ ] **Step 1: Pause the loop, free the GPU**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 2
ps -eo pid,cmd | grep -E "train.py --config config_temp" | grep -v grep | awk '{print $1}' | xargs -r kill
sleep 5
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~0 MiB
```

- [ ] **Step 2: Run training (background; watch RAM during the data-read)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
mkdir -p ../../repro/gp_winner/runs
export WANDB_MODE=disabled
.venv-gp/bin/python ../../repro/gp_winner/train_ours.py > ../../repro/gp_winner/runs/train_ours.log 2>&1 &
echo "train PID $!"
```
During the data-read, watch `free -g` (avail should stay >0; 2 fragments fit the 31 GB box). If it is OOM-killed (silent death during "reading", no traceback), the held-out fragment alone may be too large — record it and, as a fallback, swap train/holdout so the smaller Fr47 is held out, or downsample. (Fr47 ≈ 8181×6330, Fr143 ≈ 14830×9506.)

- [ ] **Step 3: Confirm learning + checkpoints**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CSV=$(find villa/ink-detection/models -name metrics.csv 2>/dev/null | tail -1)
.venv/bin/python -c "
import csv
rows=list(csv.DictReader(open('$CSV')))
seen={}
for r in rows:
    e=r.get('epoch')
    for c in ('train/total_loss_epoch','val/total_loss_epoch'):
        if r.get(c): seen.setdefault(e,{})[c]=r[c]
for e in sorted(seen,key=lambda x:int(x)):
    d=seen[e]; print('epoch',e,'train',round(float(d.get('train/total_loss_epoch',0)),4),'val',round(float(d.get('val/total_loss_epoch',0)),4))
"
ls villa/ink-detection/outputs/vesuvius/pretraining_all/vesuvius-models/*.ckpt 2>/dev/null | wc -l
```
Expected: per-epoch loss rows; one `.ckpt` per epoch (up to 12). Train loss should fall; note whether val falls (the held-out signal).

Deliverable: trained per-epoch checkpoints on our data.

---

## Task 5: Held-out eval, verdict, record, restart loop

**Files:** Modify `FINDINGS.md`; create report image under `reports/gp_winner_repro/`

- [ ] **Step 1: Held-out inference on Fr143 with the latest checkpoint**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection
CKPT=$(find outputs -name "timesformer_wild16_PHercParis2Fr143_fr*epoch*.ckpt" -printf '%T@ %p\n' | sort -n | tail -1 | cut -d' ' -f2-)
echo "checkpoint: $CKPT"
export WANDB_MODE=disabled
.venv-gp/bin/python inference_timesformer.py \
  --model_path "$CKPT" \
  --segment_path "$PWD/train_scrolls" \
  --segment_id PHercParis2Fr143 \
  --out_path "$PWD/../../repro/gp_winner/runs/phase3" \
  > ../../repro/gp_winner/runs/infer_phase3.log 2>&1
ls -la ../../repro/gp_winner/runs/phase3/
```
Expected: a `PHercParis2Fr143_prediction_*.png`. (If the `ModelCheckpoint` filename uses a different id token, adjust the glob — list `outputs/**/*.ckpt` and pick the newest.)

- [ ] **Step 2: Held-out pixel-AUC + thumbnail**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
mkdir -p reports/gp_winner_repro
PRED=$(ls repro/gp_winner/runs/phase3/*PHercParis2Fr143*prediction*.png 2>/dev/null | head -1)
.venv/bin/python repro/gp_winner/render_eval.py \
  --pred "$PRED" --out "reports/gp_winner_repro/phase3_heldout_Fr143_thumb.png" --scale 8 \
  --label "villa/ink-detection/train_scrolls/PHercParis2Fr143/PHercParis2Fr143_inklabels.png"
```
Expected: prints `pixel_auc=<x>` and writes the thumbnail.

- [ ] **Step 3: Judge the verdict** (the diagnostic fork)

Interpret the held-out AUC against the references:
- **AUC ≳0.75 (≫ our loop's 0.56):** our **data/labels are fine** — a known-good recipe learns them. The gap is our **model/training code** (`resenc_unet`, our `train.py`). Next: fix our trainer (separate spec).
- **AUC ~0.5–0.56 (≈ chance / our loop):** our **data/labels are the problem**. Next: **Phase 3b** sub-isolates label quality/alignment vs volume normalization (separate spec).
- Also weigh the per-epoch loss trend and the thumbnail (legible structure vs noise).

- [ ] **Step 4: Record + commit**

Add a `FINDINGS.md` bullet (converted-data stats, per-epoch trend, held-out AUC vs 0.5/0.56/0.905, verdict + which branch). Write memory file `gp-winner-phase3-result.md` (type project) linking `[[gp-winner-phase2-result]]` and `[[model-barely-discriminates-ink]]`. Add the thumbnail under `reports/gp_winner_repro/`.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
git add FINDINGS.md reports/gp_winner_repro/phase3_heldout_Fr143_thumb.png
git commit --no-verify -m "docs(findings): GP-winner Phase 3a verdict - proven recipe on our data"
```

- [ ] **Step 5: Restart the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
rm -f .loop_paused
bash start.sh
sleep 3
ps -eo pid,cmd | grep -E "run_autoresearch_loop" | grep -v grep | head -1 || echo "WARN: loop not running"
```

Deliverable: an evidence-backed verdict (data/labels vs model/code) with the held-out thumbnail; the loop running again.

---

## Self-Review

**Spec coverage:**
- Our Fr47→Fr143 split, winner recipe held constant → Task 3 + Task 4. ✓
- Critical data conversion (uint16 ZSTD → 8-bit cv2-readable, `//256`, logged) → Task 1 (TDD) + Task 2. ✓
- Layers 17–42, label/mask in winner naming → Task 1 (`convert_fragment`) + Task 2 verify. ✓
- Reuse `.venv-gp`, vendored untouched, loop `.venv` untouched → Global Constraints + copy-based Tasks 1/3. ✓
- Held-out eval via `inference_timesformer.py` + `render_eval.py` → Task 5 Steps 1–2. ✓
- Diagnostic verdict fork (data/labels vs model/code; Phase 3b gating) → Task 5 Step 3. ✓
- Record FINDINGS + memory + report image → Task 5 Step 4. ✓
- Loop paused for GPU, restarted → Task 4 Step 1 + Task 5 Step 5. ✓
- Normalization-as-variable + label/volume shape check (risks) → Task 1 stats, Task 2 Step 3. ✓

**Placeholder scan:** none — converter code is complete with a passing test; every command is concrete; the only judgment step (verdict) is the experiment's purpose and is spelled out as branch thresholds.

**Type/name consistency:** `convert_layer_u16_to_u8` / `convert_fragment(frag_id, src_root, dst_root, z_start, z_end)` match between test and implementation and the Task-2 CLI; fragment ids (`PHercParis2Fr47`, `PHercParis2Fr143`), paths (`train_scrolls/<F>/layers/NN.tif`, `<F>_inklabels.png`, `<F>_mask.png`, `repro/gp_winner/runs/phase3/`, `reports/gp_winner_repro/`), the checkpoint glob (`timesformer_wild16_PHercParis2Fr143_fr*epoch*.ckpt`, matching the `ModelCheckpoint(filename=f'timesformer_wild16_{fid}_fr'+'{epoch}')` carried from Phase 2 with `fid=PHercParis2Fr143`), and `render_eval.py --pred/--out/--label` are consistent across tasks.

**Known risks:** (1) `//256` could leave converted data outside the loader's `clip(0,200)` band — Task 2 Step 1 surfaces this via logged means (validated ~55–97 on Fr47 layer 17). (2) the held-out Fr143 is large; RAM during the read is the main failure mode — Task 4 Step 2 has a swap-fold fallback. (3) checkpoint filename token must match the held-out id — Task 5 Step 1 notes the glob fallback.
