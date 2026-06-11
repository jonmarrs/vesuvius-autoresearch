# Repo-as-Artifact Polish — Design

**Date:** 2026-06-11
**Status:** approved (pending spec review)
**Goal:** Package `vesuvius-autoresearch` as a compelling, *honest*, documented open-source artifact for the June Progress Prize — leading with concrete tools, backed by a candid record of what works, what doesn't, and what we learned. Second Tier-1 deliverable of the June plan.

## Context

The repo has solid quick-start docs and (now) a scroll-augmentation library, but two problems weaken it as a prize artifact:

1. **No honest results/findings document.** This session produced genuinely distinctive work — the discovery that ink-detection val metrics are artifact-saturated, a topology-aware evaluation fix, and rigorous negative results — none of it captured in a presentable form. That rigor is our strongest differentiator; most "autoresearch" packagers don't have it.
2. **Stale, overclaiming docs.** `METHOD.md` and `docs/RESEARCH_PAPER.md` contradict current reality: the paper claims best `val_bpb 0.4145` (now 0.2627, and that drop was a validation-methodology fix, not a gain), "best checkpoint is lejepa_unet" (it's the pinned `resenc_unet`), "four scroll-specific augmentations" (there are nine), cites closed villa PRs (#915/#916/#922/#923) as live, and quotes inflated GPU speedups ("430×/226×") superseded by the honest PR #1033 numbers (14–94×). `METHOD.md` still calls `val_bpb` "the primary selection signal" (selection is now topology-first) and links a non-existent `SUBMISSION.md`. Contradictory docs erode credibility.

All work here is pure documentation — fully parallel-safe while the loop runs.

## Current honest numbers (source of truth for the docs)

- Production model: `resenc_unet`, `val_bpb` 0.2627, `centerline_dice` ~0.30 (at the topology-optimal threshold; up from the 0.198 baseline this session), `skel_dist` ~19.8 (prize gate 2.0 — far off).
- Per-patch ink-vs-background AUC: ~0.70 train (Fr47) / ~0.60 val (Fr143) — **re-measure current best_model for the FINDINGS table**.
- GPU fibers: eigensolver float64 parity 3.1e-10; dense speedups 14–94× (64³–256³); tiled 512³ ~3–5 s at ~1 GB VRAM.
- Negatives: clDice late-fine-tune → cl_dice 0.073–0.077 (degrades); TimeSformer@64px → AUC 0.487 train / 0.557 val.
- Live wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

## Design — four documents

### 1. `FINDINGS.md` (new — centerpiece, balanced framing)

Sections, in order:
- **What this is** — one paragraph: an autonomous, evidence-gated ink-detection research loop on a single RTX 4090.
- **Deliverables (tools)** — lead with the concrete: the autoresearch loop + bandit; the 9-family scroll-augmentation library ([villa #201](https://github.com/ScrollPrize/villa/issues/201), → `docs/SCROLL_AUGMENTATIONS.md`); GPU fiber/ridge detection (closed-form eigensolver, 14–94×, tiled 512³@1GB); wandb experiment tracking; the topology-aware evaluation toolkit. Each with a one-line "what / where".
- **Honest current results** — a small table: val_bpb, centerline_dice (note: at topology-optimal threshold), skel_dist (note gate 2.0), per-patch AUC train/val. Stated plainly as mediocre-but-improving; no spin.
- **What we learned** (the rigor section): (a) val metrics are artifact-saturated — a predict-constant model scores dice 0.75 on ~60%-ink patches; (b) topology metrics must be read at a topology-optimal threshold (cl_dice 0.073→0.198 on the *same* model, just by thresholding); (c) negatives — clDice late-fine-tune degrades cl_dice, TimeSformer@64px hits AUC ~0.49 because the 0.5 mm (~64 px) prize window can't host its 256 px context; (d) bugs found via rigor — Frangi fiber target silently trained on zeros, 5 of 9 sampled augmentations were no-ops.
- **Reproduce** — pointer to README quick-start + the live wandb dashboard link.

### 2. `README.md` honesty pass

- Fix the "Key Features" overclaims: reframe "Grand Prize Architectures" (TimeSformer/ResNet3D/I3D are *available* in the zoo, but the 64 px prize window favors the CNN — TimeSformer@64px underperforms); reframe "Topological Metrics" to note they require topology-optimal thresholding to be meaningful.
- Add a top-of-README link to `FINDINGS.md` and the live **wandb dashboard**.

### 3. `METHOD.md` refresh

- "Evaluation metrics": selection is **topology-first** (centerline_dice primary, val_bpb as a noise-tolerant guard), and topology metrics are evaluated at the topology-optimal threshold, not the Dice threshold.
- Replace the stale `SUBMISSION.md` → Results reference with `FINDINGS.md`.
- Keep the (good) "Honest scope" framing; update its numbers.

### 4. `docs/RESEARCH_PAPER.md` refresh

- Abstract: drop "0.4145"; state current honest numbers and make the **artifact-saturation finding** the headline insight; keep the cross-scroll-generalization-is-unproven honesty.
- Methodology: best checkpoint is `resenc_unet` (not lejepa); **nine** scroll augmentations (not four); note the no-op-augmentations fix.
- Results: remove the inflated CuPy speedups and closed-PR / deprecated-`vesuvius-c` claims; replace with the honest PR #1033 fibers numbers and a pointer to `FINDINGS.md`.
- Keep it labeled a living/in-progress note.

## Verification

- Re-measure current best_model AUC (Fr47/Fr143) and use those exact numbers in `FINDINGS.md`.
- Every number in the four docs matches `best_model.pt` / measured values / committed evidence (no 0.4145, no lejepa-as-best, no closed-PR-as-live, no 430× speedups).
- All internal links resolve (`FINDINGS.md`, `docs/SCROLL_AUGMENTATIONS.md`, wandb URL, reports/).
- Diff limited to: `FINDINGS.md` (new), `README.md`, `METHOD.md`, `docs/RESEARCH_PAPER.md`.

## Out of scope

- LAB_NOTEBOOK.md (a chronological log; leave as-is).
- Any code change or new measurement beyond the one AUC re-measurement.
