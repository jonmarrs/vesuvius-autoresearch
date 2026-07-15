# Research Plan: Vesuvius Challenge (Project 002)

*Updated 2026-07-15 for the new prize announcement. Supersedes the Grand-Prize-era plan.*

## Prize landscape (2026-07-15 announcement)
- **New 2027 Grand Prize** ($1M): fully read a complete eligible-set scroll using ≤8 hours
  of human input, by 2027-06-25. Not our lane (needs a full read pipeline).
- **10 Letter-Discovery prizes** ($50k/scroll) + a **Title prize** ($50k, Scroll 1) across
  the eligible set, same deadline. Our evidence (`FINDINGS.md`) says independent
  letter-reading at the prize-legal ≤0.5×0.5mm window is not within reach for us.
- **Monthly prize, restructured:** *"$20,000 will be awarded every month to the best
  open-source submission that makes the collection easier to read"* (Gold Aureus $20k /
  Denarius $10k / Sestertius $2.5k / Papyrus $1k tiers below it). The prizes page now
  explicitly requires **held-out validation on ground truth data** and **false-positive
  mitigation**. June tooling winners were modest and practical ($2k ML augmentations +
  tool optimization; $1k fiber-annotation format conversion) — the winning genre is small,
  documented, *adopted* open-source tools.

## Objective
Win **monthly open-source Progress Prizes** with tools that literally *make the collection
easier to read and easier to evaluate honestly* — directly matching the restructured prize
and the new held-out-ground-truth requirement. A capped exploratory swing at First Letters
stays behind a pre-registered gate.

## Strategic Roadmap (Q3 2026)
1. **Primary A — surface-volume renderer (`repro/sota_data/render_surface.py`):** turns the
   bucket's mesh-only segments (e.g. Scroll 3 / PHerc0332) into detector-ready surface
   volumes — the most literal "makes the collection easier to read" contribution; validated
   against a released Scroll-1 surface (NCC ~0.59).
2. **Primary B — ScrollGT (registered-GT evaluation):** the held-out human-ground-truth
   scoring layer the new rules require, released standalone
   (github.com/jonmarrs/scrollgt): registration (`repro/sota_data/register*.py`) + honest
   metric contract (`detector/metrics.py`, AP-lift as the false-positive gate) +
   compliance checker + CI + leaderboard. 3 validated targets; expand with more verifiable
   Scroll-1 targets (a Scrolls 2–3 extension is impossible — unread scrolls have no GT).
3. **Secondary — capped First-Letters swing (≤20% GPU):** window-compliant arms on
   rendered Scroll-3 data, scored honestly. Pre-registered escalation gate: held-out
   ROC > 0.65 or clearly legible letterforms; otherwise capped.
4. **Monthly filing discipline:** file every cycle (June lapsed; July deadline 2026-07-31,
   draft at `docs/PRIZE_FILING_DRAFT_2026-07.md`, framed to the new "easier to read"
   language + held-out-GT emphasis).

## Core Research Focus
1. **Honest evaluation:** threshold-swept F1 / AP-prevalence-lift / ROC-AUC
   (`detector/metrics.py`) against registered human ground truth — the metric contract
   that caught near-chance reading, including our own.
2. **Autonomous loop (idle windows only):** `run_autoresearch_loop.py` +
   `scripts/training/train.py`, selecting on the honest F1 contract since 2026-07-11.
3. **Hallucination compliance:** prediction window ≤ **0.5×0.5 mm (64×64 px @ 8µm)**,
   zero train/predict overlap (mechanically checked by
   `scripts/validate_prize_artifact.py`).

## Constraints
- Single RTX 4090 (24GB), 500GB storage, open anonymous-S3 data only, MIT, no credentials.

## Verification & Submission
- **Scoring:** `detector` `measure` CLI produces JSON scorecards vs registered GT.
- **Submission mechanics (dormant until a real discovery):**
  `scripts/generate_submission_package.py` + `scripts/validate_prize_artifact.py`
  enforce scale bar, 3D position, window cap, and the non-overlap audit.
