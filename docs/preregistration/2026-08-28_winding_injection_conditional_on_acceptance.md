# PRE-REGISTRATION: does a whole-winding injection survive *acceptance*?

**Committed UNRUN, 2026-08-28.** No fit has been run, no checkpoint exists, and no outcome has been
observed. Design and decision rule are fixed here before the instrument is capable of producing a
number.

## The gap this targets

Two results already exist and neither answers the operational question.

* **Ours (#1621, `reports/spiral_satisfaction_winding_blindness.md` §4).** Real traced windows,
  displaced by whole windings, scored by villa's unmodified function: max |Δ| exactly 0.0000, with
  half-winding controls moving 48% and 92% of windows. Invariance established.
* **@TAUIL-Abd-Elilah's (#1621, 2026-08-27).** Two real 5,000-step PHercParis4 checkpoints: the
  self-derived winding disagreed with the annotation by +8 and +6, and **the native strict metric
  rejected those patches anyway**, at 13.15% and 24.98% strict satisfied area.

Both measure geometry the metric was **already rejecting**. Our own report says only 21.7% of
extent-matched real windows were satisfied at the published dr (48.3% at a per-window best-fit dr),
and **0% of quad-matched windows at every dr tried**. An invariance that only holds on rejected
geometry costs nothing: the fit is thrown out either way.

The untested question, and the only one with consequences:

> **Among units the strict metric ACCEPTS in a real fit, does a whole-winding displacement keep them
> accepted?**

If yes, an accepted fit can carry a sheet switch. If no, the concern is closed and we should say so
publicly, having raised it.

The one existing datum pointing at "yes" is a single quad: seed 101's second fit had an anchor quad
native-strict-true while disagreeing by +5, inside a patch that still failed. One quad supports
nothing on its own.

## Design

**Population.** Units (quads, and separately patches) marked satisfied by the *unmodified* native
strict metric on a baseline fit of the reduced z-ROI. Selection uses only the baseline verdict,
never the outcome.

**Treatment.** Radial displacement about the umbilicus by `k * dr` at each unit's own fitted dr,
`k in {1, 2}`.

**Controls, which must be able to fail.**
* `k in {0.5, 1.5}` must flip accepted units to rejected. This is the harness check.
* `k = 0` must leave verdicts identical. This is the plumbing check: any change here means the
  injection path itself perturbs geometry and the run is void.

**Outcome.** `retained` = fraction of baseline-satisfied units still satisfied after injection.

## Decision rule, fixed in advance

Let `N` be the number of baseline-satisfied units.

1. **Powered?** If `N < 30`, declare the study **UNPOWERED** and report `N`. Do not report
   `retained` as a ratio over a denominator that small. Our own §4 numbers make this a live outcome,
   not a formality: quad-matched windows were 0% satisfied at every dr.
2. **Harness live?** If controls flip fewer than 50% of units, declare the harness **INERT** and draw
   no conclusion about `k in {1,2}`. A `k = 0` verdict change also voids the run.
3. Given 1 and 2 pass:
   * `retained >= 0.95` -> **the metric admits whole-winding displacement among accepted geometry.**
     The concern is demonstrated on real fitted geometry. Post it.
   * `retained <= 0.50` -> **the metric catches it in practice.** The concern is closed. Post that
     too, on the same thread where it was raised.
   * otherwise -> report `retained` with its interval and draw no verdict.

## What this cannot establish

Prevalence. The injection is imposed, so this measures whether the metric *can* be fooled on
accepted geometry, never how often real fits land there. Estimating that needs anchors, and
`abs_winding.json` ships 59 across 6 collections, of which one was directly attached in the z window
TAUIL examined. That ceiling is annotation supply and no amount of compute moves it.

Also single scroll (PHercParis4), reduced z-ROI (roughly a third, VRAM-bound at 24 GB), one fit
configuration, and a fitted `dr` rather than a swept one.

## Failure modes being pre-committed against

* Selecting units after seeing injected outcomes. Selection is on the baseline verdict alone.
* Reporting `retained` over a tiny `N`. Rule 1 forbids it.
* Treating an inert harness as evidence of blindness. Rule 2 forbids it, and it is the exact error
  the half-winding controls exist to catch.
* Reporting only the favourable arm. Both the >= 0.95 and <= 0.50 outcomes are pre-committed to be
  posted, including the one that retracts our own concern.
