# June 2026 Progress Prize Packaging Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Produce ready-to-file June Progress Prize drafts that lead with the open tooling and the rigorous window-limited finding, refreshed to the completed arc.

**Architecture:** Docs-only. One new standalone report (the centerpiece), refreshes to the filing draft and Discord post, and link edits in README/FINDINGS. No code. "Tests" are self-checks: every number traces to a committed result, and no AI-authorship markers appear in outward documents.

**Tech Stack:** Markdown. Source of truth for numbers: committed `FINDINGS.md` + this session's results.

**Spec:** `docs/superpowers/specs/2026-06-15-june-prize-packaging-design.md`

**Global constraints (apply to every task):**
- No AI-authorship markers anywhere in `reports/…study….md`, `PRIZE_FILING_DRAFT…`, `DISCORD_POST_DRAFT…` (text or commit-trailers on these are fine, but not inside the documents).
- Every numeric claim must match a committed FINDINGS.md figure (listed in Task 1). Invent nothing.
- Do not present the closed May/June villa PRs as merged/open routes; the fibers tool is cited as a public repo artifact.

---

## Reference numbers (all already committed in FINDINGS.md — cite these verbatim)

| Experiment | Result to cite |
| --- | --- |
| TimeSformer @64px | per-patch AUC ~0.49 train / ~0.56 val (needs 256px context the window forbids) |
| LeJEPA 64px init | only ~20% of encoder tensors shape-compatible; large-window pretrain |
| Pseudo-label + oracle | baseline V-region pooled pixel AUC ~0.49; pseudo-label quality vs truth AUC 0.502 (chance); oracle (true U-region labels) 0.50 — no lift |
| 12h long-schedule | 12-point pooled pixel-AUC curve flat 0.508–0.525, no trend |
| Overfit probe | fresh model memorizes 16 fixed ink patches 0.42 → 1.0 in 100 steps |
| Augmentation ablation | FULL 0.522 train / 0.490 val; NONE 0.509 train / 0.525 val (both ~chance) |
| Brightness control | 0.97 @ step 50, 0.99 @ step 300 vs ink ~0.51 at the identical regime |
| Production model | ~0.557 pixel AUC (warm-start accumulation, not fresh-trainable) |

---

## Task 1: Write the negative-results report (centerpiece)

**Files:**
- Create: `reports/ink_detection_64px_window_study_2026-06.md`

- [ ] **Step 1: Write the report** with these sections (prose; use the reference-numbers table above for every figure):

  1. **Title + one-line abstract** — e.g. "Is ink learnable at 0.5 mm? A reproducible study of the Vesuvius prize's hallucination window." Abstract: a fresh model memorizes ink patches trivially yet cannot learn ink from the full fragment at 64 px, while it fits a synthetic CT-derived target to 0.99 in the same regime — so direct supervised ink detection is learnability-limited by the 64 px window.
  2. **Question & why it is binding** — the 0.5 mm / ~64 px hallucination rule (no train/predict overlap; ≤64×64 @ 8µm) forbids large-context models; the 2023 GP-winning TimeSformer needs 256 px. So a prize-compliant detector must work at 64 px.
  3. **Method / rigor** — pooled pixel AUC as the honest metric (vs artifact-saturated Dice/`val_bpb`, where a near-constant predictor scores Dice ≈ 0.75); leak-free spatial splits (Fr143 into disjoint U/V regions with a 128 px buffer, no patch overlap); fresh-init controls (best_model moved aside, no warm-start leakage); the gated `eval_every_steps` learning-curve hook.
  4. **Evidence chain** — one short paragraph per row of the reference table, each stating the number and what it rules out (data, compute, capacity, pipeline, augmentation, optimization). End with the decisive brightness control.
  5. **Verdict & honest scope** — at 64 px, ink is not a learnable function of the CT patch *for direct supervised detection with this preprocessing*. Explicitly NOT a claim that no representation/preprocessing/segmentation could recover it; note the production ~0.557 is warm-start accumulation, not fresh-trainable signal.
  6. **Reproduce** — exact commands:
     ```bash
     # capacity/pipeline: can it memorize a tiny set? (expect ~1.0)
     PYTHONPATH=. python scripts/overfit_probe.py --target real --k 16 --steps 2000
     # same-regime control: regime fits a learnable target? (expect ~0.99)
     PYTHONPATH=. python scripts/control_fulldata_probe.py --steps 300 --eval-every 50
     # leak-free spatial split used for the held-out region
     PYTHONPATH=. python scripts/spatial_split_mask.py --mask local_data/PHercParis2Fr143/mask.png \
       --out-u /tmp/u.png --out-v /tmp/v.png --axis 1 --fraction 0.5 --buffer 128
     ```
     Note pooled pixel AUC is computed by `scripts/pixel_auc.py`; the learning-curve hook is `eval_every_steps` in `scripts/training/train.py`.
  7. **Links** — FINDINGS.md, the repo, the tool scripts.

- [ ] **Step 2: Self-check the report**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
# no AI-authorship markers
grep -niE "generated with|claude|co-authored|as an ai|language model" reports/ink_detection_64px_window_study_2026-06.md && echo "FOUND MARKER — REMOVE" || echo "clean"
# the scripts it references exist
for f in scripts/overfit_probe.py scripts/control_fulldata_probe.py scripts/spatial_split_mask.py scripts/pixel_auc.py; do test -f $f && echo "ok $f" || echo "MISSING $f"; done
```
Expected: `clean`; all four `ok`. Eyeball that every number matches the reference table.

- [ ] **Step 3: Commit**

```bash
git add reports/ink_detection_64px_window_study_2026-06.md
git commit -m "docs(report): 64px-window ink-detection learnability study"
```

---

## Task 2: Refresh the filing draft

**Files:**
- Modify: `docs/PRIZE_FILING_DRAFT_2026-06.md`

- [ ] **Step 1: Rewrite the "Findings (the methodological contribution)" section**

Make the window-limited study the lead bullet and link the new report. Replace the existing third bullet ("Honest negative results … TimeSformer …") and add the window-limited result as the headline. Keep the artifact-saturated-metrics bullet and the bugs-found bullet (still valid). The new lead bullet states: a fresh model memorizes 16 ink patches to AUC 1.0 but cannot learn ink from the full fragment at 64 px (flat ~0.51), while the identical regime fits a synthetic CT-derived target to 0.99 — so direct supervised ink detection is learnability-limited by the 64 px window; full study at `reports/ink_detection_64px_window_study_2026-06.md`.

- [ ] **Step 2: Rewrite the "Honest current results" section**

Replace the "mediocre but improving / cross-scroll transfer is the stated research target" paragraph with: the honest verdict that direct detection at 0.5 mm is learnability-limited (pooled pixel AUC ~0.49–0.52 on held-out data, the artifact-free metric); the production model's ~0.557 reflects warm-start accumulation across loop cycles, not a fresh-trainable signal; the contribution is the tooling + the rigorous, reproducible negative result, not a state-of-the-art detector.

- [ ] **Step 3: Add the probe/eval tooling to "What is being released (open tools)"**

Add a 5th tool entry: the evaluation/diagnosis suite — pooled pixel-AUC measurement (`scripts/pixel_auc.py`), the overfit/feasibility probe (`scripts/overfit_probe.py`), the same-regime control (`scripts/control_fulldata_probe.py`), the gated learning-curve hook (`eval_every_steps` in train.py), and leak-free spatial-split tooling (`scripts/spatial_split_mask.py`) — the instruments behind the methodological finding.

- [ ] **Step 4: Update the internal note + Links**

Keep the internal filing note (refresh numbers at file time; no AI markers; don't present closed PRs as merged). Add the report to the Links list. Update the note's "numbers as of 2026-06-11" to reference the committed FINDINGS as the current source.

- [ ] **Step 5: Self-check + commit**

```bash
grep -niE "generated with|claude|co-authored|as an ai|language model" docs/PRIZE_FILING_DRAFT_2026-06.md && echo "MARKER — REMOVE" || echo "clean"
grep -niE "mediocre but improving|stated research target" docs/PRIZE_FILING_DRAFT_2026-06.md && echo "STALE FRAMING REMAINS — fix" || echo "stale framing gone"
git add docs/PRIZE_FILING_DRAFT_2026-06.md
git commit -m "docs(filing): refresh June draft - window-limited finding as headline"
```
Expected: `clean`; `stale framing gone`.

---

## Task 3: Refresh the Discord post draft

**Files:**
- Modify: `docs/DISCORD_POST_DRAFT_2026-06.md`

The current draft is built around villa PR #1033, which was closed — it must be reframed. The new post is about the finding + the public tools (no open-PR claim, no prize mention, no AI markers).

- [ ] **Step 1: Rewrite the draft**

- Status line: drop the "PR #1033 is open" framing; state the repo is public (MIT) and the post invites replication/discussion of the 64 px learnability result. Primary channel `#code`.
- Post body (copy-paste block): short and technical — the question (can ink be learned at the 0.5 mm prize window?), the decisive observation (a fresh model memorizes 16 ink patches to AUC 1.0 and fits a synthetic CT-derived target to 0.99 in the production regime, yet stalls at ~0.51 on real ink at 64 px), the link to the study and the repo, and a specific ask: replication on other fragments / counter-examples / whether anyone gets above-chance pooled pixel AUC at strict 64 px. The GPU fiber tool stays mentioned as a reusable public artifact (not an open PR).
- Follow-through checklist: keep the "Jon posts", "check replies after 24h", "log in community_signal" items; remove the PR-specific gating.

- [ ] **Step 2: Self-check + commit**

```bash
grep -niE "generated with|claude|co-authored|as an ai|language model" docs/DISCORD_POST_DRAFT_2026-06.md && echo "MARKER — REMOVE" || echo "clean"
grep -niE "PR is open|pull/1033.*open|fresh current-main PR is open" docs/DISCORD_POST_DRAFT_2026-06.md && echo "STALE PR CLAIM — fix" || echo "no stale open-PR claim"
git add docs/DISCORD_POST_DRAFT_2026-06.md
git commit -m "docs(discord): reframe June post around the 64px finding + public tools"
```
Expected: `clean`; `no stale open-PR claim`.

---

## Task 4: Link the report from README + FINDINGS

**Files:**
- Modify: `README.md`, `FINDINGS.md`

- [ ] **Step 1: Add the report link to README**

In the README's "Honest results, methodology, and negative results" callout (the line near the top linking FINDINGS.md) and/or the "Evidence & upstream contributions" section, add a link: the 64 px window learnability study at `reports/ink_detection_64px_window_study_2026-06.md`. One sentence describing it.

- [ ] **Step 2: Add a pointer from FINDINGS.md**

At the end of the window-limited verdict bullet (the one ending "…`scripts/control_fulldata_probe.py`.)"), append: "Full standalone study: [reports/ink_detection_64px_window_study_2026-06.md](reports/ink_detection_64px_window_study_2026-06.md)."

- [ ] **Step 3: Self-check + commit**

```bash
grep -c "ink_detection_64px_window_study_2026-06.md" README.md FINDINGS.md
git add README.md FINDINGS.md
git commit -m "docs: link the 64px window study from README and FINDINGS"
```
Expected: each file shows ≥1.

---

## Task 5: Final consistency sweep + push

- [ ] **Step 1: Sweep all four outward docs for AI markers + number consistency**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
grep -rniE "generated with|🤖|co-authored-by:.*claude|as an ai language model" \
  reports/ink_detection_64px_window_study_2026-06.md docs/PRIZE_FILING_DRAFT_2026-06.md docs/DISCORD_POST_DRAFT_2026-06.md && echo "MARKER FOUND" || echo "all clean"
# spot-check the headline numbers appear consistently
grep -l "0.99" reports/ink_detection_64px_window_study_2026-06.md docs/PRIZE_FILING_DRAFT_2026-06.md
```
Expected: `all clean`; the control number present in both report and filing draft.

- [ ] **Step 2: Push**

```bash
git push origin main
```

- [ ] **Step 3: Hand off filing/posting to the user**

These are DRAFTS. The user files via the official form (~June 24-28, after a final numbers refresh) and posts to Discord. Do not file or post. Report the four documents are ready for review.

---

## Self-Review

**Spec coverage:**
- Negative-results report (centerpiece, full section spec + reproduce) → Task 1. ✓
- Filing-draft refresh: Findings + Honest results + open-tools + links/note → Task 2. ✓
- Discord post reframe (finding + tools, no open-PR claim) → Task 3. ✓
- Light repo consistency (README + FINDINGS links) → Task 4. ✓
- Constraints (no AI markers, numbers trace to committed results, don't present closed PRs as merged, user files) → global constraints + per-task self-checks + Task 5. ✓

**Placeholder scan:** None. Prose content is specified by section with the exact numbers to cite (reference table) and exact reproduce commands; the writing itself is the execution. No "TBD".

**Type/consistency:** The reference-numbers table is the single source cited across the report (Task 1), filing draft (Task 2), and Discord post (Task 3) — the same figures (0.99 control, ~0.51 ink, flat 0.508–0.525, 1.0 overfit) appear consistently; script paths referenced in reproduce blocks (`overfit_probe.py`, `control_fulldata_probe.py`, `spatial_split_mask.py`, `pixel_auc.py`) all exist (verified in Task 1 Step 2).
