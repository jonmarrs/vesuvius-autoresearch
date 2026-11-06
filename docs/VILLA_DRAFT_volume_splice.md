# Draft: fiber volume tracing keeps overlaps "for joining", but nothing joins them

**NOT POSTED.** Prepared 2026-11-06 from [finding 105](../reports/neural_tracer_link_splice.md) and its polyline check.
Whether to post, and in what form, is the owner's decision.

**Recommended form: an issue first, not a PR.** The change adds a step villa does not have, and villa rarely
merges outside features; its fixes to its own defects do merge. The issue reports the gap and the measurement, and
offers the tool. A PR follows only if a maintainer wants it.

## Before posting

1. **The owner decides,** and writes the motivation paragraph below. Never tick the verification box for them.
2. **villa's posting limits:** at most one new issue or PR a week, and at most three open PRs.
3. **Re-check villa main of that day.** The tracer must still keep the overlaps and record the links
   (`tracing/volume.py`: `_write`, `save_tile`), and nothing may join them yet. Search the issues and PRs for "join",
   "splice" and "links" (checked 2026-11-06 at `eab6108b9`: only #2434, which joins AFV splines from a different
   generator).
4. **For a PR, not for the issue:** run the splice on a volume-tracer run of an open-data volume, so villa's
   `fibers.vcobj` export and VC3D can read the result. All of this repository's runs are local CT crops, which the
   exporter cannot bind to a volume (`docs/VILLA_OBJECT_STORE_EXPORT_CHECK.md`). That needs a GPU run and villa-main
   native builds, both the owner's.
5. **No AI-authorship markers** in the issue, commit or body, including `Co-Authored-By`.

---

**Title:** `fiber volume: the pieces it writes with overlaps "for joining" are never joined`

**In one sentence:** `tracing.volume` cuts a trace where it runs along a fiber already written, keeps `--overlap` points
"for joining", and records which fibers each piece's ends touch, but nothing in villa joins the pieces. Splicing
them by those links makes the traced fibers markedly longer, with no more merges.

**What happens now:** each written piece stays a separate fiber in the tiles, the fiber JSONs and `fibers.vcobj`. The
module docstring says the overlaps are kept for joining, and `links` lets "overlapping pieces of one fiber ... be
joined later". No villa code reads `links` to do that.

**A rule that joins them:**
* Splice a piece to the linked fiber whose end it overlaps. Its end must lie within `--overlap` trace-grid voxels of
  arclength of that fiber's nearer end, and head into it.
* Take splices nearest first, each fiber end at most once, never closing a ring, so every chain of pieces is one
  polyline.
* Along a chain, drop the next piece's points beside the previous piece's kept overlap.

It uses only what the tracer already writes.

**Measurement:** villa `ccb431818`'s volume tracer, `scrollprize/fiber_single_small` at its defaults, on ScrollGT's
fiber cubes. Scores are ScrollGT's fiber scorer (version 3), against each cube's hand-traced fibers. The rule was
registered before the ten cubes below were scored. Merge-penalized ERL, before → after:

| cube | splices | ERLpen τ = 4 | ERLpen τ = 2 | merges τ = 2 | coverage τ = 2 |
|---|---|---|---|---|---|
| s3_00994_00494_01994_512 | 722 | 105.33 → 139.66 | 34.65 → 36.93 | 180 → 192 | 0.643 → 0.641 |
| s3_00994_01994_00494_512 | 728 | 96.38 → 132.61 | 42.08 → 45.69 | 219 → 218 | 0.649 → 0.648 |
| s3_00994_02494_01494_512 | 715 | 80.76 → 96.37 | 29.60 → 30.63 | 257 → 257 | 0.571 → 0.569 |
| s3_01994_01494_00994_512 | 511 | 83.55 → 124.23 | 32.12 → 37.88 | 114 → 116 | 0.578 → 0.577 |
| s3_01994_01994_01494_512 | 493 | 77.78 → 98.00 | 32.06 → 33.10 | 187 → 192 | 0.597 → 0.595 |
| s3_02994_02494_01994_512 | 780 | 108.20 → 149.85 | 41.50 → 49.13 | 169 → 173 | 0.674 → 0.673 |
| s3_03494_01494_00494_512 | 748 | 89.33 → 117.96 | 35.03 → 38.81 | 300 → 290 | 0.611 → 0.609 |
| s3_04494_00994_01494_512 | 720 | 77.71 → 93.40 | 26.25 → 26.74 | 260 → 263 | 0.623 → 0.621 |
| s5_13497_01497_02497_256 | 43 | 25.07 → 27.74 | 11.41 → 11.88 | 24 → 27 | 0.333 → 0.332 |
| s5_16997_03997_04497_256 | 44 | 21.80 → 23.82 | 9.87 → 10.27 | 30 → 29 | 0.268 → 0.267 |

What to look at:
* **ERLpen rises on every cube at both tolerances.** The median is +29% at tolerance 4, but only +5.3% at tolerance 2.
  There, runs also break where a trace strays more than 2 voxels beside the fiber it follows, which joining cannot
  mend.
* **Merges barely move:** 1,740 → 1,757 summed at tolerance 2. 1.7% of the splices whose pieces both touch the hand
  tracing join two different hand-traced fibers.
* **Example cube:** on `s3_02994_02494_01994_512`, 780 splices turn 1,774 pieces into 994 fibers.

**Why / where this is useful:** [The owner's own words: what we were doing with the tracer, and why longer fibers
matter to someone building on its output.]

- [ ] I personally verified that the measurement above was produced by this rule on the stated data.

## Details (for the issue's reader)

* **Limits:**
  * One tracer version (`ccb431818`, before #2359 and #2440), one checkpoint and its default settings.
  * Ten cubes, eight from Scroll 3.
  * The rule was developed on eleven other cubes of the same runs.
  * ERLpen against one hand tracing per cube stands in for reviewed continuity.
* **Not yet shown:** that villa's `fibers.vcobj` export carries the spliced fibers, and that VC3D reads them.
* **Records:** https://github.com/jonmarrs/vesuvius-autoresearch:
  * the tool: `scripts/neural_tracer_splice.py`;
  * the registration: `docs/preregistration/2026-11-05_neural_tracer_link_splice.md`;
  * the report: `reports/neural_tracer_link_splice.md`;
  * the polyline record: `reports/evidence/neural_tracer_splice_polylines_2026-11-06.json`.
