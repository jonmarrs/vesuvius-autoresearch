# LeJEPA SSL-Init Experiment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether warm-starting `lejepa_unet` from the unused LeJEPA SSL pretrain beats the resenc baseline (per-patch ink AUC ~0.74 train / 0.61 val), via staged smoke → probe → full run → AUC comparison.

**Architecture:** Config-only experiment (no repo code change expected). Pause the loop, run `train.py` with a lejepa config in stages that each gate the next, measure AUC on `last_model.pt`, record honestly, restore the loop. If the smoke reveals a build/load bug, fix it as a separate pause-protected change.

**Tech Stack:** PyTorch, the existing `train.py` pipeline (`architecture=lejepa_unet`, `foundation_model_path`), `/tmp/auc_check.py`. Interpreter: `.venv` via `PYTHONPATH=. .venv/bin/python`.

**Context for the implementer:**
- This is a research experiment with no unit tests; each task's "verification" is the stage's gate. **If a gate fails, STOP and report — do not proceed to a longer stage.**
- The autoresearch loop runs continuously (a crontab watchdog restarts it). To pause it you MUST set the flag first: `touch .loop_paused`, then kill PIDs. Resume with `bash start.sh` (clears the flag).
- Process checks: do NOT trust `pgrep -f`/inline `grep` for the loop — they self-match the checking shell. Use `nvidia-smi` (GPU ~6 MiB = nothing training) and `ps -eo pid,cmd | grep -E "run_autoresearch_loop|training/train.py" | grep -v grep`.
- Resenc baseline to beat: AUC **0.74 train / 0.61 val**. `best_model.pt` (resenc) must remain untouched.
- LeJEPA checkpoint: `checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth`.

## File Structure

- `/tmp/cfg_lejepa.json` (create, ephemeral) — the experiment config.
- `.loop_paused` (create/remove) — the watchdog pause flag.
- `FINDINGS.md` (modify, Task 5) — record the result.
- No source files change unless the smoke reveals a build/load bug (handled inline if it arises).

---

## Task 1: Pause the loop and build the experiment config

- [ ] **Step 1: Pause the loop**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
touch .loop_paused
ps -eo pid,cmd | grep -E "run_autoresearch_loop|training/train.py" | grep -v grep | awk '{print $1}' | xargs -r kill -9
sleep 4
nvidia-smi --query-gpu=memory.used --format=csv,noheader   # expect ~6 MiB
ps -eo pid,cmd | grep -E "run_autoresearch_loop|training/train.py" | grep -v grep || echo "loop stopped"
```
Expected: GPU ~6 MiB, "loop stopped". (Killing the loop parent can orphan a `train.py` child holding the GPU — if GPU is still high, kill that PID too.)

- [ ] **Step 2: Build the lejepa config**

```bash
.venv/bin/python - <<'PYEOF'
import json
c = json.load(open("config.json"))
c["architecture"] = "lejepa_unet"
c["foundation_model_path"] = "checkpoints/lejepa_foundation_v1/lejepa_foundation_v1_final.pth"
c["loss_ink_bce"] = 0.5
c["loss_ink_dice"] = 0.5
c["loss_fiber_bce"] = 0.0
c["loss_st"] = 0.0
c["use_uamt"] = False
c["use_betti_loss"] = False
c["use_cldice"] = False
c["time_budget"] = 60   # smoke first; raised in later tasks
json.dump(c, open("/tmp/cfg_lejepa.json", "w"), indent=2)
print("arch", c["architecture"], "| foundation set:", bool(c["foundation_model_path"]),
      "| patch", c["patch_size"], "| num_layers", c["num_layers"])
PYEOF
```
Expected: `arch lejepa_unet | foundation set: True | patch 64 | num_layers 16`.

---

## Task 2: Smoke — build, load encoder, one fwd/bwd (GATE)

- [ ] **Step 1: Run the preflight smoke**

```bash
PYTHONPATH=. timeout 600 .venv/bin/python scripts/training/train.py --smoke --config /tmp/cfg_lejepa.json 2>&1 | tee /tmp/lejepa_smoke.log | grep -iE "Instantiating LeJEPA|Loading pretrained backbone|LeJEPA encoder|Loaded [0-9]+/|PREFLIGHT|Error|Traceback|NaN" | tail -15
```
Expected: lines showing `Instantiating LeJEPA…`, `Loading pretrained backbone…`, a `Loaded N/M compatible tensors` for the LeJEPA encoder with **N > 0**, and `PREFLIGHT OK`.

- [ ] **Step 2: GATE — confirm it built and loaded**

```bash
grep -q "PREFLIGHT OK" /tmp/lejepa_smoke.log && echo "BUILD+FWD/BWD OK" || echo "GATE FAILED: no PREFLIGHT OK"
grep -oE "Loaded [0-9]+/[0-9]+ compatible tensors.*LeJEPA|LeJEPA encoder" /tmp/lejepa_smoke.log | head -1
```
Expected: `BUILD+FWD/BWD OK` and a non-zero encoder load.
**If GATE FAILED:** inspect `/tmp/lejepa_smoke.log` for the error. Common cases: (a) encoder keys don't map (`Loaded 0/...`) → the foundation isn't actually initializing the backbone; (b) an fp64/dtype or shape error in the forward. If it's a small, well-understood train.py fix (e.g. input dtype cast), make it, add a brief note, re-run the smoke. Otherwise **STOP and report** — the experiment can't proceed.

---

## Task 3: Probe — does it learn? (~20 min, GATE)

- [ ] **Step 1: Raise the budget and run a short real training**

```bash
.venv/bin/python -c "import json;c=json.load(open('/tmp/cfg_lejepa.json'));c['time_budget']=1200;json.dump(c,open('/tmp/cfg_lejepa.json','w'),indent=2)"
PYTHONPATH=. nohup .venv/bin/python scripts/training/train.py --config /tmp/cfg_lejepa.json > /tmp/lejepa_probe.log 2>&1 &
echo "probe PID $!"
```

- [ ] **Step 2: Confirm it started and loaded the foundation (first ~60s)**

```bash
until grep -qE "Step 0000|Traceback|Error" /tmp/lejepa_probe.log 2>/dev/null; do sleep 5; done
grep -iE "Loading pretrained backbone|Loaded [0-9]+/|Step 0000|Traceback" /tmp/lejepa_probe.log | head -5
```
Expected: foundation loaded + `Step 0000 | Loss: …`. If `Traceback`, STOP and report.

- [ ] **Step 3: Wait for the probe to finish, then GATE on learning + finite metrics**

Use a background wait on the PID (replace `<PID>`), then inspect:
```bash
until ! kill -0 <PID> 2>/dev/null; do sleep 20; done; echo "probe done"
echo "=== loss trajectory (start vs end) ==="
grep -oE "Step [0-9]+ \| Loss: [0-9.]+" /tmp/lejepa_probe.log | sed -n '1p;$p'
echo "=== final metrics ==="
grep -iE "val_bpb \(Off|avg_skel_dist:|avg_centerline|Instability|NaN|RESULT" /tmp/lejepa_probe.log | grep -ivE "warn" | tail -5
```
**GATE (all must hold):** the end loss is clearly below the start loss; `val_bpb` is a real number (NOT `1.000000`); no `Instability`/`NaN`. If the gate fails (loss flat, val_bpb=1.0, or NaN), **STOP and report** — SSL-init isn't training cleanly here; don't spend the full hour.

---

## Task 4: Full run + AUC measurement

- [ ] **Step 1: Raise the budget and run the full training**

```bash
.venv/bin/python -c "import json;c=json.load(open('/tmp/cfg_lejepa.json'));c['time_budget']=3600;json.dump(c,open('/tmp/cfg_lejepa.json','w'),indent=2)"
PYTHONPATH=. nohup .venv/bin/python scripts/training/train.py --config /tmp/cfg_lejepa.json > /tmp/lejepa_full.log 2>&1 &
echo "full PID $!"
```

- [ ] **Step 2: Wait for completion**

```bash
until ! kill -0 <PID> 2>/dev/null; do sleep 30; done; echo "full run done"
grep -iE "val_bpb \(Off|avg_centerline|avg_skel_dist:|RESULT" /tmp/lejepa_full.log | grep -ivE "warn" | tail -4
```

- [ ] **Step 3: Confirm last_model.pt is the lejepa run and best_model is untouched**

```bash
.venv/bin/python -c "import torch;c=torch.load('last_model.pt',map_location='cpu',weights_only=False);print('last_model arch', c.get('config',{}).get('architecture'))"
.venv/bin/python -c "import torch;c=torch.load('best_model.pt',map_location='cpu',weights_only=False);print('best_model arch', c.get('config',{}).get('architecture'),'cl_dice',round(c.get('avg_centerline_dice',-1),4))"
```
Expected: `last_model arch lejepa_unet`; `best_model arch resenc_unet` (unchanged — the resenc baseline is safe).

- [ ] **Step 4: Measure per-patch AUC on Fr47/Fr143 (GPU; loop is paused so it's free)**

```bash
PYTHONPATH=. .venv/bin/python /tmp/auc_check.py last_model.pt cuda 2>&1 | grep -E "arch=|AUC|baseline" | tail -4
```
Expected two lines: `Fr47 (train) AUC: mean=…` and `Fr143 (val) AUC: mean=…`. Record both. (If `/tmp/auc_check.py` is missing, recreate it: it loads the checkpoint, builds the model via `build_inference_model` with the stored arch, samples `require_ink` patches per fragment, and computes per-patch `roc_auc_score(target.ravel(), sigmoid(model(x)).ravel())`.)

---

## Task 5: Record result, restore the loop

- [ ] **Step 1: Interpret against the success criterion**

- **Win:** Fr143 (val) AUC ≥ ~0.64 → SSL init helps; worth a longer run / a tracked lejepa path. Propose next step to the user.
- **Neutral/negative:** val AUC ≤ 0.61 → SSL-init-of-lejepa-at-64px doesn't beat the resenc CNN; revert to resenc and reconsider levers (multi-scroll is the approved next Tier-3 step).

- [ ] **Step 2: Append the result to FINDINGS.md** under "What we learned" (negative-results bullet) with the measured AUC and the one-line interpretation. Example shape:

```markdown
  - *LeJEPA SSL init (lejepa_unet warm-started from the foundation pretrain), trained 1 h at the 64 px window*: Fr47/Fr143 AUC <X>/<Y> vs the resenc baseline 0.74/0.61 — <helped / did not beat the CNN>.
```

- [ ] **Step 3: Restore the loop**

```bash
rm -f /tmp/cfg_lejepa.json
bash start.sh   # clears .loop_paused and restarts
sleep 10
grep -c ModuleNotFoundError autoresearch.out   # expect 0
tail -2 autoresearch.out
```
Expected: 0 import crashes; a cycle running.

- [ ] **Step 4: Commit the FINDINGS update**

```bash
git add FINDINGS.md
git commit -m "docs(findings): record LeJEPA SSL-init experiment result (AUC <X>/<Y>)"
git push origin main
```

---

## Verification (whole experiment)

- [ ] Smoke gate passed (build + non-zero encoder load + PREFLIGHT OK), or a documented train.py fix made it pass.
- [ ] Probe gate passed (loss down, finite val_bpb, no NaN) — or stopped early with a report.
- [ ] Full run completed; Fr47/Fr143 AUC measured and recorded in FINDINGS.md.
- [ ] `best_model.pt` still `resenc_unet` (baseline untouched).
- [ ] Loop restarted clean (0 import crashes), `.loop_paused` cleared.
