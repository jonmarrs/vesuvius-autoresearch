# PRE-REGISTRATION: a conservative sheet-switch detector

**Committed UNRUN, 2026-08-29.** No detector code exists yet, nothing has been scored, and no
number below has been computed. Design and decision rule are fixed here first.

## Why this is not the question @pmh47 closed

Issue #1621 asked whether the satisfaction metric detects a **whole-patch** displacement by a whole
winding. It does not, and @pmh47 established that this is correct: in general no absolute winding
exists for a patch, so the periodicity is the right invariance.

**A sheet switch is not a whole-patch displacement.** It is a *partial* one: part of a traced
surface jumps to a neighbouring wrap while the rest stays. That produces an **internal
discontinuity**, which is a local continuity violation rather than a global gauge choice, and the
wish list asks for exactly this:

> Sheet switches | Meshes can jump from one wrap to another. | VC3D inspection and manual
> correction. | **Stronger local continuity constraints and conservative failure detection.**

A whole-patch shift is invisible *by design*. A partial shift is not, and nothing in the closed
issue says it should be.

## The detector

`satisfaction_metrics.get_patch_satisfied_areas` already returns `target_winding_idx_per_patch`, an
`(H-1, W-1)` integer winding index per quad, `-1` where no target was assigned. It is computed and
never persisted.

**Signal:** within a single patch, two 4-adjacent quads that both have a target and whose winding
indices differ. A patch is meant to be one sheet, so an interior winding jump is a switch candidate.

**Conservative operating point, fixed here:** a candidate is reported only if the discontinuity
forms a connected boundary of at least `L` adjacent quad-pairs, with `L` swept over
{1, 2, 4, 8, 16} and the reported operating point chosen by the rule in "Decision rule" below, not
by inspecting which value looks best.

Offline recomputation reuses upstream's own loaders (`load_checkpoint_cpu`, `build_fit_inputs`,
`build_transform` from `find_inconsistent_windings.py`), so no part of the fit or the metric is
reimplemented.

## Floors, published beside every number

Same discipline as ScrollGT's other families.

| floor | what it is |
|---|---|
| `flag_nothing` | reports no candidates; bounds the value of silence |
| `flag_everything` | every patch is a candidate |
| `flag_random_matched` | random patches at the detector's own flag rate, 5 seeds |
| `flag_disconnected_subrow` | patches whose subrow BFS left an unreached component, a trivial geometric proxy already measured in `reports/subrow_disconnection.md` |

## Validation by injection

**Treatment.** In a converged fit, displace a **contiguous half** of a patch's quads radially about
the umbilicus by `k * dr` at that patch's own dr, leaving the other half untouched. This manufactures
a sheet switch with a *known* location and magnitude.

`k in {1, 2}` (whole-winding switches, the realistic failure) and `k in {0.5, 1.5}` (half-winding,
a grosser error).

**Controls that can fail:**

* `k = 0`, a null injection, must leave the flag set unchanged. Any change means the injection
  path itself perturbs geometry and the run is void.
* half-winding injections must be caught **at least as often** as whole-winding ones. A detector
  that catches a subtler error more often than a grosser one is miscalibrated, and that outcome
  voids the result rather than being reported as a curiosity.

**Outcome measures:** detection rate at the planted location (recall), and flags raised on
un-injected patches in the same run (false-alarm rate). Both reported against every floor.

## Decision rule, fixed in advance

Let `R_k` be recall at displacement `k` and `F` the false-alarm rate, each measured across **three
seeds**, with `S` the seed-to-seed spread of the detector's margin over `flag_random_matched`.

1. **Operating point** is the smallest `L` whose false-alarm rate is at or below `flag_random_matched`'s.
   Chosen by that rule, not by which `L` gives the best recall.
2. **Go / no-go, by 2026-09-15:** the detector must beat `flag_random_matched` on `R_1` by a margin
   greater than `S`. If it does not, **this is not filed.** The finding is published as a negative
   result and September is filed with the reproduction guide alone, or with nothing.
3. **Conservative means conservative.** If `F` exceeds 5% of patches at the chosen operating point,
   the detector is reported as **not conservative** regardless of its recall, because the wish list
   asks for a tool that a human can trust to stay quiet.
4. **Powered.** The baseline fit scores 38,439 patches with 25,148 satisfied, so unlike the shelved
   winding study there is no `N < 30` risk. If for any reason fewer than 100 patches are eligible
   for injection, the study is declared UNPOWERED and reported as such.

## What this cannot establish

Prevalence of real sheet switches. Injections are planted, so this measures whether a detector finds
a switch that is there, never how often one occurs. Estimating that needs labelled switches, which
do not exist publicly.

Single scroll (PHercParis4), single z-ROI [13056, 18432), single fit configuration with three inputs
disabled. Detection of *our own* injection is an easier problem than detection in the wild, and the
write-up must say so wherever a number is quoted.

## Failure modes pre-committed against

* Choosing `L` after seeing which value maximises recall. Rule 1 fixes the selection rule.
* Reporting recall without the false-alarm rate. Rule 3 makes a high-recall, high-alarm detector a
  failure rather than a result.
* Quietly widening the injection until it becomes detectable. `k` is fixed here at {0.5, 1, 1.5, 2}.
* Filing a tool that does not beat its own floor. Rule 2 says file nothing instead.
