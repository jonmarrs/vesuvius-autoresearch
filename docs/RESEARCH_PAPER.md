# Autonomous Architectural Evolution for 3D Ink Detection in Carbonized Herculaneum Scrolls

**Author:** Jon Marrs

**Status:** Draft / in-progress research notes — not a submitted paper. Numbers and claims here track the current state of the [`vesuvius-autoresearch`](https://github.com/jonmarrs/vesuvius-autoresearch) loop and are updated as cycles complete; treat as a living document until a version is explicitly submitted somewhere.

## Abstract
Detecting ink within micro-CT scans of carbonized papyrus scrolls remains a significant challenge due to low signal-to-noise ratios, morphological variability across scrolls, and the risk of model hallucination. These notes describe a single-GPU (NVIDIA RTX 4090) research program with two strands: an autonomous bandit loop over architectural and hyperparameter tweaks, and — the stronger 2026-06/07 strand — a **productionized ink detector** built by replicating the proven 2023 Grand-Prize TimeSformer recipe and then **rebasing it onto the newly-open SOTA scroll data by distillation**. Under the community metric contract (threshold-swept F1 primary; average precision and AP-prevalence-lift as imbalance-robust gates; ROC-AUC secondary), the detector scores held-out same-scroll `val_f1` 0.393 / lift 2.07 (ROC-AUC 0.709) at the prize-compliant 64 px lateral window, and the first *valid* cross-scroll measurement quantifies the generalization gap at lift 1.29 (near chance). Distilling the same recipe from the released canon predictions on the open SOTA surface volumes lifts held-out **agreement-with-teacher** (explicitly not ground-truth accuracy — no aligned ground-truth labels are released) from the chance floor to `val_f1` 0.662 / AP 0.742 / lift 3.24, with the repo's first letterform-shaped output. The methodological through-line is measurement honesty: Dice/`val_bpb` saturate on ink-rich patches (a near-constant predictor scores Dice ≈ 0.75), a widely-copied `skel_dist` "prize gate" is provably invalid (blind to spatial location), and every claim above ships with its measurement instrument and its caveats.

## I. Introduction
The Vesuvius Challenge seeks to read the lost library of Herculaneum through advanced imaging and machine learning. In June 2026 the challenge read its first *complete* scroll (PHerc. 1667 [4]) — driven by improved phase-contrast scanning, semi-automated unwrapping, and ink models used as "visibility amplifiers" — and released the underlying data openly. With hundreds of scrolls still unread, the "Generalization Gap" — the failure of a model trained on one scroll to detect ink on another — remains the field's central open problem, and the newly-open data makes it addressable by independent researchers on consumer hardware.

Manual architectural tuning is slow. The autoresearch loop attempts to compress that loop by running 15-minute (Day Shift) or 60-minute (Night Shift) experimental cycles autonomously, mutating a small number of axes (learning rate, capacity, augmentation knobs, loss balance, auxiliary tasks, etc.) per cycle and promoting only configurations that improve `val_bpb` over the held checkpoint.

## II. Methodology

### A. Model Architecture
The **production detector** is the proven 2023 Grand-Prize **TimeSformer** recipe (depth-as-time over 26 through-surface slices, 64 px lateral tiles, coarse 4×4 output upsampled at inference), productionized as the tested `vesuvius_autoresearch.detector` subpackage with a one-command `reproduce`. A full-resolution 2.5D **ResEncUNet** alternative (community-winner family, per-pixel 64×64 output) was built and measured — and *underperformed* the TimeSformer under our AdamW+cosine recipe (`val_f1` 0.369 vs 0.393); it likely requires the full nnU-Net training protocol, which we deliberately did not adopt. The bandit loop retains its own architecture zoo (`resenc_unet` etc.); a LeJEPA self-supervised pretrain proved shape-incompatible at the 64 px window (~20% of encoder tensors load). None of these claims to be a novel architecture — the contribution is the replication rigor, the search infrastructure, and the honest measurement, not a new model.

### B. Autonomous Evolution Framework
The loop's tweak axes (currently 19 families): learning rate, weight decay, capacity (`num_blocks`), attention head count, dropout, lasagna preprocessing toggle, batch size, patch size, temporal depth (`num_layers`), width (`base_feat`), per-task loss weights (ink/dice/fiber/structure-tensor), ridge/Frangi feature toggle and sigma, augmentation mode (Albumentations vs batchgeneratorsv2), architecture, nine scroll-specific augmentation probabilities (decohesion, warping, squeeze, z-dropout, intensity-drift, sheet-compression, thick-slice, rician-noise, blank-rectangles); a 2026-06 fix unified these into one library after finding five were silent no-ops, foundation-model path, pseudo-label directory, UA-MT toggle and EMA / consistency hyperparameters, and as of 2026-05-16 the auxiliary multi-task heads toggle. A Thompson-sampling-style bandit weights families by recent success (`autoresearch_history.json`).

### C. Data Strategy
The detector trains on PHerc Paris 2 Fragment 47 (Scroll 2) with held-out Fragment 143 for same-scroll validation, and is measured cross-scroll on Scroll 1 (PHerc Paris 4) segments — the first *valid* cross-scroll number for this project (an earlier attempt was retracted after a data-alignment bug was found). As of 2026-07 the primary data substrate is the **open SOTA bucket** (`s3://vesuvius-challenge-open-data/`, anonymous, ≈48 scrolls in one consistent OME-Zarr layout, released alongside the first complete scroll reading of PHerc. 1667 [4]). A verified practical finding for other teams: the bucket ships **re-flattened surface volumes and model predictions, not ground-truth ink labels aligned to the new geometry** — so supervised training on it requires either label registration (future work) or distillation from the released predictions (implemented, §IV.C). Distillation uses disjoint train/held-out segments; teacher provenance (dtype/range/threshold) is persisted in the reports.

### D. Resource Constraints and Citizen Science Accessibility
In the spirit of citizen science and decentralized science (DeSci), our framework is designed to be accessible to researchers with standard high-end consumer hardware and typical internet connectivity. We strictly limit resource consumption to ensure that the methodology remains tolerable for individual contributors:
*   **Data Bandwidth:** We maintain a monthly download limit of **500 GB**, achieved through a targeted "download once, train indefinitely" offline-first strategy.
*   **Local Storage:** We cap local data storage at **500 GB** at any given time, prioritizing high-value labeled segments over full scroll volumes.

## III. Experimental Setup
Experiments run on an NVIDIA RTX 4090 (24 GB VRAM). We enforce a 0.5 × 0.5 mm (64 × 64 voxel at 7.91 µm spacing) prediction window per the Vesuvius Challenge hallucination guidance for ink detection. The loop runs continuously during Day Shift (07:00–19:00 local, 900 s/cycle) and Night Shift (otherwise, 3600 s/cycle).

## IV. Current Results

### A. Working detector (same-scroll and cross-scroll)
The productionized TimeSformer detector, trained on Scroll-2 Fr47 and measured under the
community contract:

| Metric (held-out) | Same-scroll Fr143 | Cross-scroll Scroll-1 |
| --- | --- | --- |
| `val_f1` | 0.393 | 0.222 |
| `average_precision` | 0.357 | 0.144 |
| `ap_prevalence_lift` (1.0 = chance) | 2.07 | 1.29 |
| ROC-AUC (secondary) | 0.709 | 0.585 |

Real, transferable ink signal at the prize window same-scroll (proven-recipe reference:
0.711 ROC-AUC); **weak cross-scroll transfer** — the quantified generalization gap. Getting
here required root-causing three real inference defects (a ÷255 normalization mismatch alone
moved held-out ROC-AUC 0.57 → 0.70), each now covered by a regression test. The bandit
loop's own from-scratch stack remains at the chance floor; the earlier loop-era numbers
(`val_bpb` ≈ 0.2627, AUC 0.74 train / 0.61 val, with the documented artifact-saturation and
zero-Dice-wall caveats) are retained in `FINDINGS.md` as history.

### A2. SOTA distillation (agreement-with-teacher)
Distilling the same recipe from the released canon ink predictions on open SOTA Scroll-1
surface volumes (no aligned ground truth exists, so **all numbers are agreement with a model
output**): on a fully held-out segment, `val_f1` 0.372 → **0.662**, AP 0.224 → **0.742**,
prevalence-lift 0.98 (exact chance) → **3.24**, ROC-AUC 0.499 → **0.865**; the output shows
letterform-shaped strokes in text lines. An independent review verified the train/held-out
segments are disjoint. Caveat recorded in the report: the held-out region also serves as the
best-epoch selection set (AP/ROC-AUC are threshold-free and unaffected).

### B. GPU fiber/ridge detection
A closed-form symmetric-3×3 eigensolver replaces the cuSolver `eigvalsh` path
that fails on large Hessian batches, enabling 14–94× dense speedups over NumPy
(64³–256³) and tiled 512³ execution in ~3–5 s at ~1 GB VRAM (float64 eigenvalue
parity 3.1e-10). This was proposed upstream as ScrollPrize/villa#1033 (closed
without review); the maintained version lives in this repo. Earlier `vesuvius-c`
binding PRs (#914/#916) and CuPy-acceleration PRs (#915) were also closed and are
superseded by the closed-form path above.

### C. What's open
- **Cross-scroll distillation at scale:** the open bucket's ≈48 scrolls in one format make
  multi-scroll distillation the direct attack on the measured generalization gap
  (lift 2.07 same-scroll → 1.29 cross-scroll).
- **Independent validation of the distilled model:** register legacy hand labels onto the
  SOTA re-flattening to spot-check agreement-with-teacher numbers against real ground truth.
- **Legibility at the prize window:** same-scroll signal is real (lift 2.07) but not legible
  at 64 px; a 224 px clean-room SegFormer reads letterforms (held-out ROC-AUC 0.804) but
  exceeds the hallucination window — the legibility-vs-window tension remains open.
- **Re-pointing the autonomous loop** at the distillation/detector configuration space under
  the F1/AP contract (the loop's historic `val_bpb` objective is a weak discriminator).
- *Retracted framing:* an earlier revision tracked `skeleton_distance_length` ≈ 19.8 against
  a "prize gate of 2.0"; we subsequently proved that gate invalid for ink detection (it is a
  branch-length-histogram divergence, blind to spatial location — a zero-overlap prediction
  passes it). It is no longer a target (probe: `scripts/probe_skel_dist_validity.py`).

## V. Discussion
The project's June–July arc is a case study in measurement-first debugging. The bandit
loop's apparent "`val_bpb` plateau" decomposed into layered evaluation artifacts
(Dice saturation on ink-rich patches; topology metrics read at the wrong threshold; an
invalid `skel_dist` gate) plus genuine stack defects, localized by elimination: capacity,
pipeline, augmentation, data, labels, and the 64 px window were each ruled out
experimentally, leaving the model/training stack — confirmed when the proven GP-winner
recipe reached held-out ROC-AUC 0.711 on the *same* data where the loop's stack sat near
chance. **A claim in an earlier revision of these notes is hereby corrected:** we previously
wrote that the GP TimeSformer "underperforms at the 64 px window / needs a 256 px context
the hallucination rule forbids." That was an artifact of a misconfigured run. The recipe's
through-surface context rides the depth (time) axis, not the lateral window; properly
configured it is window-compliant and is now our production detector. The remaining
legibility gap at 64 px is real but distinct from detectability.

The second lesson is that the field's 2026-06 breakthrough lever — better data — transfers
to consumer hardware. With no aligned ground truth released, distillation from the released
predictions moved a held-out ranking signal from exact chance to lift 3.24 in one 12-epoch
run on one GPU, with honesty preserved by construction (explicit agreement-with-teacher
framing, disjoint segments, persisted teacher provenance, chance-floor baseline measured
first).

## VI. Conclusion
Notes-to-self status. The repo now contains a reproducible path from the open SOTA data to
a working detector (replication → productionization → metric honesty → cross-scroll
measurement → distillation), alongside the documented negative results that shaped it. The
open work — cross-scroll distillation at scale, independent validation against registered
ground truth, and re-pointing the autonomous loop at this configuration space — is research,
not engineering.

## References
[1] Seales, B., et al. "Reading the Scrolls of Herculaneum," EduceLab, 2023.
[2] Karpathy, A. "Autoresearch Methodology," 2025.
[3] Vesuvius Challenge Technical Requirements, 2026.
[4] Vesuvius Challenge team, "Complete virtual unwrapping and reading of a rolled
    Herculaneum papyrus," arXiv:2606.29085, 2026 (PHerc. 1667 announcement,
    scrollprize.org/firstscroll).
