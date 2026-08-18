# Vesuvius Autoresearch Strategy: Systematic Progress Plan

*Rewritten 2026-07-11. The April–May version of this document (see git history) described
a Grand-Prize-era plan and readiness-audit checkboxes that our own findings later refuted;
`FINDINGS.md` is the authoritative record of what actually works.*

This document outlines the research strategy for winning Vesuvius Challenge prizes while
operating within strict hardware, storage, and bandwidth constraints. The current plan of
record is summarized in **[research_plan.md](./research_plan.md)** (Q3 2026: ScrollGT
benchmark primary; capped First-Letters swing; monthly filing discipline).

## 1. Constraints & Compliance

*   **GPU (RTX 4090):** 24 GB VRAM. Single card — GPU time is the scarcest resource;
    workstreams are explicitly budgeted (benchmark work has priority; the autonomous loop
    runs in idle windows only).
*   **Prize compliance:** strict **0.5×0.5 mm window (64×64 px @ 8µm)** and **zero
    train/predict overlap** — mechanically enforced by
    `scripts/validate_prize_artifact.py` and the loop's `evaluate_prize_gates`.
*   **Storage:** 500 GB project limit; prioritize labeled segment-volume pairs over full
    scroll volumes.
*   **Reproducibility:** MIT, open anonymous-S3 data only, no credentials, single-GPU
    reproducible. `Dockerfile` provided.

## 2. Evaluation Strategy (the load-bearing asset)

Honest measurement is this project's differentiator:

*   **Metric contract:** threshold-swept F1 (primary), AP-prevalence-lift (imbalance-robust
    real-signal gate), ROC-AUC (secondary) — `src/vesuvius_autoresearch/detector/metrics.py`
    + the `measure` CLI. The inherited `skeleton_distance` gate was proven invalid
    (location-blind) and removed from all decision paths.
*   **Ground-truth registration:** `repro/sota_data/register*.py` registers 2023 human ink
    labels onto the open SOTA re-flattened geometry (obj-exact bridge, ~8-voxel residual,
    teacher-free alignment gates). This enabled the first independent GT calibration of the
    released canon predictions and is being productized as the **ScrollGT** benchmark.
*   **Selection:** the autonomous loop promotes models on this contract as of 2026-07-11
    (`scripts/training/train.py`, `is_f1_improvement`).

## 3. Established findings that bound the strategy (see FINDINGS.md for detail)

*   Fresh 64px training sits near chance on our data; capacity/pipeline are proven fine.
*   Distillation from the released canon predictions reproduces the teacher **including its
    failures**. ⚠ **CORRECTED 2026-08-15.** This bullet used to end "distilled students read
    near chance on held-out human GT (~0.55 ROC)". That was a misregistration artifact, not a
    result: a hardcoded `LEVEL0_SHAPE` put the held-out label ~1766 voxels out of place.
    Re-registered, the same students score **roc 0.731 (arm B) / 0.746 (arm C)** against
    **0.518** for the all-positive floor, and the canon teacher **0.753**. The students were
    reading held-out ink the whole time. The teacher-reproduction half of the bullet stands;
    the near-chance half is retracted
    ([`registration_offset_2026-08-07.md`](../reports/detector/registration_offset_2026-08-07.md)).
*   ~~GT fine-tuning on registered labels (POC, 2 segments) made held-out reading *worse*.~~
    ⚠ **RETRACTED 2026-08-15.** That model was fine-tuned on a displaced label and scored
    against a displaced label; degradation toward the trivial all-positive predictor is the
    expected behaviour of a model measured against a mislocated target. The experiment has
    not been re-run and **cannot be**: exactly one Scroll-1 segment is hand-labelled,
    re-flattened and correctly placed, and it is spent as the held-out evaluation target, so
    there is no training set
    ([`gt_training_data_exhaustion_2026-08-15.md`](../reports/detector/gt_training_data_exhaustion_2026-08-15.md)).
*   Cross-scroll transfer is weak (lift 2.07 same-scroll → 1.29 cross); training-scroll
    diversity helps (1.22 → 2.12 on an unseen scroll) but saturates at ~2.1.
*   **Detection at the prize window is real and held-out; legibility is not, and the
    detection we have is borrowed.** (Re-derived 2026-08-15, replacing the bullet retired
    below.)

    Distilled students run at `size = 64`, and `DetectorConfig.validate_window()` hard-fails
    anything wider, so every number here is **inside** the 64 px @ 8 µm prize window. Against
    registered human ground truth on held-out `20231210121321` (all-positive floor 0.518):
    arm B **0.7305**, arm C **0.7462**, canon teacher **0.7526** roc_auc, AP-lift 2.3–2.4.
    Arm A scores 0.7716 but was best-epoch-selected on this segment, so read B and C as the
    clean rows. That is genuine held-out detection at the prize window, and it retires the
    "near chance" premise outright.

    Three things nonetheless keep the strategic conclusion standing, on new grounds:

    1.  **The capability is inherited, not learned.** Fresh 64 px training still sits at
        chance (first bullet, unretracted). The students match the teacher rather than
        beating it — 0.73–0.75 against its 0.753 — which is distillation fidelity, exactly
        what the second bullet says. Nothing here demonstrates *independent* reading.
    2.  **The window costs legibility, not detectability.** 224 px reads letterforms; 64 px
        yields detectable-not-legible signal (`LAB_NOTEBOOK.md`, 2026-06-16 verdict as
        refined). Detection at 0.75 roc_auc is not letter-reading, and the gap between them
        is the window itself, which the prize fixes.
    3.  **Our instrument cannot certify legibility at this scale anyway.** The registered-GT
        floor is ~0.31 mm against a 0.512 mm window — ~60%. Registered-GT evaluation can
        establish detection but is structurally unable to resolve within-window letterform
        structure, so "we read letters at 64 px" is not a claim this evidence *could* support
        even if it were true.

    **Conclusion, re-derived: independent letter-reading at the prize window is still not
    within reach** — but for a materially different reason than before. It is no longer "our
    models do not read held-out ink," which was false. It is that detection ≠ legibility, and
    what detection we have is the teacher's.

    **Escalation gate, updated.** The old implicit trigger was "can we get off chance?" —
    already passed, and it passed a month ago without anyone noticing because the
    misregistration hid it. The trigger that now means something: **a model that beats the
    canon teacher held-out at ≤64 px by a margin wider than the selection caveat.** Matching
    it is fidelity; beating it is independence. Reading-prize work stays a capped exploration
    behind that gate, not the primary lane.

## 4. Prize-Specific Workflows

*Aligned to the 2026-07-15 announcement: the monthly prize is now "$20,000 … to the best
open-source submission that makes the collection easier to read," and milestone submissions
require held-out ground-truth validation + false-positive mitigation.*

*   **Monthly open-source Progress Prizes (primary):** two MIT tools that make the
    collection easier to read / evaluate — the **surface-volume renderer** (mesh-only
    segments → detector-ready volumes) and **ScrollGT** (held-out registered-GT evaluation +
    AP-lift false-positive gate). File every cycle (deadline discipline after the lapsed
    June cycle). Grow ScrollGT with more *orientation-verifiable* Scroll-1 targets — NOT a
    Scrolls 2–3 extension, which is impossible (unread scrolls ship no human GT; Scroll 2
    ships no segments at all — bucket survey 2026-07-17). The v0.2 (August) lead is
    **PHerc 1667**: render its June-2026 merged mesh-only segment, then align the published
    full-reading transcription as the first non-training-scroll GT — see
    `reports/detector/scrollgt_v02_groundwork.md`.
*   **First Letters / Title (secondary, ≤20% GPU):** run the window-compliant arms on
    rendered Scroll-3 data, score honestly. ⚠ **This bullet's gate was superseded 2026-08-16
    and the two must not be read together.** It said "held-out ROC > 0.65 or clearly legible
    letterforms", which the corrected numbers now *clear* (arms B/C at 0.7305/0.7462), while
    the gate re-derived in section 3 above (**beat the canon teacher, 0.7526, by more than
    the selection caveat**) is *not* cleared. Two gates giving opposite answers is an
    artifact of adding the second without reconciling the first; **section 3's gate
    governs.** This one is also inapplicable on its own terms: it was written for rendered
    Scroll-3 data, which ships no human ground truth at all, so it was never testable there
    and the Scroll-1 substitute is a single held-out target. Submission mechanics
    (`scripts/generate_submission_package.py` + validator) stay dormant until a real
    discovery exists.

## 5. Operational Notes

*   The autonomous loop (`run_autoresearch_loop.py` → `scripts/training/train.py`) runs
    Day/Night shifts in idle windows; pause it (`.loop_paused` + kill PIDs — `stop.sh`'s
    pattern misses `-u` invocations) before editing model/train code.
*   Daily review artifacts: `sprint_logs/`, `history.tsv`, `reports/detector/`,
    `scripts/generate_daily_report.py`.
