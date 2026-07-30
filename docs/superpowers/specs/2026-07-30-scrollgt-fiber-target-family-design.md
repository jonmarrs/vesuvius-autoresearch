# ScrollGT fiber connectivity target family

**Date:** 2026-07-30
**Status:** approved, ready for planning
**Repos touched:** `scrollgt` (primary), `vesuvius-autoresearch` (doc correction only)

## Problem

villa's 2026 open-problems post asks for a way to "identify and separate long fibers with the
right connectivity", and states the preference explicitly: *"a tracer that confidently follows
fewer fibers correctly is more useful than one that follows more fibers with a higher error
rate."*

Work in `vesuvius-autoresearch` built the measurement layer for that problem and produced one
result that is useful to anyone entering the lane, independent of any tracer:

**Coverage and precision cannot rank a fiber tracer.** Five completely different instance
labellings — connected components, one instance for everything, one instance per voxel, 50 random
labels, and our tracer — all score identical coverage and precision, because those metrics are
properties of the shared fiber *mask*, not of the *labelling*. Raw ERL alone is also gameable:
labelling everything as a single instance scores near-oracle while its merge-penalized ERL is
exactly 0.00. **Both ERL and the merge count are required.**

Two scales exist in the current evidence and must not be mixed:

| | 128³ sub-volume (22 fibers) | full 256³ cube (87 fibers) |
| --- | --- | --- |
| shared coverage / precision | 0.960 / 0.229 | 0.9177 / 0.2194 |
| oracle ERL | 127.69 | 258.27 |
| single-instance ERL / ERLpen | 111.49 / **0.00** | 199.18 / **0.00** |
| floors measured | all four | two (single-instance, connected components) |

The finding holds at both scales, but the five-labelling table exists only at 128³. Since the
shipped targets are full 256³ cubes, **all four floors must be re-run at full-cube scale** before
publication, so every number in the README, the scorecards, and the baselines sits on one scale.
This is a prerequisite task, not a nice-to-have: publishing a headline measured at one scale
beside baselines measured at another is the exact defect being corrected below.

That finding currently sits inside a research monorepo, where nobody entering the fiber lane will
find or install it. The July Progress Prize filing scored zero on community use. Packaging this as
a usable benchmark is the August lever.

## Approach

Ship it as a second **target family** inside ScrollGT rather than a new standalone repo.

ScrollGT's existing thesis — human ground truth, gaming-resistant scoring, negatives published on
its own authors — is exactly the shape of this contribution. The fiber ground truth is hand-traced
NML from villa's public `fiber-skeletons` dataset; the floors are anti-gaming controls; our own
tracer ships as a published loss. One repo means one CI, one villa listing, and one adoption story,
which is what the scored-zero criterion needs.

ScrollGT becomes a benchmark *suite*: ink pixel targets, PHerc-1667 column targets, and now fiber
connectivity targets.

## Scope: what crosses the boundary

**Moves into `scrollgt`:**

- `eval_trace.py` — ERL, merge-penalized ERL, splits, merges, and the four floors.
- `skeleton_io.py` — NML → per-fiber graphs, including the coordinate-convention handling.

**Stays in `vesuvius-autoresearch`:**

- `trace.py` (the baseline tracer) and `semantic.py` (`fiber_hz_vt` inference), plus `detection.py`
  and the existing `bench_cli.py`.

The boundary is deliberate: these are the benchmark's *entrant*, not part of the benchmark. Keeping
them out is what holds ScrollGT to a lean install with no torch and no GPU.

### Dependency impact

`eval_trace.py` requires `scipy.ndimage` (`distance_transform_edt`, `label`,
`generate_binary_structure`). `scipy` therefore becomes an **explicit** dependency of ScrollGT.

This costs nothing at install time: ScrollGT already depends on `scikit-learn>=1.4`, which requires
scipy transitively. The declared dependency set goes from
`numpy, scikit-learn, pillow` to `numpy, scipy, scikit-learn, pillow`, and the resolved
environment is unchanged. **No torch, no GPU, no model download** on any code path.

## Data

Six cube targets, one directory each under `data/fibers_<cube>/`:

| cube | GT fibers |
| --- | --- |
| s1_00497_01497_03997_256 | 87 |
| s1_00497_02497_02997_256 | 109 |
| s1_00997_02497_02997_256 | 128 |
| s1_08997_02997_02497_256 | 105 |
| s1_10997_02997_02997_256 | 91 |
| s5_03997_01497_03997_256 | 68 |

Each directory ships:

- **`skeleton.npz`** — the GT fibers pre-extracted from NML (per-fiber node coordinates in
  `(z, y, x)` and edge arrays), so no NML parsing or download is needed to score.
- **`mask.npz`** — the reference fiber mask, `P(fiber) >= 0.5` from `scrollprize/fiber_hz_vt`,
  stored via `np.packbits`. Measured at **252 KB** per cube (mask density 6.0%); ~1.5 MB for all
  six. ScrollGT's data directory roughly doubles, from ~2 MB, and stays small.
- **`meta.json`** — following the existing target convention: source NML path on
  `dl.ash2txt.org/datasets/fiber-skeletons/`, cube origin, the model and threshold that produced
  the mask, tolerance, and voxel size (7.91 um).

Shipping the mask is what makes floors reproducible without a GPU. It also makes them *honest*:
every entrant is scored against the identical mask, so differences in the scorecard come from the
labelling rather than from a better or worse segmentation.

### Splits

The ground truth is a public villa dataset, so a hidden test set cannot be enforced and will not be
claimed. Instead `s5_03997_01497_03997_256` is **designated the cross-scroll reporting split** — a
labelled convention, since the other five cubes are Scroll 1. Scorecards report Scroll-1 cubes and
the Scroll-5 cube separately.

## Interface

```bash
scrollgt score-fibers <labels.npy> data/fibers_<cube> [--json-out card.json]
```

`labels.npy` is a cube-shaped int array: 0 = background, distinct id per predicted fiber instance.

Output mirrors the existing `scrollgt score` contract — a markdown scorecard row plus optional
JSON. Rules that the output must always honour:

- **Both ERL variants always print together**, never one alone, because raw ERL is gameable to
  within 13% of the oracle by labelling everything once.
- **Tolerance is part of every scorecard.** Ground truth is a ~1-voxel skeleton while any detector
  predicts full fiber thickness, so a number without its tolerance is meaningless.
- **Splits and merges are reported separately and never summed.** A split fails to help; a merge
  actively corrupts the U/V parameterization fibers are wanted for.
- The four floors print alongside any entry, and the card **flags `BELOW the naive baseline`** when
  the entry's raw ERL trails connected components.

## Baselines

`baselines/BASELINES.md` gains the six-cube table, in the house style of publishing our own
negatives:

| cube | tracer ERL | cc ERL | tracer ERLpen | cc ERLpen |
| --- | --- | --- | --- | --- |
| s1_00497_01497_03997 | 26.6 | 197.1 | 23.2 | 37.1 |
| s1_00497_02497_02997 | 45.8 | 207.5 | 33.6 | 64.3 |
| s1_00997_02497_02997 | 36.3 | 195.8 | 29.8 | 56.5 |
| s1_08997_02997_02497 | 34.1 | 186.5 | 30.8 | 106.1 |
| s1_10997_02997_02997 | 37.4 | 194.1 | 34.2 | 57.7 |
| s5_03997_01497_03997 (cross-scroll) | 31.5 | 182.2 | 25.4 | 51.1 |

**Connected components is a strong baseline that our tracer does not beat**, losing by 4.5-7.4x on
raw ERL and 1.6-3.5x on merge-penalized ERL, on every cube. Fragmentation is the cause: the tracer
finds the fibers (coverage 0.62-0.88) but cannot hold one identity along them.

## Correction to carry over

`docs/FIBER_TRACING.md` and `reports/fiber_connectivity_eval.md` in `vesuvius-autoresearch`
currently state that the tracer is "marginally ahead of connected components" on the
merge-penalized metric (24.27 vs 22.47). That held on a 128³ sub-volume and **does not survive at
full-cube scale**, where connected components wins on both metrics across all six cubes. Both
documents must be corrected as part of this work, and the packaged claim must be the stronger
negative.

## Testing

- Port the existing CPU fiber tests covering `eval_trace` and `skeleton_io` (84 tests currently run
  under `-k fiber`; the subset covering these two modules moves).
- Retain the coordinate-convention test that asserts in-bounds NML nodes land on the shipped
  semantic label at a rate of exactly 1.000 — this is what pins NML `x,y,z` against volume `z,y,x`
  and the origin encoded in the filename as `z_y_x`.
- **New:** a test asserting the published floors reproduce from shipped data alone, with no
  network and no GPU. This is the regression that keeps the zero-GPU path real; without it, a data
  packaging mistake would be silent.
- **New:** a gaming test asserting that the four floors produce identical coverage and precision
  but well-separated ERL — the finding itself, pinned as an executable claim.
- ScrollGT CI runs the suite on CPU.

## Prerequisite

Before any packaging work: re-run all four floors (single instance, connected components, one
instance per voxel, 50 random) on all six full 256³ cubes in `vesuvius-autoresearch`, and refresh
`reports/fiber_benchmark_all_cubes.json`. Everything published downstream — README headline,
scorecards, `BASELINES.md` — draws from that one full-cube run. No 128³ sub-volume number is
carried into ScrollGT.

## Out of scope

- Improving the tracer (seed NMS, `high_curvature` termination). Those remain open in
  `vesuvius-autoresearch`; this work ships the measurement layer and the honest baseline.
- PyPI publication. ScrollGT remains a source install, consistent with its current state.
- Any change to the existing ink pixel or column target families.

## Success criteria

1. `scrollgt score-fibers` scores a user labelling against any of the six cubes with no GPU, no
   model download, and no network access.
2. The published floors reproduce from shipped data, enforced by a test.
3. The gaming finding is stated in the README and pinned by a test.
4. Our tracer's loss to connected components is published in `baselines/BASELINES.md`.
5. The stale "marginally ahead" claim is corrected in both `vesuvius-autoresearch` documents.
6. Every published number derives from the single full-cube floor run; no 128³ sub-volume figure
   appears in ScrollGT.
