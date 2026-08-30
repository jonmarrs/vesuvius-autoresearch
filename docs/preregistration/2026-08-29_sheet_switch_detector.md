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

---

# POST-OBSERVATION NOTE, 2026-08-29. The rule is NOT amended.

Added after measuring the baseline flag rate and before any injection. It records two things and
changes nothing: the decision rule above stands exactly as written.

## 1. An excursion outside the pre-registered sweep, not adopted

The sweep fixed above is `L in {1, 2, 4, 8, 16}`. While measuring, I also ran `L = 32`. Results on
the converged baseline fit, 38,442 patches:

| L | patches flagged | rate |
|---:|---:|---:|
| 1 | 2,914 | 7.6% |
| 2 | 2,914 | 7.6% |
| 4 | 2,851 | 7.4% |
| 8 | 2,712 | 7.1% |
| 16 | 2,367 | 6.2% |
| **32** *(not pre-registered)* | 1,665 | **4.3%** |

**Within the pre-registered sweep, no operating point reaches the 5% bar.** `L = 32` is the only
value that does, and it was not pre-registered. **It is not adopted, and it must not become the
reported operating point.** Extending a sweep until a threshold is met, having seen that the
registered values fail, is the precise failure this document exists to prevent. It is recorded here
rather than deleted so the temptation is part of the record.

## 2. A flaw in rule 3, recorded and deliberately not fixed

Rule 3 treats the flag rate on un-injected patches as a **false-alarm** rate. That assumes flagged
patches are clean. Sheet switches are a real failure mode that VC3D users currently correct by hand,
so some of those 2,914 patches are plausibly **genuine switches**. With no labelled switches in
public data, true detections and false alarms are not separable in that number.

So 7.6% is an **upper bound on false alarms**, not a measurement of them, and rule 3 as written can
fail a detector for correctly finding real defects.

**Decision: rule 3 stands as written.** The flaw was found *after* seeing the baseline rate, so any
amendment now would be made with knowledge of the number it would relax, which is indistinguishable
from tuning the standard to fit the result. Keeping a known-conservative bar costs us a possible
true finding; moving it would cost the credibility of every number under it.

The injection study is what makes the numerator meaningful: it supplies known positives at known
locations, which is the only handle available on the true/false split.

**If a future amendment is ever made, it must be dated, must state that it was made with knowledge
of the 7.6% baseline, and must not be applied retroactively to results already scored.**

---

# DESIGN FREEZE, 2026-08-29, before any injection or seed-agreement run

The detector specified at the top of this document used **connected-boundary length** `L`. Baseline
measurement showed that statistic is wrong for this signal: the split is bimodal and consists of two
large regions, so `L` barely moved the flag rate (7.6% at `L=1` to 6.2% at `L=16`). The statistic is
replaced here, and the replacement is frozen before any validation runs.

**Disclosed:** the new statistic was chosen **after** seeing the baseline distributions in
`reports/sheet_switch_baseline_signal.md`. That is legitimate development, not validation, but every
write-up must state it, and no result below may be presented as if the statistic had been chosen
blind.

## The frozen detector

For each patch, over **satisfied quads only** (quads the metric accepts, where the winding
assignment is meaningful):

```
minority_fraction = 1 - (count of quads on the patch's most common winding) / (satisfied quads)
```

A patch is **flagged** when both hold:

* `minority_fraction >= 0.10`
* the minority region is at least **16 satisfied quads**

Nothing else. No boundary-length term, no shape term, no per-patch tuning.

## Why 0.10, and what it costs us

0.10 is chosen as "a substantial region of the patch sits on another winding": a tenth is well past
any plausible single-quad noise, and 16 quads is the minimum patch size already used throughout.

**At 0.10 the baseline flag rate is 5.12%, which FAILS rule 3's 5% bar.** A threshold of 0.20 would
give 3.74% and pass. **0.20 is not chosen, precisely because passing is the only reason to prefer
it.** Selecting a threshold because it clears our own bar is the same failure as extending the `L`
sweep to 32, and that one is already recorded three sections above.

So this detector is frozen in the expectation that it fails rule 3 as written. Rule 3 stands.

## Added control: seed agreement

A flag that does not survive a re-fit is measuring optimizer noise, not geometry. A second fit of
the same data, identical except `optimizer_random_seed: 2`, is running now.

**Measure:** of patches flagged in fit A, what fraction are flagged in fit B, and vice versa
(Jaccard over flagged patch ids). **Floor:** the agreement expected if the same number of patches
were flagged at random, computed from the two flag counts and the patch population.

**Pre-committed reading, fixed before the numbers exist:**

* agreement at or below the random floor means the detector is measuring fit noise, and it is
  reported as such regardless of injection recall;
* high agreement does not prove the flags are switches, only that they are properties of the
  geometry rather than of the seed.

This control can fail, and if it does it ends the line of work.

## What remains unfrozen

The injection study's parameters are already fixed at the top of this document (`k in
{0.5, 1, 1.5, 2}`, contiguous half-patch displacement, `k = 0` null arm, three seeds). Nothing there
changes.

---

# CLOSED 2026-08-30. Not filed. The premise did not survive.

The study ends here, before its 2026-09-15 gate, and not because the gate was failed on evidence.
The condition it was designed to test turns out to be unreachable.

`get_patch_satisfied_areas` computes ONE target per patch and accepts a quad only within
`0.45 * dr` of it. Geometry displaced by a whole winding sits `1.0 * dr` away, so it cannot be
satisfied on the neighbouring winding, only fail. And the per-quad winding index is
`round((target_shifted_radius - cum_adj + branch_offset) / dr)`, where both correction terms are
theta-wrapping bookkeeping rather than statements about where the surface lies.

So the two-winding condition this detector looks for cannot be produced by displacing geometry, by
us or by a real sheet switch. Three injection designs failed for three different-looking reasons;
the fourth would have too. Full argument and numbers:
`reports/sheet_switch_detector_premise_broken.md`.

**Rule 2 is honoured, not evaded.** It committed us to filing nothing if the detector could not be
shown to beat its floors. It cannot be shown to beat anything, because recall is not measurable
here.

**What the pre-registration bought.** Every constraint in it held under pressure and each one cost
something:

* `L = 32` cleared the 5% bar, was outside the registered sweep, and was recorded and not adopted;
* the frozen threshold failed rule 3 at 5.02% and the 0.20 threshold that passes was declined,
  because passing was its only merit;
* rule 3's own flaw was found after seeing the baseline and left unamended for that reason;
* the seed-agreement control's reading was fixed before the numbers existed, which is why a 0.9696
  Jaccard was reported as "geometry, not noise" rather than as vindication.

Without those written down first, this session would have produced a filed submission resting on a
detector that cannot detect the thing it names.

**What was not caught.** None of it questioned the premise. The pre-registration specified how to
validate the detector and never asked whether the condition it detects is reachable. That question
was answerable on day one by reading what makes a quad satisfied, and cost about a day by not being
asked.
