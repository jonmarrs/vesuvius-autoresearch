# Repo-as-Artifact Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the repo a compelling, honest, documented prize artifact: add a `FINDINGS.md` centerpiece and refresh `README.md`, `METHOD.md`, and `docs/RESEARCH_PAPER.md` so every claim matches measured reality.

**Architecture:** Pure documentation. One new file (`FINDINGS.md`) plus honesty edits to three existing docs. One measurement task up front provides the current AUC numbers. No code, no loop interaction — parallel-safe while the loop runs.

**Tech Stack:** Markdown; `.venv` Python for the AUC re-measurement; `git`.

**Context for the implementer:**
- Source-of-truth numbers live in the spec (`docs/superpowers/specs/2026-06-11-repo-artifact-polish-design.md`) and are restated here. Use these exact figures.
- The autoresearch loop runs `train.py` subprocesses and writes `config.json` / loop artifacts at cycle boundaries (~15–60 min). Commit doc files mid-cycle, or stage only your files, to avoid the pre-commit stash conflicting with loop-written files.
- The repo's git user is "Jon Marrs"; a parallel agent also commits to `main` — `git fetch` before pushing.

## Source-of-truth numbers

- Production model: `resenc_unet`; `val_bpb` **0.2627**; `centerline_dice` **~0.30** (at the topology-optimal threshold; up from the 0.198 session baseline); `skel_dist` **~19.8** (prize gate 2.0).
- Per-patch ink AUC: **measured in Task 1** (prior checkpoint was ~0.70 train / ~0.60 val).
- GPU fibers (PR #1033): eigensolver float64 parity **3.1e-10**; dense speedups **14–94×** (64³–256³); tiled **512³ ~3–5 s at ~1 GB VRAM**.
- Negatives: clDice late-fine-tune → cl_dice **0.073–0.077** (degrades); TimeSformer@64px → AUC **0.487 train / 0.557 val**.
- Live wandb: `https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch`

## File Structure

- `FINDINGS.md` (create) — repo-root honest results + methodology + negatives.
- `README.md` (modify) — "Key Features" honesty + FINDINGS/wandb links.
- `METHOD.md` (modify) — topology-first selection; fix stale `SUBMISSION.md` ref.
- `docs/RESEARCH_PAPER.md` (modify) — honest abstract/methodology/results.

---

## Task 1: Re-measure current best_model AUC

**Files:** none (produces numbers for Task 2). Uses the existing `/tmp/auc_check.py` if present, else the inline command below.

- [ ] **Step 1: Run the AUC check on the current best_model (CPU, so it doesn't contend with the loop's GPU)**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
# If /tmp/auc_check.py is absent, recreate it from scripts/diagnose_topology_postproc.py's loader pattern:
#   load best_model.pt -> build_inference_model(arch from ckpt) -> VesuviusLabeledDataset(Fr47 / Fr143, require_ink=True)
#   -> per patch: roc_auc_score(target.ravel(), sigmoid(model(x)).ravel()); print mean per fragment.
CUDA_VISIBLE_DEVICES="" PYTHONPATH=. .venv/bin/python /tmp/auc_check.py best_model.pt cpu
```
Expected: two lines, `Fr47 (train) AUC: mean=0.NN` and `Fr143 (val) AUC: mean=0.NN`. Record both numbers; they fill the FINDINGS results table. (If the model fails to load, stop and report — do not invent numbers.)

- [ ] **Step 2: No commit** (measurement only).

---

## Task 2: Write `FINDINGS.md` (centerpiece)

**Files:**
- Create: `FINDINGS.md`

- [ ] **Step 1: Write the file with the content below**, substituting the Task 1 AUC numbers into the results table (`<AUC_TRAIN>` / `<AUC_VAL>`):

```markdown
# Findings

An autonomous, evidence-gated ink-detection research loop for the Vesuvius
Challenge, running continuously on a single NVIDIA RTX 4090. This document is the
honest record: what the tools do, how the model actually performs, and what the
search has taught us — including the negative results.

## Deliverables (tools)

- **Autoresearch loop** (`run_autoresearch_loop.py`) — a bandit samples
  architecture / loss / augmentation / hyperparameter "families", trains each
  candidate under a fixed wall-clock budget on a single GPU, evaluates on a
  held-out fragment, and promotes only topology-improving configurations.
- **Scroll-specific augmentation library** (`scroll_augmentations.py`) — nine
  GPU-native augmentations modeling scroll-CT artifacts; addresses
  [villa #201](https://github.com/ScrollPrize/villa/issues/201). See
  [docs/SCROLL_AUGMENTATIONS.md](docs/SCROLL_AUGMENTATIONS.md) and the
  [before/after demo](reports/augmentation_demos/all_families.png).
- **GPU fiber/ridge detection** — a closed-form symmetric-3×3 eigensolver that
  avoids the cuSolver `eigvalsh` failure on large Hessian batches, with tiled
  execution: dense 14–94× over NumPy (64³–256³), 512³ tiled in ~3–5 s at ~1 GB
  VRAM, float64 eigenvalue parity 3.1e-10. See
  [reports/fibers_gpu_validation_2026-06.md](reports/fibers_gpu_validation_2026-06.md).
- **Experiment tracking** — opt-in Weights & Biases logging (parameter/gradient
  histograms, per-cycle metrics, prediction images), mirroring villa's setup.
  Live: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch
- **Topology-aware evaluation toolkit** — selects the binarization threshold that
  maximizes centerline overlap and reports the prize topology metrics there
  (see "What we learned").

## Honest current results

Production model: `resenc_unet`, evaluated on held-out `PHercParis2Fr143`
(disjoint from the `PHercParis2Fr47` training fragment).

| Metric | Value | Note |
| --- | --- | --- |
| `val_bpb` | 0.2627 | 1 − Dice at the Dice-optimal threshold |
| `centerline_dice` | ~0.30 | at the topology-optimal threshold; up from 0.198 |
| `skel_dist` | ~19.8 | prize gate is 2.0 — large remaining headroom |
| ink AUC (train Fr47) | <AUC_TRAIN> | per-patch ink-vs-background discrimination |
| ink AUC (val Fr143) | <AUC_VAL> | 0.5 = chance |

This is a mediocre-but-improving detector, stated plainly. The contribution is
the reproducible, evidence-gated search process and the tooling around it — not
a state-of-the-art model.

## What we learned

- **Validation metrics are artifact-saturated.** On ink-containing patches
  (~60% ink), a near-constant predictor scores Dice ≈ 0.75 at a low threshold.
  So `val_bpb` / Dice alone do not prove a model localizes ink; per-patch AUC
  exposed that the production model sits at ~0.70 train / ~0.60 val.
- **Topology metrics depend on the threshold.** Evaluating `centerline_dice` /
  `skel_dist` at the Dice-optimal threshold understates topology by ~2×; at the
  topology-optimal threshold the *same* model reports `centerline_dice`
  0.073 → 0.198. The loop now selects and reports at the topology-optimal point.
- **Negative results (kept honest):**
  - *clDice as a late fine-tune* of the converged model degrades centerline
    overlap (cl_dice 0.073–0.077), rather than improving it — the soft skeleton
    is a poor proxy on a diffuse, under-confident model.
  - *The GP-winning TimeSformer at the 64 px prize window* reaches only AUC
    ~0.49 train / ~0.56 val. Its strength needs the 256 px context that the
    Challenge's 0.5 mm (~64 px) hallucination window forbids; at 64 px a CNN
    that emits full-resolution per-pixel output is the better fit.
- **Bugs surfaced by the rigor:** the Frangi fiber target silently trained on
  zeros (a backend bug in the upstream `tools.py`), and 5 of 9 sampled
  augmentation families were silent no-ops until the augmentation code was
  unified into one library. Both are fixed.

## Reproduce

See the [README](README.md) quick start to install and run a cycle, and the live
[wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch) for
streaming metrics.
```

- [ ] **Step 2: Verify links resolve**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
for p in docs/SCROLL_AUGMENTATIONS.md reports/augmentation_demos/all_families.png reports/fibers_gpu_validation_2026-06.md README.md; do test -e "$p" && echo "OK $p" || echo "MISSING $p"; done
grep -c "<AUC_TRAIN>\|<AUC_VAL>" FINDINGS.md   # expect 0 (placeholders replaced)
```
Expected: all `OK`; placeholder count 0.

- [ ] **Step 3: Commit**

```bash
git add FINDINGS.md
git commit -m "docs: add FINDINGS.md (honest results, methodology, negative results)"
```

---

## Task 3: README honesty pass

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Fix the two overclaiming Key Features bullets**

Replace the `Grand Prize Architectures` bullet with:

```markdown
- **Architecture zoo:** ResEnc-UNet (production), plus TimeSformer, ResNet3D-101, and Inception-I3D options. Note: at the prize's ~64 px window a full-resolution CNN outperforms the patch-based transformers (see [FINDINGS.md](FINDINGS.md)).
```

Replace the `Topological Metrics` bullet with:

```markdown
- **Topology-aware evaluation:** `centerline_dice` and `skeleton_distance_length`, evaluated at the topology-optimal binarization threshold (the Dice-optimal threshold understates topology ~2×).
```

- [ ] **Step 2: Add FINDINGS + wandb links near the top of the README**

Immediately after the teaser line (`*The first autonomous research swarm for the Vesuvius Challenge.*`), add:

```markdown
> **Honest results, methodology, and negative results:** see [FINDINGS.md](FINDINGS.md).
> **Live experiment tracking:** [wandb dashboard](https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch).
```

- [ ] **Step 3: Verify**

```bash
grep -c "FINDINGS.md" README.md            # expect >= 2
grep -ci "Grand Prize Architectures" README.md   # expect 0 (overclaim removed)
```
Expected: `FINDINGS.md` referenced; old overclaim gone.

- [ ] **Step 4: Commit**

```bash
git add README.md
git commit -m "docs(readme): honesty pass on Key Features; link FINDINGS + wandb"
```

---

## Task 4: METHOD.md refresh

**Files:**
- Modify: `METHOD.md`

- [ ] **Step 1: Update the "Evaluation metrics" section** — replace the `val_bpb ... the primary selection signal` framing with topology-first:

```markdown
## Evaluation metrics

- **`centerline_dice`** (primary selection signal) and **`skeleton_distance_length`** —
  topological scores that reward correct fiber/stroke structure, not just pixel
  overlap. Evaluated at the topology-optimal binarization threshold (the
  Dice-optimal threshold understates them ~2×). Integrated from the Villa metrics
  suite (see `CREDITS.md`).
- **`val_bpb`** — bits-per-byte on held-out cross-fragment validation (lower is
  better); a guard rail with a noise tolerance, not the sole objective. A lower
  `val_bpb` only counts as an improvement if topology does not regress.
```

- [ ] **Step 2: Fix the stale `SUBMISSION.md` reference** in the "Honest scope" section — change `see \`SUBMISSION.md\` → Results` to `see \`FINDINGS.md\``, and update the numbers sentence to:

```markdown
This is research tooling. The loop's selection mechanism works as intended
(topology-first keep-if-better), and `centerline_dice` has climbed from 0.198 to
~0.30 this cycle window, but absolute performance remains mediocre and
`skeleton_distance_length` shows large remaining headroom (see `FINDINGS.md`).
The contribution offered here is the reproducible, evidence-gated search process,
not a state-of-the-art detector.
```

- [ ] **Step 3: Verify**

```bash
grep -c "SUBMISSION.md" METHOD.md     # expect 0
grep -c "FINDINGS.md" METHOD.md       # expect >= 1
```
Expected: no `SUBMISSION.md`; `FINDINGS.md` present.

- [ ] **Step 4: Commit**

```bash
git add METHOD.md
git commit -m "docs(method): topology-first selection; replace stale SUBMISSION.md ref"
```

---

## Task 5: RESEARCH_PAPER.md refresh

**Files:**
- Modify: `docs/RESEARCH_PAPER.md`

- [ ] **Step 1: Rewrite the Abstract's results sentence.** Replace the sentence beginning "The current best `val_bpb` ... is **0.4145**; ..." with:

```markdown
On held-out PHerc Paris 2 Fragment 143 the production `resenc_unet` reports `val_bpb` ≈ 0.2627 and `centerline_dice` ≈ 0.30 (at the topology-optimal threshold). The headline methodological finding is that these validation metrics are *artifact-saturated* — a near-constant predictor scores Dice ≈ 0.75 on ink-rich patches — so per-patch discrimination AUC (≈ 0.70 train / 0.60 val) is the honest signal. Cross-scroll generalization to Scroll 2 / Scroll 3 is unproven and is the active research target, not a claimed result.
```

- [ ] **Step 2: Fix the Methodology architecture + augmentation claims.** In section II.A, change "The current best checkpoint is `lejepa_unet` ..." to "The current production checkpoint is `resenc_unet` (pinned for fine-tuning); a LeJEPA self-supervised pretrain (`checkpoints/lejepa_foundation_v1/`) is available as an initializer." In section II.B, change "four scroll-specific augmentation probabilities (decohesion/squeeze/z-dropout/intensity-drift)" to "nine scroll-specific augmentation probabilities (decohesion, warping, squeeze, z-dropout, intensity-drift, sheet-compression, thick-slice, rician-noise, blank-rectangles); a 2026-06 fix unified these into one library after finding five were silent no-ops".

- [ ] **Step 3: Replace the stale Results (section IV).** Replace section IV.A's `val_bpb ≈ 0.4145` paragraph and IV.B's inflated speedups with:

```markdown
### A. Model performance
The production `resenc_unet` reports `val_bpb` ≈ 0.2627 and `centerline_dice` ≈
0.30 (topology-optimal threshold) on held-out Fragment 143. Per-patch ink-vs-
background AUC is ≈ 0.70 (train) / 0.60 (val). See `FINDINGS.md` for the full
honest results and the artifact-saturation analysis.

### B. GPU fiber/ridge detection
A closed-form symmetric-3×3 eigensolver replaces the cuSolver `eigvalsh` path
that fails on large Hessian batches, enabling 14–94× dense speedups over NumPy
(64³–256³) and tiled 512³ execution in ~3–5 s at ~1 GB VRAM (float64 eigenvalue
parity 3.1e-10).
```

Delete the bullet referencing closed villa PRs #915/#916/#922/#923 and the
deprecated `vesuvius-c` bindings as if they were live; if a sentence is needed,
state they were proposed and closed, and the maintained version lives in this
repo.

- [ ] **Step 4: Verify no stale figures remain**

```bash
grep -c "0.4145\|lejepa_unet.*best\|430×\|430x" docs/RESEARCH_PAPER.md   # expect 0
grep -c "0.2627\|resenc_unet\|artifact" docs/RESEARCH_PAPER.md           # expect >= 2
```
Expected: stale figures gone; current figures present.

- [ ] **Step 5: Commit**

```bash
git add docs/RESEARCH_PAPER.md
git commit -m "docs(paper): refresh to current honest numbers; drop stale 0.4145/lejepa/closed-PR claims"
```

---

## Verification (whole feature)

- [ ] `grep -rn "0.4145\|430×\|430x" README.md METHOD.md docs/RESEARCH_PAPER.md FINDINGS.md` → no matches.
- [ ] `grep -rn "SUBMISSION.md" METHOD.md` → no matches.
- [ ] FINDINGS.md results table has real AUC numbers (no `<AUC_*>` placeholders).
- [ ] All internal links resolve: `FINDINGS.md`, `docs/SCROLL_AUGMENTATIONS.md`, `reports/augmentation_demos/all_families.png`, `reports/fibers_gpu_validation_2026-06.md`, wandb URL.
- [ ] Diff limited to: `FINDINGS.md`, `README.md`, `METHOD.md`, `docs/RESEARCH_PAPER.md`.
- [ ] `git fetch origin && git push origin main`.
