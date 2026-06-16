# June 2026 Progress Prize Packaging — Design

**Date:** 2026-06-15
**Status:** approved
**Goal:** Produce ready-to-file June Progress Prize materials that lead with the
open-source tooling and a rigorous, reproducible methodological finding (direct
ink detection at the 0.5 mm / 64 px window is learnability-limited), refreshed to
reflect the now-complete experimental arc. The user files via the official form
and posts to Discord; this work produces the drafts.

## Context

The model-improvement arc is conclusively closed: six experiments + two probes
(culminating in the brightness control — 0.99 AUC on a learnable target vs ~0.51
on ink at the identical regime) show that legible ink is not a learnable function
of a 64 px CT patch by direct supervision. The existing filing draft
(`docs/PRIZE_FILING_DRAFT_2026-06.md`) predates this and still frames the model as
"mediocre but improving" with "cross-scroll transfer as the stated research
target." The June path is the standalone repo-as-artifact + honest methodology
(villa PRs are closed on sight — not a route). Deadline 2026-06-30; file ~June
24-28 after a final numbers refresh.

Hard constraints (carried from prior memory): no AI-authorship markers anywhere
in filing text, the report, or the Discord post; the user files/posts personally;
lead with open tools + honest methodology, not model accuracy; do not present the
closed May villa PRs as merged.

## Deliverables

### 1. Negative-results report (new centerpiece)

`reports/ink_detection_64px_window_study_2026-06.md` — a standalone, citable study
of the window-limited finding. Sections:

- **Question & why it is binding** — can a model learn ink directly from 64 px
  (0.5 mm) CT patches? The 0.5 mm hallucination rule forbids the large-context
  approaches (e.g. the GP-winning TimeSformer at 256 px) that otherwise work.
- **Method / rigor** — pooled pixel AUC as the honest metric (vs artifact-saturated
  Dice/`val_bpb`); leak-free spatial splits (Fr143 U/V regions, 128 px buffer);
  fresh-init controls (no warm-start leakage); the gated learning-curve hook.
- **Evidence chain** — one tight paragraph each, each with its number and what it
  rules out: TimeSformer@64px (~0.49/0.56), LeJEPA (window-incompatible),
  pseudo-label + oracle (more same-scroll data doesn't help; 0.49→0.50),
  12 h long-schedule (flat 0.508–0.525), overfit probe (memorizes 16 patches to
  1.0 → capacity/pipeline fine), augmentation ablation (none vs full both ~chance
  → aug not the bottleneck), and the **decisive brightness control** (0.99 by step
  300 vs ink ~0.51, identical regime → not optimization/LR).
- **Verdict & honest scope** — at 64 px, ink is not a learnable function of the CT
  patch *for direct supervised detection with this preprocessing*; explicitly NOT
  a claim that no representation/preprocessing could recover it, and noting the
  production model's ~0.56 is warm-start accumulation, not fresh-trainable signal.
- **Reproduce** — exact scripts (`scripts/overfit_probe.py`,
  `scripts/control_fulldata_probe.py`, `scripts/spatial_split_mask.py`,
  `scripts/pixel_auc.py`, the `eval_every_steps` hook) + run commands.

Numbers come from the committed FINDINGS.md / memory of this session; every figure
in the report must match a committed result (no invented numbers).

### 2. Filing-draft refresh (`docs/PRIZE_FILING_DRAFT_2026-06.md`)

- **Findings** section: rewrite so the window-limited study is the headline
  methodological contribution; link the new report. Keep the artifact-saturated-
  metrics and bugs-found points (still valid and valuable).
- **Honest current results** section: replace the "mediocre but improving /
  cross-scroll is the target" framing with the honest verdict (direct detection at
  0.5 mm is learnability-limited; production ~0.56 is warm-start accumulation).
- **Open tools** list: add the probe/eval suite (`pixel_auc`, `overfit_probe`,
  `control_fulldata_probe`, the gated learning-curve hook, leak-free split tools)
  as part of the methodology deliverable.
- Keep the internal "refresh numbers at file time; no AI markers; don't present
  closed PRs as merged" note.

### 3. Discord post refresh (`docs/DISCORD_POST_DRAFT_2026-06.md`)

Short, technical, reframed around the finding + the tools; invites replication /
discussion of the 64 px learnability result. No prize mention, no AI markers.

### 4. Light repo consistency

Link the new report from `README.md` and `FINDINGS.md` so the repo presents it as
the methodology centerpiece. No clean-clone reproduction audit (out of scope per
the chosen packaging tier).

## Components & boundaries

Four independent documents, each editable/reviewable on its own: the report (new),
the filing draft (edit), the Discord post (edit), and the README/FINDINGS links
(small edits). The report is the source of truth for the finding; the filing draft
and Discord post summarize and link it.

## Verification

- Every numeric claim in the report and filing draft traces to a committed result
  (FINDINGS.md / session memory) — no new/invented numbers.
- No AI-authorship markers anywhere in the three outward documents.
- The report's reproduce commands name scripts that exist in the repo.
- Filing draft no longer contains the stale "mediocre but improving / cross-scroll
  is the target" framing.
- Internal filing notes (refresh-at-file-time, closed-PRs caveat) retained.

## Out of scope

- New code (all tooling exists and is committed/tested).
- Filing the form / posting to Discord (the user does this).
- The end-to-end clean-clone reproduction audit (the un-chosen packaging tier).
- Reopening any villa PR.
