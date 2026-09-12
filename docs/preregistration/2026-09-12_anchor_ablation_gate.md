# Pre-registration: the gate that decides whether the anchor ablation can run

**Written 2026-09-12, before the pilot fit is launched.** This registers a
*feasibility gate*, not a study. It produces no finding about anchors and must never be reported as
one.

## The question the study would ask, and whose it is

villa's `scrollprize.org/docs/39_winding_annotations.md` says relative winding annotations "seem to
have a great impact on the spiral fit" and asks for automation. villa's open-problems page names the
bottleneck as "creating winding constraints that are precise and fast enough to use widely."

**Nobody tests that against recovered ink.** Every winding-constraint project in villa's catalogue —
winding-sync, winding-ruler, spiralcheck, FASP, axiosdevs' annotator — validates on geometry, and we
have now measured geometry and ink coming apart four times on the pinned tree.

The study would ablate **anchor count** (59 → 10 in `abs_winding.json`) on current villa, 3 seeds per
arm against the existing `curbase_s1..s3`, and report the effect on `total_fg_pixels`.

We already have the companion result: removing 5,413 **same-winding** (relative) constraints changes
reading by **+0.28%, 95% CI [−2.56%, +3.13%]**. The absolute anchors are a different, far smaller,
higher-leverage set, and are the ones villa asks people to draw by hand.

## Why a gate is needed at all

The ink strip is selected by winding **name** (w120–w129). `fit_spiral.py:1577`: "Absolute-winding
status is determined solely by the source file: only pcls loaded from `abs_winding.json` carry
absolute winding numbers." Thin the anchors and nothing guarantees that index 120 denotes the same
physical wrap.

**If numbering shifts, the two arms' strips are different papyrus and any ink difference between them
is uninterpretable.** This is not a caveat to disclose later; it voids the study.

The previous attempt to settle this used **median radius** and could not:
`calibrate_radius_to_winding.py` showed one winding sweeps ~1,683 vx of radius and overlaps its
neighbours entirely. It left the question at "~15 vx drift, too close to call", measured at 200 steps
on the superseded tree.

## The pilot

One fit: `spiral_out/fit_anchor10_pilot.sh` — 10 anchors, current villa, seed 1, 30,000 steps,
matched to `curbase_s1` in every other respect. **No render and no scoring**, because the gate is read
off the fitted meshes. Cost ~3h against the ~36h a full study would waste if the answer is bad.

Measured by `scripts/measure_winding_identity.py`, which matches windings by surface proximity and
reports an index offset. Its positive control is already on the record: two current baselines
differing only by RNG give **10/10 offset 0**, median self-distance **24.0 vx**, median margin to the
neighbouring winding **4.9 vx**.

## Decision rule, fixed now

| pilot outcome | decision |
|---|---|
| all 10 reference windings match at **offset 0** | **PROCEED** — register and run the 3-arm study |
| **any** offset ≠ 0 | **DO NOT RUN as designed.** A name-selected strip is not comparable between arms |

**Robustness condition, also fixed now:** the winner must beat the runner-up in at least **9 of 10**
windings by a positive margin. The instrument's own warning applies — the margin (4.9 vx) is smaller
than the seed-to-seed self-distance (24 vx), so no single row is comfortable and **10/10 agreeing is
the evidence, not any one match.** If offsets are 0 but the margin condition fails, the result is
**INCONCLUSIVE**, not a pass.

**Anchor count is fixed at 10 and will not be swept.** 10 is the strongest manipulation that earlier
work found still plausibly keeps numbering pinned, and drift was measured to plateau between 10 and
20. Trying several counts until one passes the gate is how a feasibility check becomes a search for a
favourable configuration.

## What the pilot cannot tell us

It is **one seed**. It establishes that numbering survives *in this fit*, not that it survives in
general. If the study runs, each ablated arm gets the same check, and **any arm that fails it is
excluded and reported as excluded** — not quietly dropped, and not used to reselect the anchor count.

It also says nothing about ink. The pilot is deliberately not rendered so that no ink number exists
to peek at before the study is registered.

## Prediction

**None on the ink endpoint** — that is the study's, not the pilot's.

On the gate itself I expect numbering to be preserved, on the reasoning that 10 anchors still pin the
index while the earlier 4.5× drift jump came from removing the loss entirely. Recorded so it can be
a miss, but note that **I have now been wrong on the direction of the last two registered geometry
predictions, in opposite directions**, so this expectation carries no weight and nothing downstream
depends on it.
