# PHerc 1667: the 22 reading columns located on the merged geometry — v0.2(a) step 1

The published full reading (Angelotti et al., CC BY-NC 4.0) transcribes **22 columns**
(Coll. 1–4 traces, Coll. 5–22 text), but no machine-readable column coordinates are in
the open bucket. This report derives them: the preprint's page-3 figure strips (the
ink-detection reading over the flattened surface, with labeled `col. N` brackets) are
registered onto the merged tifxyz geometry, and the bracket extents are mapped into
merged-grid coordinates.

**Artifact:** [merged1667_column_bboxes.json](merged1667_column_bboxes.json) — per-column
`gx0..gx1` on the merged grid (2061×30097, scale 0.05 → multiply by 20 for full-res
flattened px), transcription status, provenance, per-column flags.
**Overlay:** [merged1667_column_overlay.png](merged1667_column_overlay.png) — the boxes on
the merged valid mask; the "traces" columns sit exactly on the fragmentary scalloped
region, gutters land in the wrap-damage notches.

## Method

1. Extract the three page-3 strips from the preprint PDF (2110×475 each; together they
   tile cols 1–8 / 9–16 / 17–22).
2. Build papyrus masks (gray threshold, cyan annotations excluded) and register each
   strip to the merged tifxyz valid mask by template matching over a scale sweep
   (TM_CCOEFF_NORMED on the shape masks — the scalloped outline is the signal).
3. Detect the cyan bracket **line** band (rows 24–32; the labels sit above it, ticks
   below), close sub-bracket gaps, map intervals through each strip's transform, and
   merge cross-strip truncations in grid space.

## Registration quality (the reasons to believe it)

- All three strips **independently** recover the same scale (4.7 grid px / figure px)
  and the same vertical offset (gy0 = 19).
- The three strips tile the grid left-to-right with the **last strip's right edge landing
  3 px from the grid's true right edge (30094 vs 30097)** — an end-to-end closure over a
  30k-px strip that a wrong scale or offset could not produce.
- Match scores 0.49/0.67/0.67 (lowest on the most fragmentary strip, as expected).
- Bracket extraction yields **exactly 22 columns** after merging the two cross-strip
  truncation pairs (cols 9 and 16 — flagged in the JSON, widths carry up to ~200 px of
  strip-crop slack; all other columns are single-strip).
- Column widths rise monotonically ~1050 → 1250 grid px from interior to exterior —
  physically expected (outer wraps have larger circumference), and not a property the
  extraction was told about.

## What this unlocks (ScrollGT v0.2 (a))

Each column is now a **candidate benchmark target region on canonical geometry**, with
scholar-validated GT at column granularity: text presence (Coll. 5–22 vs 1–4), and — with
further transcription parsing — line counts and per-line legibility. Combined with the
gate-validated renderer (NCC 0.78 on this scroll), the full target pipeline exists:
render any column region → score a model's output against what eight papyrologists say
is there. Residual work for v0.2: refine bboxes on the two flagged columns, add y-extents
per column (text band vs full sheet), parse per-column line structure from the preprint,
and design the column-level scoring contract.

License note: bracket coordinates derive from the preprint figures (CC BY-NC 4.0) —
attribution required, non-commercial; consistent with how ScrollGT ships third-party GT.

## Addendum 2026-07-19: measured line pitch — a third independent cross-check

Per-column ink row-profile autocorrelation of the figure strips (the reading itself)
gives the text-line pitch directly: well-preserved text columns cluster tightly at
**108–132 grid px (median 120)**, with the strongest periodicity on col 20 (autocorr
0.73) — whose estimated ~13 lines matches the transcription's attested 11 within the
span-estimate error. Fragmentary columns give unreliable pitches (low ink; one
half-harmonic artifact on col 10) — flagged as such. This is a third independent
consistency check on the registration (after transform agreement and tiling closure):
the registered geometry carries line structure at the pitch the transcription implies.

Shipped to ScrollGT (commit 0be6e09): per-column `measured_line_pitch` in columns.json,
and the scoring contract's `line_pitch_range` calibrated [60,220] → **[85,160]** with
provenance (floor re-measured; only noise periodicity moved, 0.068 → 0.062).

## Addendum 2026-07-19 (2): flagged cols 9/16 refined; local wobble measured

Local junction-window registration (strip-edge windows re-fit at fine x-step against the
merged mask, with control windows in shape-rich areas): the corrections (+47/−33 grid px
for col 9; +66/−94 for col 16) close the inter-strip gaps to <35 px and land both widths
on the neighbor trend (1095 and 1132 vs neighbors 1062–1189) — a consistency check the
refinement was not tuned for. The controls also measure the registration's **intrinsic
local wobble: ±40–90 grid px** (broad correlation plateaus), so the flagged columns'
uncertainty is now *measured* ±90 rather than *bounded* ±250; flags and scorer gutter
exclusions are retained (±90 is still comparable to gutter widths). Full-band baseline
rows re-scored against the refined target: every shift ≤0.007 (noise realization moved
0.578→0.585, legacy 0.595→0.592, arm C unchanged) — both models remain statistically at
the noise floor. Shipped in scrollgt commit bc2fe91.
