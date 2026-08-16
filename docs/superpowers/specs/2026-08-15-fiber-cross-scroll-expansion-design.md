# Fiber cross-scroll expansion: n=1 → n=6, with size classes enforced in code

**Date:** 2026-08-15
**Status:** design, awaiting review
**Repos:** builds in `vesuvius-autoresearch`, ships to `../scrollgt` (public)

## Problem

ScrollGT reports cross-scroll fiber transfer from **one** Scroll-5 cube
(`s5_03997_01497_03997_256`) while **five** hand-traced Scroll-5 cubes sit unused in
`local_data/fiber_skeletons/`. An axis with n=1 cannot separate tracer quality from cube
idiosyncrasy — which is precisely the limitation
[`gt_training_data_exhaustion_2026-08-15.md`](../../../reports/detector/gt_training_data_exhaustion_2026-08-15.md)
disclosed for the pixel family today. Here it is undisclosed, and unlike the pixel family it
is **not capped**: the data is already on disk.

Discovered in the same investigation: the **column family is also n=1**
(`pherc1667_merged_columns` is the only column target) and that is likewise undisclosed.

## Inventory (measured 2026-08-15)

11 cubes local, 6 shipped:

| cube | size | shipped | `fiberprob.npy` |
|---|---|---|---|
| `s1_00497_01497_03997_256` … `s1_10997_02997_02997_256` (5 cubes) | 256³ | yes | yes |
| `s5_03997_01497_03997_256` | 256³ | yes (the sole cross-scroll target) | yes |
| `s5_06494_01994_03994_512` | 512³ | **no** | **yes** |
| `s5_06994_00994_04994_512` | 512³ | **no** | no |
| `s5_07994_01994_05494_512` | 512³ | **no** | no |
| `s5_07997_02997_05497_256` | 256³ | **no** | no |
| `s5_14997_01497_01497_256` | 256³ | **no** | no |

## Constraints established by reading the code

- **The target mask is model output, not annotation.** `meta.json` records
  `model: scrollprize/fiber_hz_vt (Apache-2.0), threshold 0.5`, and
  `scripts/export_fiber_targets.py:87` **requires** `{stem}_fiberprob.npy`, hard-failing on
  shape mismatch. Four of the five cubes lack it.
- **We generate that file ourselves.** `vesuvius_autoresearch/fibers/bench_cli.py::_fiber_prob`
  runs `fiber_hz_vt` and caches to `{cube}_fiberprob.npy`. The shipped six were produced this
  way, which the current metadata does not say.
- **The exporter is already size-agnostic.** `size_from_stem` parses the size out of the cube
  name and `shape = (size, size, size)`; the line-90 check is a consistency guard, not a 256
  assumption. No change needed for 512³ there.
- **The split logic hardcodes n=1.** `CROSS_SCROLL_SPLIT` is a single stem and
  `split = "cross_scroll" if stem == CROSS_SCROLL_SPLIT else "primary"`
  (`export_fiber_targets.py:32,130`). Running five more Scroll-5 cubes through it would label
  them `primary` — cross-scroll cubes marked same-scroll, corrupting the axis being expanded.
- **ERL is a length statistic and does not compare across cube sizes.**
  `eval_trace.py:222`, `_erl(runs) = Σr²/Σr`, in voxels. A 512³ cube admits fibers up to twice
  as long per axis, so its ERL is systematically larger for geometric reasons. The oracle
  scores 258.27 on `s1_00497_01497_03997_256`; on a 512³ cube it will be materially higher.
  Reporting both sizes in one undifferentiated table would let a tracer look better on a big
  cube than a better tracer on a small one.

## Design

### 1. Size class as a first-class field, enforced in code

Each target's `meta.json` gains `size_class` (the integer cube edge, `256` or `512`).

`scrollgt score-fibers` then:
- **refuses to aggregate ERL or ERLpen across size classes** — an explicit error, not a
  silent mean;
- **always prints the cube's own class oracle ERL** beside any score, so a number is only
  ever read against its own ceiling.

This mirrors the existing rule that `score-fibers` never prints one ERL without the other,
and it is pinned in `tests/test_fiber_gaming.py` rather than documented in prose. The lesson
from the 2026-08-14 claim-vs-test audit is that this project's failures were never in metric
code — they were properties asserted once and never re-checked, so the invariant belongs in
CI.

### 2. Split becomes a predicate

`CROSS_SCROLL_SPLIT` (single stem) is replaced by a scroll-derived rule: any `s5_*` cube is
`cross_scroll`, any `s1_*` cube is `primary`. A test pins that every shipped Scroll-5 cube
carries `cross_scroll`, so the n=1 assumption cannot silently return.

### 3. Generate the four missing probability volumes

Run the existing `_fiber_prob` path for the four cubes lacking it. Provenance in each new
target's `meta.json` must state that the probability volume was generated locally with
`fiber_hz_vt` at threshold 0.5, on what date — and the same statement is **backfilled to the
six existing targets**, which are locally generated but do not say so.

### 4. Floors and oracle per new cube

Compute the full floor set (connected components, one-instance, per-voxel, 50-random) and the
oracle for each new cube, since the ceiling is class-dependent and the floors are what make a
score readable.

### 5. Documentation

- `baselines/BASELINES.md`: "Six 256³ cubes" is wrong on both counts after this. Replace with
  the per-class tables and state the cross-class rule.
- `README.md`: fiber family description.
- **Column n=1 disclosure**: one paragraph stating the column family has a single target, as
  the pixel family disclosure already does. Found in this investigation; shipping the fiber
  fix while silently knowing about the column gap would repeat the failure this repo spent
  2026-08-15 correcting.

## Non-goals

- **Re-running our tracer on the new cubes.** It already loses to connected components on all
  six; five more losses is not the point of this work, and the floors are what make the new
  targets usable by others.
- **Any change to the column family beyond the disclosure paragraph.** A second column target
  is a separate project with its own registration risk.
- **Changing the metric.** ERL's size dependence is a property of the statistic, not a defect
  to fix; the design contains it rather than redefining it.

## Verification

- Every new target loads and scores through the shipped `scrollgt score-fibers` path with no
  network and no GPU, matching the existing targets' guarantee.
- A test asserts cross-class aggregation raises, and that each scorecard carries its class
  oracle.
- A test asserts every `s5_*` target is labelled `cross_scroll`.
- ScrollGT's existing suite passes unchanged.
- The oracle ERL for a 512³ cube is confirmed to exceed the 256³ oracle, which is the
  empirical check that the size-class rule was needed rather than assumed.

## Risks

- **512³ inference is 8× the volume** and may not fit the existing patch-based path without
  adjustment. If it does not, the honest fallback is shipping the two 256³ cubes (cross-scroll
  1 → 3) and stating in BASELINES that the three 512³ cubes are pending and why — never
  dropping them silently.
- **Locally generated masks are a provenance claim.** Whatever `fiber_hz_vt` weights and
  inference settings are used must be recorded, and if they cannot be pinned exactly, that
  uncertainty is disclosed rather than implied away.
- **The new cubes' annotation quality is unmeasured.** The exporter records
  `measured_node_landing_rate_on_semantic_label`; if any new cube lands materially worse than
  the shipped six, it is disclosed on the target rather than quietly averaged in.
