# July 2026 Progress Prize — Filing Draft

**Status:** DRAFT for review. Deadline 2026-07-31 11:59pm PT. Refresh numbers immediately
before filing via the official Progress Prize form. (The June draft was not filed; this
draft supersedes `PRIZE_FILING_DRAFT_2026-06.md`. Reframed 2026-07-11 around the ScrollGT
release; re-aligned 2026-07-15 to the new monthly prize — *"$20,000 will be awarded every
month to the best open-source submission that makes the collection easier to read"* — and
the prizes page's new emphasis on *held-out validation on ground truth data* and
*false-positive mitigation*.)
**Primary submission artifacts (open-source, MIT):**
- https://github.com/jonmarrs/scrollgt — the honest held-out ground-truth evaluation layer
- the Scroll-3 surface-volume renderer (`repro/sota_data/render_surface.py` in the repo
  below) — makes the bucket's mesh-only segments readable/detectable for the first time
**Methodology/source repo:** https://github.com/jonmarrs/vesuvius-autoresearch (MIT)
**Live experiment tracking:** https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

---

## Title

**Two open-source tools that make the collection easier to read: a renderer that turns the
bucket's mesh-only segments into detector-ready surface volumes, and ScrollGT — the
held-out human-ground-truth evaluation layer the reading effort has been missing (with
published baselines that include our own negatives).**

## Summary

The July prize rewards *"the best open-source submission that makes the collection easier to
read,"* and the prizes page now requires *held-out validation on ground truth data* and
*false-positive mitigation*. This submission is two MIT tools that serve exactly that, plus
the honest measurement discipline behind them.

**(1) A surface-volume renderer for the bucket's mesh-only segments.** Scroll 3 (PHerc0332)
ships two segments in the open bucket as *mesh-only* — no surface volumes, no predictions —
so no one can run ink detection on the live First-Letters scroll without a private renderer;
PHerc 1667's merged full-reading geometry (the segment behind the June-2026 complete
reading) ships the same way. Ours rebuilds the surface from `original.obj` or directly from
the released tifxyz geometry grids, and is **validated against released surface volumes on
two scrolls**: Scroll 1 center-layer NCC 0.59 (just under our pre-registered 0.60 gate —
the miss and its resolution-mismatch cause documented, not hidden) and **PHerc 1667 NCC
0.78, a gate PASS** at matched comparison resolution — the same sampler scoring higher
exactly where the comparison is fair, confirming the Scroll-1 residual was the comparison,
not placement. It has produced the first independent surface volumes from Scroll 3's
mesh-only segments *and* from the PHerc-1667 merged reading geometry (coherent papyrus
fibers). It makes previously-unusable data usable — the most literal "easier to read"
contribution we have.

**(2) ScrollGT — the held-out ground-truth evaluation layer.** The bucket ships surface
volumes and *model predictions* but no human ground truth aligned to the new geometry, so
nobody outside the core team can answer the basic question the new rules now demand held-out
proof of: **does an ink model actually read, or does it reproduce another model?**
**[ScrollGT](https://github.com/jonmarrs/scrollgt)** registers the 2023 Grand-Prize-era human
ink labels onto the SOTA geometry (exact `original.obj` UV bridge, ~8-voxel median residual,
gated alignment validation) and provides a one-command scoring harness (threshold-swept F1
primary, AP-prevalence-lift as the anti-gaming / false-positive gate, ROC-AUC secondary), a
prize-window/overlap compliance checker, CI, and a held-out leaderboard.

ScrollGT's credibility is that it has teeth — demonstrated on its own authors.
Scored against these targets: the **released canon prediction reads a held-out segment
near chance** (ROC-AUC 0.56; 0.70 on a friendlier segment — the first such calibration
published outside the core team); our **distilled students collapse from 0.79+
train-exposed to ~0.55 held-out** (distillation reproduces the teacher *including its
failures*); and **fine-tuning on the registered labels made reading worse** (0.558 →
0.531, collapsing to the trivial all-positive predictor). Every negative is a published
baseline row. The project also **caught and corrected its own over-reads** under internal
review before release — that discipline is what the benchmark packages for everyone else.

## What is being released (open tools)

1. **ScrollGT** (https://github.com/jonmarrs/scrollgt) — **the headline release.**
   Three registered ground-truth targets on the SOTA data (two train-exposed regions and a
   held-out flagship Scroll-1 segment), each with full registration provenance, gates, and
   residual caveats in `meta.json`; the `scrollgt score` harness (PNG/npy probability maps
   → scorecard; verified to reproduce the published canon-teacher baseline to 4 decimals
   *and* to run from a clean clone in one command); the `scrollgt check` prize-compliance
   pre-check (official ≤64px/0.5mm window rule + train/predict overlap); published baselines
   including the negatives, a front-page held-out leaderboard, `CONTRIBUTING.md` submit-a-row
   flow, GitHub Actions CI (py3.10–3.12), a quickstart notebook, 15 tests, MIT. Each target
   ships only after an **independent, teacher-free orientation validation** — three
   gate-passing regions were *withheld* because their orientation could not be verified
   (integrity as a feature, not a limitation). Anyone can score a model today with
   `git clone` + one command. (An expansion to more Scroll-1 targets is the next step; a
   Scrolls 2–3 extension is blocked because those scrolls are unread and ship no human
   ground truth — that gap is *why* First Letters is open.)

2. **Ink detector subpackage** (`vesuvius_autoresearch.detector`) — the proven 2023
   Grand-Prize TimeSformer recipe productionized as a tested subpackage
   (`config`/`data`/`model`/`train`/`infer`/`eval`/`cli`) with a one-command `reproduce`.
   Held-out same-scroll: **val_f1 0.393 / AP 0.357 / prevalence-lift 2.07 / ROC-AUC 0.709**
   (proven reference 0.711), window-compliant (64 px lateral; depth is the through-surface
   axis). Surfacing this required fixing real inference defects (input normalization,
   PyTorch-2.6 checkpoint loading, shape alignment) — each documented with a regression
   test. → [reports/detector/REPRODUCTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/REPRODUCTION.md)

3. **Community metric contract + cross-fragment measurement** (`detector/metrics.py`,
   `measure` CLI; the same contract ScrollGT ships) — `val_f1` (threshold-swept) primary;
   **average precision** and **AP-prevalence-lift** (AP ÷ base rate; ≈1 ⇒ chance) as
   imbalance-robust honesty gates; ROC-AUC demoted to a secondary diagnostic. Includes the
   **first valid cross-scroll measurement** for this project: the same detector scores
   lift 2.07 same-scroll but only **1.29 cross-scroll** — quantifying the generalization
   gap the field is attacking.
   → [reports/detector/cross_scroll_measurement.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_measurement.md)

4. **SOTA open-data tooling** (`repro/sota_data/`) — anonymous-S3 discovery/fetch of
   `s3://vesuvius-challenge-open-data/`, OME-Zarr region extraction, detector-format
   conversion with loud alignment guards, and a documented survey of what the bucket
   actually ships (re-flattened multiscale surface volumes + model predictions; **no
   ground-truth ink labels aligned to the new geometry** — the gap ScrollGT fills).

5. **SOTA distillation + ground-truth measurement pipeline** (`repro/sota_data/`) —
   teacher–student distillation from the released canon predictions onto SOTA surface volumes
   (disjoint train/held-out segments, chance-floor baseline, persisted provenance), the
   multi-scroll registry + controlled cross-scroll experiments, **and** the ground-truth
   registration harness (`register.py`, `register_run.py`, `gt_register.py`) that ScrollGT
   productizes.
   - *Agreement-with-teacher* results (fidelity to the released prediction, NOT accuracy):
     held-out val_f1 0.372 → 0.662 / lift 0.98 → 3.24; multi-scroll diversity lifts unseen-
     scroll transfer 1.22 → 2.12, saturating at ≈2.1 with a third scroll.
   - *Ground-truth* results (vs human labels): the canon teacher scores ROC-AUC 0.56–0.70
     (segment-dependent); on a **held-out** segment the distilled students read **near chance
     (ROC-AUC ~0.55)** — the agreement-with-teacher gains were largely train-region fit.
   - *Ground-truth fine-tuning* (new this week, a documented negative): fine-tuning the best
     student on the registered labels **reduced** held-out discrimination (ROC 0.558 → 0.531)
     and collapsed it to the trivial all-positive predictor — human-label supervision at this
     scale (2 segments) is not a cheap unlock.
   → [sota_distill_measurement.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/sota_distill_measurement.md),
   [cross_scroll_distill.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_distill.md),
   [cross_scroll_scale.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/cross_scroll_scale.md),
   [registered_gt_heldout_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_heldout_validation.md),
   [gt_finetune_heldout.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/gt_finetune_heldout.md)

6. **Surface-volume renderer for mesh-only segments** — a **one-command CLI**
   (`repro/sota_data/render_cli.py`; docs at
   [SURFACE_RENDERER.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SURFACE_RENDERER.md)),
   accepting either a segment `original.obj` (with teacher-free coordinate-scale
   inference) or, new this week, the **released tifxyz geometry grids** directly — the
   format most bucket segments ship, with no scale ambiguity. **Label-free output** (no
   fabricated GT). **Validated against released surface volumes on two scrolls,
   pre-registered gate NCC ≥ 0.60:** Scroll 1 scored 0.59 (miss, attributed to a
   resolution-mismatched comparison — reported as FAIL, not spun), and **PHerc 1667 scored
   0.78 — PASS** at near-matched resolution, confirming the Scroll-1 attribution with the
   same sampler. Applications: the first independent surface volumes from Scroll 3's two
   mesh-only segments (the live First-Letters scroll), and — new this week — from **PHerc
   1667's merged full-reading geometry** (the ~20-gigapixel segment behind the June-2026
   complete reading, which ships mesh-only). In both cases running arm C over the renders
   shows **texture, not letterforms** — the cross-scroll ceiling demonstrated on the prize
   scrolls themselves, not merely argued.
   → [render_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/render_validation.md),
   [render_validation_1667.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/render_validation_1667.md),
   [scroll3_first_look.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/scroll3_first_look.md),
   [merged1667_first_look.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/merged1667_first_look.md)

7. **Carried forward from June (still maintained):** the scroll-specific 3D augmentation
   library ([villa #201](https://github.com/ScrollPrize/villa/issues/201);
   [docs/SCROLL_AUGMENTATIONS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/SCROLL_AUGMENTATIONS.md)),
   GPU fiber/ridge detection (closed-form 3×3 eigensolver, 14–94× over NumPy;
   [docs/FIBER_DETECTION.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/docs/FIBER_DETECTION.md)),
   the evaluation & feasibility-probe suite (pixel-AUC, overfit probe, learnable-target
   control, leak-free spatial splits), and the autoresearch loop — which this month was
   **rewired to select models on the honest F1/AP-lift contract** (its former `val_bpb`
   selection metric was a weak discriminator, and its inherited topology gate was proven
   invalid — see Findings).

## Findings (the methodological contribution)

Full narrative: [FINDINGS.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/FINDINGS.md).
The through-line is measurement honesty:

- **The metric matters more than the model.** Dice/`val_bpb` saturate on ink-rich patches
  (a near-constant predictor scores Dice ≈ 0.75); ROC-AUC is over-optimistic under class
  imbalance. The adopted contract (F1-swept + AP + prevalence-lift) exposed both our own
  chance-floor results and the real improvements — and as of this month it is also the
  autonomous loop's model-selection criterion, replacing `val_bpb`.
- **A "prize topology gate" we inherited is provably invalid** (`skel_dist` is a
  branch-length-histogram divergence, blind to location — a zero-overlap prediction passes).
  We removed it from every decision path and published the probe.
- **Cross-scroll generalization is the bottleneck, quantified:** lift 2.07 same-scroll →
  1.29 cross-scroll for the same detector; and better data alone does not fix it (the
  detector run on SOTA data produced texture, not ink, until retrained).
- **Distillation reproduces the teacher on consumer hardware — measured as agreement, then
  checked against truth.** Training against the canon predictions lifted held-out
  *agreement-with-teacher* from chance to lift 3.24 (disjoint segments, review-verified). But
  the ground-truth calibration below shows this is teacher *fidelity*, not reading ability:
  on held-out data vs human labels the same students are near chance. Read the 3.24 as
  "faithfully reproduces the teacher," not "reads ink."
- **Training-scroll diversity drives generalization; scaling saturates — both measured.**
  At fixed budget, adding a second training scroll lifted unseen-scroll (PHerc 1667)
  transfer from lift 1.22 to 2.12 (single-scroll distillation actually *over-specializes*,
  landing below the undistilled detector cross-scroll); a third scroll plus 50% more data
  did not lift it further (≈2.1 plateau). A full bucket sweep found only 4 of 45 scrolls
  ship canon teacher predictions today — the practical frontier is released teachers, not
  scan volumes.
- **Negative results, kept honest:** a community-style full-resolution 2.5D ResEncUNet
  *underperformed* the TimeSformer under our recipe (val_f1 0.369 vs 0.393); and
  **ground-truth fine-tuning on the registered labels made held-out reading worse**
  (ROC 0.558 → 0.531, collapsing to the trivial all-positive predictor — recall 1.0,
  swept F1 exactly 2p/(1+p)). Both documented rather than discarded; the fine-tune
  negative is what a first injection of human-label signal at POC scale (2 segments,
  ~8-voxel registration residual) actually buys.
- **Ground-truth calibration on SOTA data (registered hand labels) — the load-bearing
  finding, now shipped as ScrollGT.** No ground-truth labels aligned to the SOTA
  re-flattening are released, so we built the bridge: register the 2023 hand label onto SOTA
  geometry via the segment's `original.obj` vertex texture coordinates (nearest-vertex map,
  ~8 old-scan-voxel residual), gate on validated alignment before scoring, then measure.
  Two segments:
  - **A datapoint nobody outside the core team has published:** the released canon prediction
    scores **ROC-AUC 0.56–0.70 vs human labels**, segment-dependent (0.70 on one, 0.56 on
    another where it reads the ink poorly). Agreement-with-teacher was therefore agreement
    with a *variable, often mediocre* proxy — not truth.
  - **The sobering held-out result:** on a segment **no distilled student trained on**, scored
    against human ground truth, the students read **near chance (ROC-AUC ~0.55, prevalence-
    lift ~1.16)** — statistically tied with the (weak) teacher and the undistilled detector.
    The distilled "wins" reported on training regions (up to ROC-AUC 0.80) were **substantially
    train-region fit**. Distillation faithfully reproduces the teacher — *including its
    failures* — rather than learning to read independently. (The same registration quality let
    the good-teacher segment score 0.70, so the near-chance number is real, not a registration
    artifact.)
  - → [registered_gt_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_validation.md),
    [registered_gt_heldout_validation.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/registered_gt_heldout_validation.md)
- **A per-segment quality map of the released canon prediction (new this week) — it reads
  its showcase family and little else.** Across all six Scroll-1 segments for which a 2023
  hand label, an `original.obj`, and a bridge mesh all exist, the teacher-enrichment
  orientation check fires on **exactly one** segment (20230702185753). On the other five the
  released prediction is too weak for enrichment to even validate the label's orientation.
  Combined with the ground-truth ROC-AUCs (0.49–0.73, segment-dependent), this is the first
  independent, per-segment characterization of *where* the canon release is and isn't
  trustworthy — a datapoint no one outside the core team has published.
  → [orientation_probe_2026-07-11.md](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/orientation_probe_2026-07-11.md)
- **The fit-vs-reading exhibit (new this week).** The *same* GT-fine-tuned model scores
  **ROC-AUC 0.954 on its own training region and 0.531 on the held-out target** — a
  0.42-ROC gap between memorizing labels and reading ink, in one benchmark, from one model.
  It is the sharpest single demonstration of why an eval must have a held-out surface and
  why exposed-region scores are never reading ability. (The 0.954 also confirms the
  registered labels on that region are genuine learnable signal, not registration noise.)
  → [scrollgt_y7000_baselines.json](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/scrollgt_y7000_baselines.json)
- **We caught and corrected our own over-read.** The first (train-region) ground-truth result
  was initially framed as students "matching or exceeding" the teacher; internal review flagged
  a binary-vs-continuous metric confound and the train-region confound, and the held-out
  measurement then showed the effect was largely fit. The committed reports lead with the
  corrected framing. This self-correction *is* the methodological contribution — and the
  reason ScrollGT's baselines can be trusted: the eval caught its own authors first.

## Honest limitations (stated plainly)

- **We do not have a strong ink detector.** On held-out data vs human ground truth the
  distilled models read near chance, and ground-truth fine-tuning at POC scale made it
  worse. The agreement-with-teacher figures (up to lift 3.24) measure fidelity to a
  released model output, not reading ability; where that output is weak, matching it is
  worthless. This is stated so no reader mistakes the distillation numbers for accuracy.
- **The ground-truth registration is approximate and one validation used a teacher-free gate.**
  The registration is a nearest-vertex geometric bridge (~8 old-scan-voxel residual; scores
  are lower bounds on true agreement — stated in every ScrollGT `meta.json`); its 2D
  orientation is carried from a decisively-validated segment as an export-pipeline invariant
  (the residual/periodicity checks are convention-blind). On the held-out segment the standard
  (teacher-dependent) alignment gate false-negatived because the teacher is weak there, so
  validation used a codified teacher-free gate (residual + text-line periodicity) — disclosed
  in the report, in the ScrollGT metadata, and reproducible from the committed code.
- **The clean cross-scroll ground-truth test is still blocked:** PHerc 1667 (and other
  non-training scrolls) ship only model predictions, no released human labels (bucket
  re-surveyed 2026-07-17: Scroll 2 ships no segments at all; Scroll 3 ships no labels — those
  scrolls are unread, which is why First Letters is open). ScrollGT v0.2 therefore targets
  more Scroll-1 segments plus a PHerc-1667 path: now that 1667 has been read in full, the
  scholar-validated published reading is the first realistic non-Scroll-1 ground-truth
  source (transcription-level, coarser than pixel labels). The first step is already done:
  the merged full-reading geometry, which ships mesh-only, now has an independent rendered
  surface volume (gate-validated on this scroll, NCC 0.78).
- The prior distillation held-out region also served as its best-epoch selection set (AP/ROC-AUC
  are threshold-free and unaffected); noted in that report.
- We claim an **honest, reproducible measurement layer** for the SOTA data — registered
  ground truth, a scoring contract with an anti-gaming gate, published baselines with
  negatives — plus the documented finding that distillation-from-canon does not, on this
  evidence, yield independent reading. Not a state-of-the-art model.

## Reproducibility

Public repos, MIT-licensed. The data path uses only the open bucket (anonymous S3, partial
OME-Zarr reads — no credentials, no special hardware beyond one 24 GB GPU; ScrollGT scoring
itself is CPU-only):

```bash
# ScrollGT: score any prediction against registered ground truth (CPU, seconds)
git clone https://github.com/jonmarrs/scrollgt && pip install -e scrollgt/
scrollgt score my_prediction.png scrollgt/data/scroll1_20231210121321
scrollgt check --window-px 64 --scan-um 8.0

# methodology repo: unit tests (CPU)
CUDA_VISIBLE_DEVICES="" uv run python -m pytest tests/test_detector_*.py tests/test_sota_*.py -q
# reproduce the working detector (train + eval, GPU)
uv run python -m vesuvius_autoresearch.detector.cli reproduce
# cross-scroll measurement of any checkpoint
uv run python -m vesuvius_autoresearch.detector.cli measure --checkpoint <ckpt>
# SOTA distillation end-to-end (network + GPU)
uv run python -m repro.sota_data.distill_run prep|baseline|train|measure
```

## Links

- **ScrollGT (headline release): https://github.com/jonmarrs/scrollgt**
- Methodology repo: https://github.com/jonmarrs/vesuvius-autoresearch
- Findings: .../blob/main/FINDINGS.md
- Lab notebook: .../blob/main/docs/LAB_NOTEBOOK.md
- Detector reproduction: .../blob/main/reports/detector/REPRODUCTION.md
- Cross-scroll measurement: .../blob/main/reports/detector/cross_scroll_measurement.md
- SOTA distillation result: .../blob/main/reports/detector/sota_distill_measurement.md
- Ground-truth calibration: .../blob/main/reports/detector/registered_gt_heldout_validation.md
- GT fine-tune negative: .../blob/main/reports/detector/gt_finetune_heldout.md
- wandb: https://wandb.ai/jdmarrs-uc-davis/vesuvius-autoresearch

## Pre-filing checklist (internal — delete before submission)

- [ ] Refresh all numbers against the latest committed reports.
- [ ] Re-verify every repo link resolves on GitHub main (both repos).
- [ ] Confirm no AI-authorship markers anywhere in linked artifacts (incl. scrollgt).
- [ ] Cite any early ScrollGT traction (stars/issues/external scores) if it exists by
      filing time; do not manufacture or overstate it.
- [ ] File via the official Progress Prize form before 2026-07-31 11:59pm PT.
