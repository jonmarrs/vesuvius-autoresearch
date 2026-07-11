# Research Plan: Vesuvius Challenge (Project 002)

*Updated 2026-07-11. Supersedes the Grand-Prize-era plan (see git history).*

## Objective
Win Vesuvius Challenge **Progress Prizes** by shipping community infrastructure, with a
capped exploratory swing at the open **First Letters / First Title prizes (Scrolls 2–3)**.
The $1M Grand-Prize era closed with PHerc 1667 being read in full (2026-06-25); our
evidence base (see `FINDINGS.md`) says independent letter-reading at the prize-legal
window is not currently within reach, so the primary lane is evaluation infrastructure.

## Strategic Roadmap (Q3 2026)
1. **Primary — ScrollGT (registered-GT benchmark):** release our ground-truth
   registration capability (`repro/sota_data/register*.py`: 2023 human ink labels
   registered onto the open SOTA re-flattened geometry) as a standalone, versioned
   evaluation benchmark + one-command scoring harness
   (`src/vesuvius_autoresearch/detector/metrics.py`) + prize-compliance validator
   (`scripts/validate_prize_artifact.py`). v0.1 = 2 Scroll-1 segments (July);
   v0.2 = Scrolls 2–3 (August).
2. **Secondary — capped First-Letters swing (≤20% GPU):** extract Scroll 2–3 surface
   data (shared with v0.2), run the window-compliant TimeSformer arms, score honestly.
   Pre-registered escalation gate: held-out ROC > 0.65 or clearly legible letterforms;
   otherwise it stays capped.
3. **Monthly filing discipline:** file every Progress Prize cycle (June lapsed; July
   deadline 2026-07-31, draft at `docs/PRIZE_FILING_DRAFT_2026-07.md`).

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
