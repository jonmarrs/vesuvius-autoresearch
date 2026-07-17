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
    failures** — distilled students read near chance on held-out human GT (~0.55 ROC).
*   GT fine-tuning on registered labels (POC, 2 segments) made held-out reading *worse*.
*   Cross-scroll transfer is weak (lift 2.07 same-scroll → 1.29 cross); training-scroll
    diversity helps (1.22 → 2.12 on an unseen scroll) but saturates at ~2.1.
*   Consequence: **independent letter-reading at the prize window is not currently within
    reach**; reading-prize work is a capped exploration behind a pre-registered escalation
    gate, not the primary lane.

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
    rendered Scroll-3 data, score honestly. Escalate only past the pre-registered gate
    (held-out ROC > 0.65 or clearly legible letterforms). Submission mechanics
    (`scripts/generate_submission_package.py` + validator) stay dormant until a real
    discovery exists.

## 5. Operational Notes

*   The autonomous loop (`run_autoresearch_loop.py` → `scripts/training/train.py`) runs
    Day/Night shifts in idle windows; pause it (`.loop_paused` + kill PIDs — `stop.sh`'s
    pattern misses `-u` invocations) before editing model/train code.
*   Daily review artifacts: `sprint_logs/`, `history.tsv`, `reports/detector/`,
    `scripts/generate_daily_report.py`.
