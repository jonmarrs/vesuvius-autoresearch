# ScrollGT v0.2 groundwork — open-bucket survey 2026-07-17

Question: can ScrollGT v0.2 extend to Scrolls 2–3 in August, as the Q3 strategy assumed?
Answer: **no — not as scoped.** Fresh anonymous-S3 survey of `s3://vesuvius-challenge-open-data/`
(2026-07-17) shows what each candidate scroll actually ships, and it redirects v0.2.

## Survey results

| scroll | prefix | segments | surface volumes | ink content | human GT |
|---|---|---|---|---|---|
| Scroll 2 | `PHercParis3/` | **none** (volume + photo only) | — | — | — |
| Scroll 3 | `PHerc0332/` | 2, both **mesh-only** | none (ours are the only independent ones) | scroll-level *segmentation* surface predictions only (`representations/predictions/surfaces/`, m7-L2) — no ink maps | none |
| PHerc 1667 | `PHerc1667/` | **20** | 19 of 20 | 19 segments carry `ink-detection/` **model predictions** (incl. a 2026-07-09 high-res `mrg20736-1um` run and a `new_canon_autoresearch_recipe` run) | none in bucket |

Notes:
- The 20th PHerc-1667 segment (`20260612121456-w011_..._merged_v4_flatboi_straightened_v4`,
  dated 2026-06-12) is **mesh-only** — almost certainly the merged geometry behind the
  2026-06-25 full reading, and a direct target for our surface renderer.
- Every `ink-detection/` file on 1667 is a model output (filenames encode recipe, tile,
  stride). Registering *those* as ScrollGT targets would recreate exactly the
  reproduce-the-teacher trap ScrollGT exists to break. Not eligible as GT.

## What this means for v0.2

1. **Scroll 2 is impossible today** — there is nothing to register against (no segments,
   no meshes, no flattened geometry).
2. **Scroll 3 has no label source** — the scroll is unread; that gap is why First Letters
   is open. The renderer (not the benchmark) remains our Scroll-3 contribution.
3. **PHerc 1667 is the real v0.2 lead.** The scroll was read in full (announced
   2026-06-25), so a *scholar-validated reading* now exists in the literature even though
   the bucket ships no labels. Two concrete paths, in order of cost:
   - **(a) Transcription-level GT:** align the published column/line reading to segment
     coordinates and score at character/line granularity (region-level presence/absence
     rather than pixel maps). Coarser than the Scroll-1 targets but genuinely
     human-validated, and it would give ScrollGT its first non-training-scroll target —
     unlocking the clean cross-scroll domain-ceiling measurement that is currently blocked.
   - **(b) Renderer on the merged segment:** render
     `20260612121456-w011_..._straightened_v4` with `render_cli.py` (same one-command path
     as Scroll 3) to produce the independent surface volume the reading geometry lacks in
     the bucket. Useful on its own and a prerequisite for (a) if the published reading is
     keyed to the merged flattening.
4. **More Scroll-1 targets remain the cheap wins** — three gate-passing regions were
   withheld at v0.1.1 only for lack of independent orientation validation; any new
   validation route (e.g. a second enrichment-informative canon segment, or the
   text-line-periodicity gate hardened further) converts them directly into targets.

## Decision

v0.2 (August) re-scoped: **PHerc-1667 path (b) then (a), plus withheld-target conversion.**
"Scrolls 2–3" is dropped from the v0.2 label; the July filing draft and the strategy doc
now say this. Re-survey the bucket before starting — a labels drop for 1667 (the core team
has released aligned GT before, for Scroll 1) would collapse path (a) from
transcription-alignment work into the existing `gt_register.py` flow.
