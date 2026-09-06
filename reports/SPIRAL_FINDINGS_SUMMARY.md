# Spiral ink objective: what we measured, with every floor attached

**2026-08-31, extended 2026-09-05.** One page over fifteen reports. Each claim is paired with the
floor it must clear, because the floor is what several of these results turned on, and getting the
floor wrong caused two reversals in a single afternoon.

## The floors, established first

| floor | value | applies to |
|---|---:|---|
| pipeline non-determinism | **1.42%** | two renders of the SAME meshes, and same-fit comparisons |
| seed spread, `2*CV`, n=4, **inner** w010-w019 | **21.7%** (95% CI 12.3-81.0%) | two DIFFERENT fits, inner windings |
| seed spread, `2*CV`, n=4, **outer** w120-w129 | **8.4%** (95% CI 4.8-31.4%) | two DIFFERENT fits, outer windings |
| duplicate-coverage baseline (full fit) | **0.0897 to 0.1042%** | gap>=2 overlap in any converged fit |
| duplicate-coverage baseline (10-winding span) | **0.00%** | the span all arms are measured on |

`reports/pipeline_determinism_and_which_floor_applies.md`, `reports/seed_spread_four_fits.md`,
`reports/outer_winding_noise_floor.md`.

**The floor is region-specific and the difference is large.** A floor measured on the inner windings
is 2.6x too wide for the outer ones. Quote the one for the region you measured in; transferring
across regions is what made finding 13a's stated margin wrong.

**Every floor here is an n=4 variance, and those are far softer than a bare percentage suggests.**
The 95% interval on a CV at n=4 spans **0.57x to 3.73x** the point estimate, which is why the
intervals are now printed beside the numbers. This is not a technicality: an n=4 variance has misled
this work **twice, in opposite directions** -- it made the outer floor look 2.6x wider than it is
(finding 14), and it made the geometry effect's sd multiple look nearly twice as large as it is
(finding 12, corrected 2026-09-03). Use a floor to decide whether a comparison is worth taking
seriously, not to decide a result; where a difference lands near one, the honest answer is a test
with a stated alpha, not a ratio against a soft denominator.

## Findings

**1. The objective can be inflated by coverage that reads nothing new.**
Duplicating all ten windings, with occupied cells byte-identical to baseline so zero new papyrus is
read, raises `total_fg_pixels` **+92.47%** while `overall_fg_fraction` moves **-0.00044**. 65x the
applicable floor. `reports/duplicate_coverage_inflates_the_objective.md`.

**2. The metric cannot separate fake growth from real growth.**
A duplicated eleventh winding (+12.59%) and a genuinely new eleventh winding (+12.83%) land **0.24
percentage points apart**. Like-for-like, needs no floor.

**3. Neither structure score catches it.**
`line` and `column` move as much or more for the honest arm than the duplicate. They fail this
failure mode. This weakened a suggestion I had already made upstream in villa#1658.

**4. The objective is not broken: it does reward a better fit.**
A 100-step fit scores **-59.5%** against a 30,000-step one, **2.7x** the different-fit floor.
`reports/objective_does_track_fit_quality.md`. Gameable and working are both true.

**5. It is noisy between equally good fits.**
Four fits differing only in seed, satisfaction indistinguishable (0.8382 to 0.8404), give
`total_fg_pixels` CV **0.1086**, worst pair **25.3%**. A single-run gain below ~21.7% is
uninterpretable, which is why `autoresearch.md`'s two-seed check is load-bearing, not merely prudent.

**6. A three-second geometric check separates what no ink metric can.**
Across five arms, `total_fg_pixels`, `fg_fraction`, `line` and `column` all overlap between
duplicated and honest; gap>=2 winding overlap separates cleanly (8.37 to 100% against 0.00%). It
costs 3 s on a 120-winding fit against ~12 min for one render and score, needs no ink volume, scorer
or GPU, and runs before any render. `reports/a_cheap_guard_the_metrics_lack.md`.

**7. Duplicate coverage is introduced by fitting, and concentrates in the outermost windings.**
Median wmax 126, 79.9% involving a winding at or beyond w120, reproducible across five fits with
median radius varying by 13 voxels. **Its cause is unknown**: the extrapolation explanation first
offered was withdrawn on 2026-09-01 when the arithmetic behind it proved invalid.
`reports/duplicate_coverage_is_an_outer_winding_phenomenon.md`.

**7b. It is introduced by fitting, not inherited, at every scale tested.**
Exactly 0 gap>=2 cells in the 100-step configuration at quant 1, 2 AND 4; nonzero at all three in
converged fits (242 / 1,764 / 10,345). gap-1 is background, near-identical between the two (627 vs
623 at quant 1), which is why it is excluded. Duplicate coverage is also *more* seed-reproducible
than the objective it can inflate (CV 0.0667 against 0.1086). The absolute figure is a proximity
measure at the chosen quantisation and must be quoted with it.

## Findings about the loop's decision procedure, not just its metric

These came later and are the most directly actionable, because they concern a procedure
`autoresearch.md` already prescribes rather than a property of the metric alone.

**8. The prescribed two-seed check lets through one null change in six.**
At the measured CV, the strict reading (both change runs beat both baseline runs) accepts **16.6%**
of changes with zero true effect; the loose reading (mean of two beats mean of two) is a **coin
flip** at 49.9% and is not a filter at all. An assumption-free enumeration over the four measured
values gives 1/6 and 3/6, agreeing with a 200,000-run simulation to a decimal. It also *discards*
59% of genuine +10% gains. `reports/two_seed_check_lets_through_one_in_six.md`.

**9. Two fixes, one of them free.** Three seeds per arm brings the strict rule to **5%**, at two
extra fits. Requiring `total_fg` AND `line` to both survive is stronger across the entire plausible
correlation range and never weaker, at **zero** extra fits, because the scorer already writes line
score. That correlation cannot be estimated at n=4, so the result is bounded (0.9% to 16.7%) rather
than claimed.

**10. Geometry quality and recovered ink decouple at seed scale.**
`satisfied_area` has CV 0.00114 against the objective's 0.10863: the ink metric is **96x noisier**.
Among converged fits whose geometry is indistinguishable, ink varies 25%. So the premise "a better
fit recovers more ink" holds at coarse scale, where we measured it, and not at the scale the loop
operates. The prescribed satisfaction cross-check is correspondingly stiff: **passing it rules out
catastrophe, not error.** `reports/geometry_and_ink_decouple_at_seed_scale.md`.

**11. villa's default spiral config warned about itself — UPSTREAM FIXED IT on 2026-08-27.**
> Commit `61a62c445` (#1625) split the parameter: `model_gap_expander_capacity_windings` now
> allocates the lattice with default **144** (>= 130+3, so consistent), and
> `model_gap_expander_num_windings` is documented as legacy and inert. **There is no live villa bug
> here and it must not be reported as one.** Our fits ran on a pre-fix tree, so findings 11 and 12
> are valid for villa as of 2026-08-26 and describe the value of a fix upstream has already made.
> Our tooling provenance was also wrong: fits used the villa-spiral WORKING TREE `6847063f`, renders
> used its `origin/main` `5479453a`. `reports/gap_expander_finding_is_stale_upstream_fixed_it.md`.

**11a. As originally written (true before 2026-08-27):**
`shell_outer_winding_idx` defaults to 130 and requires `model_gap_expander_num_windings >= 133`,
which defaults to 130. No shipped config overrides either, nothing anywhere assigns them, and the
inference path cannot fire because the default is not None.
`reports/spiral_default_config_gap_expander_shortfall.md`.

**12. Setting it to 133 measurably improves the fit: 5 seeds against 6, p = 3.9e-06 — which
measures the worth of upstream's #1625, not a change villa still needs.** See finding 11.

`satisfied_area` 0.84764 (n=5, sd 0.00105) against 0.83897 (n=6, sd 0.00167), **+1.034%**,
Welch t = 10.46, and the two sets are **completely disjoint** with 0.0061 between the highest base
and lowest gap fit. Every gap fit was run for the ink arms, so each is an independent re-test of
this as a registered control, and none was excluded. **Correction:** the "+7.3 to +9.8 sd" first
published divided by a base sd estimated from four fits; at six the sd is 0.00167 and the same fits
sit **4.5 to 5.9 sd** above. The effect is unchanged, the noise estimate was too small.
`reports/gap_expander_fix_improves_the_fit.md`. Sizing the test with our own noise measurement
is what made two seeds enough: this quantity's CV is 0.00114, not the objective's 0.1086. So the
finding is no longer "a default that warns about itself", which could be dismissed as cosmetic; it
is a one-line config change that improves villa's own geometry diagnostic.
`reports/gap_expander_fix_improves_the_fit.md`.

**13. RESOLVED at n=12: the change COSTS about 10% of recovered ink, while improving the geometry
score.** Six fits per arm on w120-w129, second look at the registered Pocock alpha 0.0294:
`total_fg_pixels` **-10.35%, 95% CI -15.68% to -5.03%, p = 0.0018**, with complete separation (all
six GAP below all six BASE, null probability 0.108%) and `fg_fraction` agreeing at -10.78%. The
registered prediction was MET. **The same change raises `satisfied_area` by 7-10 sd and lowers the
ink objective by a tenth** — both established on the same twelve fits, which sharpens finding 10 from
"decoupled" to "opposite for this change", and means a satisfaction cross-check would have passed
enthusiastically on a real regression. Not a live villa defect: the fits predate upstream #1625.
`reports/gap_fix_costs_ink_established.md`. The earlier looks stand as history:

**13b. At n=7 it was not established, and leaning.**
Seven fits (4 base, 3 gap) on w120-w129: `total_fg_pixels` **-9.25%**, 95% CI -19.35% to +0.85%,
**p = 0.0637** -- does not clear alpha 0.05, so not established. The arm sees effects of ~9.0% and no
smaller, and the observed effect is 9.25%, so its power ran out at exactly the size in question. Every
gap fit scores below every baseline fit (complete separation, p = 2.86%), and the registered
prediction of a negative direction was MET -- but separation was registered as confirmatory only and
does not override the primary. Settling it needs ~6 per arm, about a day of compute.
`reports/gap_fix_ink_six_fits.md`. The earlier single-pair version below stands as history:

**13a. The first measurement in the right region (one fit per arm).**
The first ink measurement of the fix was aimed at the wrong region: the shortfall acts on the
outermost windings, and every render in this work covered the innermost ten. Re-measured on
w120-w129 of the same two fits, `dT` = **-11.03%**. Registered before the data as the likely
outcome, precisely so a null could not later be dressed up as evidence of no effect.
`reports/gap_fix_outer_windings_still_not_established.md`. **The margin that report quoted was
wrong; see finding 14.**

**14. The outer windings are two and a half times QUIETER than the inner ones, and that made
finding 13a borderline rather than comfortable.** Four honest seeds rendered and scored on
w120-w129 give `total_fg_pixels` CV **0.0421** against the inner 0.1086 -- the opposite of the
registered prediction, recorded as a **miss**. The floor out there is **8.4%**, not the 21.7%
transferred from the inner windings, and the observed **-11.03% exceeds it**: on the point estimate
the rule returns REVERSES. It is nonetheless **UNRESOLVED**, because a floor from n=4 is an interval
(95% CI 4.8% to 31.4%) that straddles the observation. So finding 13a survived in letter while its
stated margin did not: -11.03% was borderline, and a properly powered arm could plausibly find the
gap fix COSTS ink where it acts. **The arm was then run: finding 13.** It did not clear either, so
this floor did its job -- it turned "comfortably null" into "borderline", which is what the seven-fit
result went on to confirm. `line` is unchanged between regions (0.0356 vs 0.0342), so this is
specific to the objective. `reports/outer_winding_noise_floor.md`.

**15. The column score's noise is one of its two terms, evaluated 3x outside its design range.**
`col_score` has outer CV **0.2139**; its `col_width_conformity` term has **0.2152** and its
`col_gap_contrast` term has **0.0082**. The score's noise is entirely conformity, which asks what
fraction of detected columns fall in 722-977 px while the detected median width out there is
240-293 px -- a tail count three widths from the distribution's centre. `col_gap_contrast` is by
contrast one of the steadiest quantities in this work, steadier than the objective by 5x. So "the
column score is noisy" was never true of the whole score, and reading it in this region means
reading a term outside the regime it was tuned for. Whether the outer windings really carry ~270 px
columns or the detector mis-segments them there is **unresolved** (finding 16 claimed to resolve it
and was retracted). What IS now known: the detector is accurate on synthetic columns, so its
227-306 px readings describe the strips, not a detector defect.
`reports/outer_winding_noise_floor.md`.

**16. RETRACTED the same day.** It claimed the outer windings lack a ~945 px column periodicity the
inner ones have, and that villa's detector under-measures width 4x. Both are wrong. A positive
control shows `score_columns` recovers known widths accurately (850->868, 600->622, 300->296) and
survives text-like broken ink (945 px pitch -> 954-965 px). And my "periodicity" was a fixed fraction
of strip width (peak/width = 0.1071 across four strips), i.e. my own high-pass residual; the inner
and outer strips had been analysed with different cutoffs (1101 vs 2500 px) because of
`hp = min(2500, p.size//8)`. Finding 15's question is **open again**.
`reports/column_structure_is_absent_outer_not_missegmented.md`.

**17. Refitting on the fit's own well-satisfied patches is a registered FAILURE.**
villa names the avenue in `37_2026_open_problems.md` ("automatically crop 'good' regions of the
spiral fit, and use these as surface patch inputs to a subsequent run"). Six fits, three per arm,
against a control matched on total patch area: `satisfied_area` **+17.66% (p < 1e-4)**,
`total_fg_pixels` **-0.83% (p = 0.89)**. Registered in advance as a failure rather than a partial
success, because selecting patches BY satisfaction and scoring the result ON satisfaction is close to
circular. Prediction met. The null is bounded, not empty: no ink effect larger than ~10% at n=3 per
arm. `reports/patch_bootstrap_verdict.md`.

**18. The two metrics now disagree in BOTH directions, which is the load-bearing result.**
Finding 13 showed the guard passing a real 10% ink regression. Finding 17 shows it firing at +17.66%
for no ink gain at all.

| case | `satisfied_area` | `total_fg_pixels` |
|---|---|---|
| gap-expander config, n=12 | +1.03% | **-10.35%** |
| patch bootstrap, n=6 | **+17.66%** | -0.83% (null) |

A cross-check that can move confidently the wrong way *and* confidently the useless way is
uninformative about ink in either direction. This is what the unposted villa draft argues;
`docs/VILLA_DRAFT_metrics_disagree.md`.

**19. Satisfaction falls with radius, so selecting on it starves the region the ink is scored in.**
Mean per-patch satisfied `fraction` runs **0.9421** in the innermost radial decile to **0.7198** in
the outermost, Pearson **r = -0.21** over 35,963 patches. A 0.90 threshold therefore drops outer
patches preferentially: the bootstrap arm matched its control on TOTAL area to 0.01 points while
carrying **~11% less relative area inside the scored strip w120-w129**. **A global area match does
not imply a match where the endpoint is measured.** Measured and published before any endpoint of
finding 17 was read. `reports/patch_bootstrap_outer_evidence_deficit.md`.

**20. Radius orders windings but cannot identify one.**
Median radius is monotone across thirteen sampled windings (w010 882 -> w129 2,576), so a radial band
table reads inner-to-outer. But a single winding sweeps a median **1,683 vx** of radius because the
spiral is not a circle -- w129 spans 1,715-3,358 and overlaps w100 entirely. The scored strip
w120-w129 covers radius **1,593-3,311**. Finding 19's report originally called its outermost band
"the region w120-w129 is scored on" and was corrected; the deficit survived at -11.2%, -15.4% and
-13.7% across three definitions of that region. `scripts/calibrate_radius_to_winding.py`.

**21. Equalising the evidence in the scored strip does not rescue the method either.**
Finding 17's control matched BOOTSTRAP on *global* area while BOOTSTRAP carried ~11% less area inside
the strip the ink is scored on, which left open that a real selection benefit was being masked. A
second registered study built a control matched on **both** total area (100.00%) and in-strip share
(0.4120, gap 0.0000), then compared it against the same three BOOTSTRAP arms:

| endpoint | STRIPMATCH | BOOTSTRAP | rel | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 1,693,013 | 1,628,729 | **-3.80%** | 0.5527 |
| `satisfied_area_fraction` | 0.8430 | 0.9799 | +16.24% | 0.0000 |

**FAILURE again, prediction met.** With the deficit removed, BOOTSTRAP's ink estimate moves *further
against* it (-0.83% -> -3.80%), the opposite direction from a masked benefit. **The outer deficit of
finding 19 is a side effect of selecting on satisfaction, not the cause of finding 17's null.** The
+16.24% geometry number carries no credit: BOOTSTRAP is selected ON satisfaction and the control is
not, so it is guaranteed by construction. Three BOOTSTRAP arms, two independently-built controls,
neither favouring them. Both nulls bounded at ~9.6%, not empty.
`reports/stripmatch_verdict.md`, `reports/stripmatch_draw_stability.md`.

## What is NOT established, and matters

**Reachability through a fit is unproven, and the search for it is CLOSED.** Every duplicate arm
copies mesh folders, which villa's loop cannot do; it edits `fit_spiral.py`. Two attempts to induce
overlap through a fit, each a verified single-variable change:

* `loss_weight_min_spacing` 2.0 -> 0: duplicate coverage **unchanged** (0.10%);
* `loss_weight_dense_spacing` 12.0 -> 0: duplicate coverage **fell** to 0.04%, the opposite of the
  registered prediction.

Under the stopping rule registered before the second arm, the search ends rather than continuing to a
third knob. **Fit-produced duplication could not be induced by the obvious means.** That is weak
evidence an optimiser would not stumble into the exploit, and it belongs beside finding 1 rather than
buried. `reports/two_nulls_fit_produced_duplication_not_induced.md`.

**A third arm (`output_winding_margin` 4 -> 0) is VOID**, not a null: its verification condition
could not fire, because the observable is clamped by a config constant.
`reports/margin_arm_void_and_a_premise_withdrawn.md`.

**A fourth arm (`model_gap_expander_num_windings` 130 -> 133) also returned a null** on duplication,
0.0909% against the honest 0.0897 to 0.1042%. Four explanations proposed for the outer-winding
concentration, four dead. The cause is unknown and the search is stopped.

**The outer boundary is a configured constant, not the end of the data.** Input patches reach radius
6510 while the outermost output winding sits at ~2504, so 27.5% of patches extend past where the fit
stops. Extrapolation is ruled out as the explanation.
`reports/the_outer_boundary_is_configured_not_data.md`.

**The satisfaction guard is untested.** `autoresearch.md` names three checks; this work tests two.
Mesh-level duplication leaves the fit untouched by construction, so satisfaction cannot respond. It
may well catch fit-produced duplication, and nothing here says otherwise.

**Nothing here observes villa's loop.** These are properties of the metric, not evidence any run has
exploited them.

## Provenance

Every finding is pre-registered with its decision rule fixed before the data, and the analysis code
for the seed spread was written before the fits finished. The corrections are in the reports rather
than tidied away: two results withdrawn and one reinstated, one prediction (arm D) recorded as a
miss, two nulls against predictions, one arm voided, and one explanation withdrawn.

**A pattern worth carrying forward:** all three verification conditions registered for the fit arms
were mis-specified, each written from a plausible reading of the code rather than from checking what
the observable actually does. Two were caught, one produced a void arm and a withdrawn premise. The
fix is to confirm an observable responds to a manipulation before spending the GPU time, not to
guess better.

**A fourth instance of the same class, caught late:** the first ink measurement of the gap-expander
fix was aimed at the innermost ten windings while the change acts on the outermost. The observable
was fine and the *region* was wrong, so the arm would have read null whether or not the fix works.
The question to ask before registering is not only "does this observable respond?" but "where can
this manipulation express itself?" (finding 13).

**A fifth instance, caught by a control rather than by luck:** finding 19's band table was first
built by assigning each patch to the band holding its centroid. The median patch spans 602 vx of
radius against 149 vx bands, so that measured almost nothing. Positive-controlling the instrument
before writing it up exposed it; spreading each patch's area across the bands it covers fixed it, and
the finding survived. Had it not survived, the table would have been withdrawn rather than corrected.

**That ambiguity is now CLOSED, and the blind design is why it could be.** Finding 17's control
matched globally and not inside the scored strip, so its null could have hidden a selection benefit.
`docs/preregistration/2026-09-04_stripmatch_followup.md` was written while those endpoints were still
unread -- fixing both the design and the "run on FAILURE" trigger before the result that would
motivate them existed -- and finding 21 answers it: no benefit with the strip equalised. A follow-up
designed after seeing the verdict would have been shaped by the verdict it was meant to explain.

Reproduce: `repro/spiral_render/`, `scripts/measure_winding_overlap.py`,
`scripts/analyse_seed_spread.py`. All from published artifacts.
