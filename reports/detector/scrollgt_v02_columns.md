# ScrollGT v0.2: the PHerc-1667 column-level target — SHIPPED

Path (a) of the v0.2 groundwork ([scrollgt_v02_groundwork.md](scrollgt_v02_groundwork.md))
is done ahead of schedule: ScrollGT now ships its **first non-training-scroll target**,
`data/pherc1667_merged_columns` (scrollgt commits ba30f4e..93a0b94, 2026-07-18).

## What shipped

- **Target package**: the 22 reading columns registered onto the merged full-reading
  geometry ([registration](merged1667_column_registration.md): 3-strip independent
  transform agreement, 3-px tiling closure), per-column text bands
  ([bboxes](merged1667_column_bboxes.json)), scholar-validated transcription status
  ([transcription](merged1667_column_transcription.json): Coll. 1–4 traces, 5–22 text,
  eight papyrologists' consensus, CC BY-NC 4.0), and the bilevel valid mask — 104 KB
  total in-repo.
- **`scrollgt score-columns`**: a new granularity-honest scoring contract. No pixel GT
  exists on this scroll, so the scorer measures *consistency with the published reading*:
  `col_gutter_auc` (region-level — signal concentrated in text columns vs inter-column
  gutters), `col_gutter_pixel_auc`, and `line_period_peak_mean` (text-line periodicity
  inside columns, pitch range declared in target meta). Partial-extent predictions are
  supported via `--origin` (columns/gutters outside the extent are skipped and listed).
  Gutters adjacent to the two cross-strip-flagged columns are excluded and counted.
  6 new tests (21 total in scrollgt), TDD.
- **Measured anti-gaming floor** (published in scrollgt BASELINES): constant **and
  papyrus-mask-copy** predictions score exactly 0.5 — the gutters are papyrus too, by
  design, so "predict the sheet" buys nothing. Uniform noise shows the region-AUC
  granularity (0.578 at n = 18 text cols vs 17 gutters — honest ±0.08). The disclosed
  geometry-oracle ceiling is 1.0 with periodicity 0.0 (independent axes).

## Honesty design notes

- Column-level scores are **necessary-not-sufficient**: the column layout is public, so
  a high `col_gutter_auc` alone proves layout-consistency, not reading. Submissions must
  include the prediction map for visual review (stated in BASELINES), and the score's
  meaning is stated in the target's meta.json `honesty_notes`.
- The renderer prerequisite is disclosed in the target meta with its validation status
  (clean-triple NCC 0.7799 gate-PASS on this very scroll,
  [render_validation_1667.md](render_validation_1667.md)).
- Model exposure: no distilled arm trained on any PHerc-1667 data (the target is
  held-out at column level for every model in scrollgt's baselines); the core team's own
  pipeline trained on this scroll — external submissions must disclose 1667 exposure.

## In flight

Model baseline rows (arm C, legacy detector) over a rendered cols-17–19 region
(grid y=100 x=20800, 1710×3990; render running via the rectangular `--region Y0 X0 H W`
CLI extension). Runner: `repro/sota_data/columns_baseline.py`. Honest expectation given
every prior cross-scroll result: arm C should sit near the floor — that expectation is
itself the point of publishing the row.
