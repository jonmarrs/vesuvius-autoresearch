# Spiral ink objective: what we measured, with every floor attached

**2026-08-31, extended 2026-09-07.** One page over seventeen reports. Each claim is paired with the
floor it must clear, because the floor is what several of these results turned on, and getting the
floor wrong caused two reversals in a single afternoon.

> **Provenance, read this before quoting anything below.** Findings 1-23 were measured on
> villa-spiral `6847063f`. Current villa recovers **67.6% more ink** through a byte-identical
> renderer and scorer (`reports/current_code_baseline.md`), so everything here describes superseded
> code. The arithmetic stands and the registrations were honoured; what is open is whether the
> relationships hold on the current tree, which
> `docs/preregistration/2026-09-11_decoupling_on_current_code.md` measured — **and the extension
> failed.** Ink null reproduces (+0.28%, p=0.80); `satisfied_area` ROSE 1.18%, the direction the
> registration itself called uninterpretable. Nothing below may be described as holding on current
> villa. [Verdict](decoupling_does_not_cleanly_reproduce.md).

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
59% of genuine +10% gains. **Corrected 2026-09-12:** the power half is obsolete for current villa (that table used the inner CV 0.1086; current seed noise is **0.0536**, where two seeds detect a 5% gain **44%** of the time — we said 0.0125/99% then 0.0263/75%, both withdrawn; six unused `curbase` seeds doubled the floor again on 2026-09-19, `reports/six_unused_seeds_double_the_current_floor.md`). The false-positive half is *stronger* than stated — it is exactly **1/C(2k,k)**, distribution-free, so it depends on nothing and no amount of better fitting improves it; three seeds takes 1-in-6 to 1-in-20. `reports/two_seed_check_lets_through_one_in_six.md`.

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
circular. Prediction met. The null is bounded, not empty: no ink effect larger than ~10% *(corrected 2026-09-12 to ~12%: the registered MDE used a df=3 CV that was optimistic — `reports/noise_floor_by_tier.md`)* at n=3 per
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
neither favouring them. Both nulls bounded at ~9.6% as registered, ~12% corrected, not empty. *(corrected 2026-09-12 to ~12%: the registered MDE used a df=3 CV that was optimistic — `reports/noise_floor_by_tier.md`)*
`reports/stripmatch_verdict.md`, `reports/stripmatch_draw_stability.md`.

**22. Winding constraints improve the geometry and do not reach the reading.**
villa names winding constraints as the scaling path ("the fastest way to unroll scrolls at scale").
`data/spiral_s1` ships **5,413 same-winding** and 2,173 relative constraints against 59 absolute
ones. Emptying `same_windings.json`, three arms against the six existing baselines:

| endpoint | BASELINE | ABLATED | rel | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 1,720,000 | 1,690,000 | -1.74% | 0.6114 |
| `satisfied_area_fraction` | 0.8390 | 0.8331 | **-0.69%** | **0.0027** |

**NULL on reading**, bounded at 8.3%, not zero. The geometry fall is *stronger* evidence than a rise
would have been: the registration made `satisfied_area` report-only because removing 5,413 inputs
could inflate it trivially ("less left to satisfy"), and that confound can only manufacture a RISE.
It fell — the fit satisfies its remaining inputs less well despite having fewer of them.
`reports/samewinding_verdict.md`.

**23. The two metrics have now come apart four times, in three different directions.**

| case | `satisfied_area` | `total_fg_pixels` |
|---|---|---|
| gap-expander config, n=12 | +1.03% | **-10.35%** |
| patch bootstrap, n=6 | **+17.66%** | -0.83% (null) |
| stripmatch, n=6 | +16.24% | -3.80% (null) |
| same-winding ablation, 3v6 | **-0.69%** | -1.74% (null) |

The first three concern fitting choices. **The fourth concerns the winding evidence villa is
investing in**, which makes it the one that bears on strategy rather than on tuning.

**24. Over the whole corpus, the guard cannot be shown to track the objective.**
Findings 13, 17, 21 and 22 each ask "did this change move both metrics together?". This asks
"across everything we have measured, does `satisfied_area` predict `total_fg_pixels` at all?" —
24 scored fits, 27% spread in ink, satisfaction 0.8308-0.9804.

**r = -0.121, 95% CI [-0.50, +0.30].**

The interval is the finding. It does NOT establish "no relationship". It DOES exclude a strong
positive one, which is what a usable guard requires — higher satisfaction meaning more ink. Capped at
+0.30 optimistically with a negative point estimate, it is not doing the job `autoresearch.md`
assigns it. Observational across heterogeneous manipulations, not causal.
`reports/geometry_ink_correlation_corpus.md`.

**Updated 2026-09-19 — it now holds on current villa too, and more tightly.** This figure is the
PINNED tier and is unchanged. Three `anchor10cov` fits that ran on current villa had been silently
misfiled into pinned by a drifted prefix list, which is fixed (`scripts/arm_tiers.py`, and an
unclassified arm now raises rather than defaulting). With them restored, the **current tier reads
n=15, r = -0.424, 95% CI [-0.77, +0.11]** — capping a guard's correlation at **+0.11** against
+0.30 on the pinned tree. The question this finding left open is answered in the same direction.

**Not attempted, and why:** searching for a geometric quantity that *does* predict ink needs to tell
candidate proxies apart, and at n=24 every candidate carries an interval about this wide. That needs
~40-60 fits or a manipulation varying ink beyond 27%.

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

**A sixth instance, and the cheapest lesson of the three studies:** the same-winding registration
predicted `satisfied_area` would RISE, reasoning from a 200-step smoke fit that showed a rise. It
fell at convergence. **A smoke fit establishes that an observable RESPONDS; it does not establish
which way it MOVES.** The same registration already recorded that limitation for its drift
measurements and I failed to apply it to effect direction.

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

**25. The decoupling does NOT extend to current villa — the ink null reproduces, the evidence
does not.**
Registered re-measurement of the same-winding ablation on current code
(`docs/preregistration/2026-09-11_decoupling_on_current_code.md`). Ink **+0.28%, 95% CI
[−2.56%, +3.13%]** — null, and a strong one. But `satisfied_area` **ROSE** 1.18% (p=0.0175), and the
registration had pre-declared a rise uninterpretable: removing 5,413 of the inputs the metric scores
can inflate it trivially, which is why the pinned tree's **fall** was evidence and this is not.
Findings 22–24 are claims about `6847063f` alone. `reports/decoupling_does_not_cleanly_reproduce.md`.

**26. The noise floor every study here quoted was wrong, in both directions.**
Every analysis script hardcodes `OUTER_CV = 0.0421`, measured at **df=3**. Pooling within-arm
deviations across the whole corpus gives the pinned tier **0.0514 (df=18)** — so pinned-tier nulls
bound **~12%, not ~10%**, and excluded less than they claimed. Current villa is **0.0263 (df=6)** — first published as 0.0125 (df=4) and withdrawn when a third arm doubled it,
**2.0× quieter, NOT established** (F(18,6)=3.83, p=0.104). At 3v3 a current-code study sees **6.0%**. The original claim of 4.1× at p=0.0143 rested on two arms agreeing at df=2; `reports/noise_floor_by_tier.md` carries the retraction. **Do not normalise ink by strip area**: `overall_fg_fraction`
is 2.6× noisier than the raw count, because `total_fg_pixels` (0.0125) is quieter than the strip it
sits on (0.0242). `reports/noise_floor_by_tier.md`.

**27. Half of the two-seed criticism expired; the other half turned out to be exact.**
Finding 9's power table used the inner CV 0.1086. At current noise two seeds catch a 5% gain
**75%** of the time (first published as 99.2% at the withdrawn CV 0.0125), so "the check cannot detect realistic gains" is **false for the loop villa runs
today** and we have stopped saying it. The false-positive half is *stronger* than first stated: it is
a rank statistic, exactly **1/C(2k,k)** under exchangeability — 2 seeds **1/6**, 3 seeds **1/20**,
4 seeds **1/70** — independent of the CV, the metric and the code version. That is why 16.6% at CV
0.1086 and 16.7% at CV 0.0125 agree. **No amount of better fitting improves it**, and villa's fits
just got 4× quieter without moving it at all. One extra seed buys 1-in-6 → 1-in-20.

**A sixth self-correction, and the one that cost the most credibility to catch:** finding 25 was
published quoting a bound of 9.6% that came from the *wrong tree's* constant. Checking where that
number came from produced finding 26, which showed the same null actually excludes ±3% — three times
stronger — while also showing every pinned-tier null was ~12% rather than ~10%. **A constant copied
between scripts stops being a measurement and becomes an assumption**; this one had been carried into
studies on a tree it was never measured on. `scripts/measure_noise_floor.py` replaces it with
something that is recomputed from the fits and refuses to pool the tiers.

**28. Ten absolute winding anchors read as well as fifty — within ±10%, which is the honest limit.**
villa asks people to draw absolute winding annotations by hand and names automating them the fastest
path to unrolling at scale; every project in their catalogue that produces them validates on
**geometry**. Cutting the 50 in-ROI anchors to 10 (z-coverage matched) on current villa changes
recovered ink by **−0.86%, p=0.76**. All three ablated arms passed a winding-identity gate at 10/10 —
the strip denotes the same papyrus in every arm — and the non-blank control.

**But the registered 2.9% bound did not hold.** The data exclude only **[−10.21%, +8.50%]** (Welch
df 2.4), because the ablated arm is **3.4× noisier** than the baselines (CV 0.0419 vs 0.0124), driven
by one arm 6.9% below its siblings that passed every validity check. The power calculation assumed the
manipulation would not change the variance. **Budget a future anchor study from the ablated arm's
spread, not the baselines'.** `reports/anchor_ablation_verdict.md`.

**A seventh self-correction, and this one was my own pre-registration.** The same study moved
`satisfied_area` **+1.39% at p=0.0032**, and the registration argued that was interpretable here —
unlike finding 25's manipulation, this one leaves the patch set identical at 38,442. That removed one
confound and missed another: `fit_spiral.py:4345` adds `abs_winding` as a **loss term at weight 5.0
competing with the patch-fitting losses**, so deleting 40 of 50 anchors reduces a competing pull and
the optimiser satisfies patches better. **A rise in patch satisfaction when you delete a competing
constraint is mechanically expected, so this is NOT a fifth decoupling case** and is not reported as
one. The correction sits in the registration at the point the wrong claim was made. The check that
would have caught it — read the *loss* the metric is scored against, not only the inputs it is
computed over — took five minutes after the fact.

**29. villa's objective is far more reproducible than the ink it counts.** *(exploratory)*
`total_fg_pixels` is a count, and every ablation here returns null on it — but a count is silent about
placement. Comparing ink maps in **volume coordinates**, in the scroll's own frame, fits differing
only by RNG seed agree on the count to **1.2%** and on ink placement at **r ≈ 0.70**, against a
θ-rotated null of **−0.09**. Two runs scoring identically are not reading the same text.
**And constraint changes move the ink no more than reseeding does** (0.701 between configs vs 0.699
within), which *strengthens* findings 25 and 28 rather than undermining them: "+0.28% on a count" does
not hide ink relocating. `reports/ink_placement_in_volume.md`.

**30. Two attempts to explain that instability failed, and one of them was caught by a validity gate.**
The *tangential* form — the sheet sliding between runs — is **refused** by a registered coherence test
whose positive control detects a planted 3° shift at p<0.001 (`ink_offsets_are_not_coherent.md`). The
*normal* form has been attempted twice and **remains untested**: the first frame averaged surface
radius across bins holding several windings (`separation_test_was_confounded.md`); the second returned
**ρ = +0.18 to +0.25 at p<0.001 on all three pairs, in exactly the predicted direction, and was an
artefact** — caught only because the registration fixed a *validity threshold* alongside its decision
rule (`the_sanity_check_caught_a_false_positive.md`). Misaligned grids manufacture precisely the
correlation the hypothesis predicts. **Register what the answer must look like to be believable, not
only what counts as a yes.**

**31. The instability is independent noise, so averaging removes it — replicated on three triplets.**
*(exploratory)* Leave-one-out consensus beats a single map by **+0.065**, against **+0.057** predicted
by treating seed differences as independent noise. Replicated free on the `nosamecur` and
`anchor10cov` triplets: **1.10–1.15× predicted on all three**, agreement tighter across triplets than
any one is to theory. The registered statistic (gain vs the *better* single) turned out to be
selection-biased and gave the least favourable of the three numbers — a decision rule fixes what
counts as a yes, not whether the statistic is right. Projection: a **3-seed consensus reaches r ≈ 0.88**
where a single run sits at 0.72, so a loop already running two seeds should keep the consensus rather
than the winner. **A forward test is running** (`2026-09-13_consensus_forward_prediction.md`): three
fresh baseline seeds, predicted 0.884, refuted below 0.80.
`reports/averaging_seeds_buys_what_noise_theory_predicts.md`.

**32. The consensus forward test is VOID, and the gate I built is why.**
Three fresh baseline seeds, predicted r = 0.884 for a 3-seed consensus. `curbase_s6` scored 3,454,937,
outside a registered ink gate of 2.70M–3.05M, so the verdict is **VOID — not a null**. Disclosed and
not claimed: consensus-vs-consensus came out **0.876**, inside the registered CONFIRM range. But s6
shows no independent sign of being a bad arm — normal `satisfied_area`, strip size, non-blank control,
one render attempt, and the **highest** mean placement correlation of all six. The gate's bound came
from the `s1–s3` spread alone (CV 0.0124, df=2) against **0.0740 across six**, and I had flagged that
spread as too tight *before* s5 and s6 existed. **Two days after a validity threshold saved a result
from being a false positive, one destroyed a result that was probably fine.** Gates are not free and
not automatically conservative. `reports/consensus_forward_verdict.md`.

**33. The 09-11 render-code split does not bias ink; both published nulls stand.**
`setup_workdir.sh` builds renders from the submodule's `origin/main`, which moved mid-corpus, leaving
`curbase_s1–s3` the only arms rendered on the old code — so every comparison against them crossed a
change touching `lasagna/fit.py` and the tifxyz reader. Re-rendering `s1`'s existing meshes with
current code: **+1.44%**, inside a registered ±2% band. Adjusting both affected verdicts by the full
amount leaves same-winding at −1.16% and anchor at −2.30%, each inside its own CI. **I escalated this
as URGENT on a difference in a count without decomposing it** — most of the ~4% that alarmed me was
strip area and ordinary density spread. `reports/rerender_test_verdict.md`.

**34. The scorer is deterministic; essentially all variance is upstream of it.**
Re-scoring the same strip with the same code moves `total_fg_pixels` by **26 pixels in 2.9 million
(0.0009%)**. Against 1.44% for a render-code change and ~2.5% CV seed-to-seed, **the fit dominates and
there is nothing to stabilise in the scoring step.** This also sharpens finding 29: placement
reproducing at only r ≈ 0.70 is a property of fitting and flattening, not of a noisy detector — given
the same strip twice, the detector returns the same answer. *(Qualified by finding 40: part of that
0.70 is the binning, not the pipeline.)*

**35. Detector confidence predicts which ink reproduces — and thresholding on it does not help.**
*(exploratory)* Ink in bins all three seeds agree on is more confident than ink only one found:
**+0.132 / +0.151 / +0.159** at the three registered binnings, all p<0.001, and **stable across bin
size** where the consensus fraction was not. But the actionable inference in that verdict's own text
is refuted: at **matched sparsity**, top-N% by confidence is *worse* than a random N% of the same ink
(−0.033 at 50%, −0.061 at 20%). Confidence carries real information about which bins agree; selecting
by it changes the spatial distribution that placement correlation depends on. **Thresholding is not a
free stability lever — averaging remains the only one.** A registered result licenses what it
measured; the sentence after it is a new claim.
`reports/confidence_predicts_but_thresholding_does_not_help.md`.

**36. Averaging seeds buys exactly what independent-noise theory predicts — pre-registered, confirmed
forward, twice.** The prediction was fixed from the model `r_k = 1/(1 + ratio/k)` with `ratio = 0.4204`,
derived from `r_single = 0.7040` measured over all 15 pairs of `s1–s6` (that input later reproduced
exactly). At **k = 3**, predicted **0.877**, measured **0.875** and **0.893** — both inside the
registered 0.85–0.91 band, on arms that did not exist when the number was written down. At **k = 2**,
the case villa's loop actually runs, predicted **0.826**, measured mean **0.8516**. Every control
passed: strip non-blank 48.2/45.6/47.1% against a 0.40–0.55 band, all nine arms inside the ink gate,
and the one previously-seen comparison structurally retired so it could not be re-reported. The
**analysis ran unattended** — decision rule, gate and retirement all committed before the arms
existed, so nobody stood between seeing a number and deciding what it meant.

So the measured curve is **0.7040 → 0.8516 → 0.875/0.893** at k = 1, 2, 3. **A loop already paying for
two seeds is better off keeping the consensus than using them to pick a winner.** Two honest caveats
kept with the result: the model *under*-predicts slightly at both k (+0.026 at k=2, +0.007 at k=3), and
at k=2 two of the three comparisons fell *above* their band while the mean sat inside it.
`reports/consensus_retest_confirmed.md`, `reports/two_seed_consensus_confirmed.md`.

**37. The render-tree split moves placement ten times less than reseeding does.** Triplet A rendered
from `d8c5f488a` while B and C are on `be09a8503`, so A-vs-C carried a confound B-vs-C did not. Bounded
rather than argued away: the *same fit, same seed, same meshes* rendered across that tree change gives
**r = 0.9715**, against within-A seed pairs averaging **0.7178** — decorrelation 0.0285 versus 0.2822.
The earlier +1.44% inert verdict could not be borrowed for this, because it bounds a **count** and this
endpoint is **placement**, the very quantity that comes apart from the count. Registered as unbounded
first, then bounded when the data allowed.
`reports/render_confound_is_bounded_and_minor.md`.

**38. Why the count reproduces when the placement does not — and one named mechanism, measured
small.** The earlier offsets work killed the *tangential* surface explanation and named the test it
had not run: ink agreement against local **normal** surface separation, to which an angular test is
blind by construction. Run on three disjoint render-clean pairs: median Spearman **ρ = −0.117**, all
three negative, all clearing a shuffled control, with the two fitted surfaces sitting a median
**3.5–5.0 voxels** apart. WEAK by the registered rule, and the registered prediction of WEAK was met.
**So normal displacement is a real contributor and not the mechanism** — it narrows what remains
rather than explaining it.

The bigger number came from a control the registration forced. **About half the ink-bearing bins hold
ink in only one arm**, yet those bins carry only **14–20% of the pair's ink**. That reconciles the
finding this whole line rests on: the count reproduces to 1.2% while placement reproduces at 0.70
because **the disagreement is concentrated in sparse, low-ink bins** while the bulk of the ink lands
where both arms agree. Dropping those bins silently would have hidden it.
`reports/normal_separation_contributes_but_does_not_explain.md`.

**39. Label snapping has no headroom on this dataset — closed by three cheap probes, not a study.**
villa names label quality "one of the main unwrapping bottlenecks" and proposes snapping labels onto
the CT-derived surface. Against `surf_sdt` — independent of the fit, so not circular the way selecting
on the fit's own residual was — label points have **IQR 0.0** and sit on a single value, against IQR
6.0 for random points in a field spanning 0–167: **12× more concentrated, 3.1× enriched.** The 11–18%
that are off-mode sit a median of **exactly 1.00 level-1 voxel** from an on-surface voxel, which is
the resolution floor and the signature of **quantisation, not drift**. The finest surface field
published is the one analysed, so no larger disk changes this; deriving a full-resolution one means
segmenting the surface, which is the unsolved problem labels exist to approximate.
`reports/label_snapping_feasibility_probe.md`.

**40. Part of the "placement instability" is the measurement, not the pipeline.** Fitting
`log|ink_A − ink_B| = a + b·log(mean ink)` per bin across three disjoint render-clean pairs gives
median **b = 0.723**, against **0.5** for pure counting noise and **1.0** for proportional scatter.
MIXED by the registered rule, prediction met. Scatter grows *faster* than √mean — so something
systematic moves ink in proportion to content — but *slower* than proportionally, so a meaningful
share of the disagreement is sparse bins flipping between present and absent with nothing having
moved.

The shuffled control, registered as a guard, answered a second question: **randomly paired bins give
b ≈ 1.0**, so proportional scatter is what *no relationship* looks like, and the observed 0.72 sitting
far below it on all three pairs shows the arms share real structure.

**Consequence for the headline: r ≈ 0.70 UNDERSTATES how much the pipeline agrees**, and should be
read as a property of the measurement as well as of fitting and flattening — a different binning
would move it. Nothing in findings 36–38 is overturned: averaging works whether the residual noise is
Poisson or geometric, and that was confirmed forward at two values of k.
`reports/the_disagreement_is_part_counting_noise.md`.

**41. The two seeds are not reading the same surface at different depths — they are reading two
different surfaces, each faithfully.** Registered prediction: a normal surface shift moves which of
the five retained depth layers the detector reads, which would scale with ink content and so explain
finding 40's `b = 0.72`. **Refuted, and the prediction missed.** Median Spearman ρ between per-bin
normal separation and layer-centroid shift is **−0.006**, two of three pairs inside their shuffled
null, with centroids differing by a median of **0.022 of a layer index** out of five and signed means
of +0.0000 / +0.0011 / +0.0007 — no systematic direction.

The registration had named this counter-case and called it the more interesting outcome: the render
resamples *relative to each arm's own surface*, so both centre their stack on their own sheet
regardless of where those sheets sit. **So the disagreement is not depth sampling; it is what the fit
decides the surface is.** Whatever scales with ink content must act before the detector.

That closes a third route. The ledger: scorer excluded (0.0009%), tangential slide excluded, depth
sampling excluded; normal separation present but small (ρ = −0.117); small-bin counting noise present
and substantial (b = 0.72); **the systematic remainder still unattributed.**
`reports/the_layer_route_is_refuted.md`.

**42. How much surface an arm puts in a bin dominates the ink disagreement — and the registered
mechanism does not explain it.** Ink is predicted on the flattened strip in *pixels* and attributed to
volume bins, so an arm whose parameterisation is locally denser contributes more ink pixels for the
same papyrus. Registered as the candidate for finding 40's systematic component. The slope of
`log(ink ratio)` on `log(density ratio)` is **+0.656, +1.252, +1.952** across the three pairs, all
clearing shuffled nulls, with genuine density variation to regress on (±0.23 at p5/p95).

**Median 1.252 reads DENSITY DOMINATES by the rule, and that verdict overstates it.** A pure density
artefact predicts exactly **1.0** — twice the samples, twice the ink pixels. Two slopes exceed that
and the three disagree by **3×**, so the association is real while the named mechanism accounts for
neither its size nor its instability. **Partial coverage** is the leading alternative — bins where a
surface does not extend get both fewer samples and less ink — and it was deliberately **not** tested,
because restricting to full-coverage bins after seeing a result that needs rescuing is the sweep these
registrations exist to prevent.

So the remainder is **no longer unattributed and not explained either.** The registration's own stated
limit is the one that bites: this cannot separate a difference in surface *extent* from a difference
in parameterisation *density*, since both change the sample count.
`reports/sampling_density_tracks_ink_but_not_proportionally.md`.

**43. The sample-count effect is interior, not an edge artefact — and `total_fg_pixels` is not
quietly counting fitted surface extent.** Finding 42 could not separate surface *extent* from
parameterisation *density*. Stratifying the slope by quartiles of `min(n_A, n_B)` separates them:
coverage effects must concentrate where one arm is sparse. **Q4 median s = +1.321, with no monotone
Q1→Q4 decline** — the slope is flat to rising, quartiles near-equal in size (559–720 bins).
**Coverage refuted.**

That is the negative worth having: the concern that villa's objective partly counts *how much surface
was fitted* rather than how well it reads is **not supported**. The ink ratio does not track the
sample ratio because one arm's surface stops sooner.

**The mechanism remains open.** `s > 1` persists in the best-covered bins on two of three pairs
(+1.32, +2.22), and pure density predicts exactly 1.0 — twice the samples over the same papyrus is at
most twice the ink pixels. Real, interior, strongly significant, unexplained by either candidate.
`reports/coverage_refuted_density_still_unexplained.md`.

## Closing note on the mechanism line

Six registered tests (findings 38–43) took the placement instability from "unexplained after two
failed attempts" to: **four routes excluded** — scorer, tangential slide, depth sampling, partial
coverage — **two contributors quantified** — normal separation ρ = −0.117, small-bin counting noise
b = 0.72 — and **one live factor that is real and mechanically unaccounted for**. All from artifacts
already on disk; no new compute.

**The last three predictions were all wrong**, each reasoned from the result before it. The
registrations held — verdicts fixed before the data, counter-cases written down, and one counter-case
turned out to be the finding — but a run of three says this mechanism is not yielding to the intuition
being applied to it. **The line is stopped here deliberately**, not exhausted: resolving the remaining
factor plausibly needs instrumenting the fit itself, which is a different and much larger undertaking
than analysing retained outputs, and proposing a fourth armchair mechanism is the thing the record
argues against.

Reproduce: `repro/spiral_render/`, `scripts/measure_winding_overlap.py`,
`scripts/analyse_seed_spread.py`. All from published artifacts.

## The noise floor line, 2026-09-19 to 21: where the variance actually lives

**44. Three arms were filed in the wrong code tier, and six replicate seeds sat unused.** Two
scripts disagreed on which tier `anchor10cov` belonged to; the correlation script's local prefix list
defaulted unknown arms to pinned and pooled three current-tier fits into the wrong population. The
ink range gave it away: 1.45M..2.95M is two populations, not one. Removing them reproduces the
published n=24 figure exactly, so the *report* was right and the *script* had drifted. Separately,
`measure_noise_floor.py` used three `curbase` seeds when nine were on disk. With all nine, the
current-tier CV goes **0.0263 → 0.0536** (df=11), the MDE at 3v3 from 6% to **12.3%**, and "current
code is quieter than pinned" dies (F(18,11)=0.92, p=0.84). The published interval contained the new
value — for the *third* time. Tier membership now lives in one place (`scripts/arm_tiers.py`) and an
unclassified arm raises. `reports/six_unused_seeds_double_the_current_floor.md`.

**45. Six manipulations, zero improved reading, one made it worse.** Across every registered study
with tree-matched controls: gap-expander −10.35% (p=0.002, HARMED); bootstrap, stripmatch, two
same-winding ablations and the anchor ablation all null, bounding 3–18%. The nulls are not equal —
same-winding-current bounds ±3% against a 12.3% design MDE, patch bootstrap only ±18% at a nominal
11.8%. The anchor study's registered control was fitted on a different villa tree than its
treatment; tree-matched, its ink estimate moves −0.86% → −5.49% (verdict still NULL) while its
geometry result strengthens. Every lever tried manipulates the geometry the fit solves for, and the
corpus correlation says that quantity does not predict ink (current tier r = −0.424, capped +0.11).
`reports/no_lever_has_improved_reading.md`, `reports/the_anchor_control_was_cross_tree.md`.

**46. The gap fix's ink loss is not duplicate removal; it pulls the surface 4 voxels inward.** Every
coverage measure is flat (strip area +0.45%, 3D surface −0.46%, duplication −3.3% n.s.) while ink
falls 10.35% — the same canvas yields less ink. The surface moves **radially inward 3.96 vx**, 24.5%
of a winding gap, in 10/10 scored windings with θ and z unchanged. **Corrected 2026-09-21:** an
earlier draft said villa's guard "fires" on villa's own fix. It does not — the guard is defined to
flag a *gain* in `total_fg_pixels` bought with a fraction *drop*, and the gap fix is a *loss* on both,
which the loop discards on the primary metric alone. The accurate statement is about the rule, not the
guard: `autoresearch.md` says a change that "lifts total while holding fraction roughly steady, is a
real win", and the converse — total and fraction both down — reads as a plain regression. On this
correctness fix that reading is wrong, and nothing in the rule can detect it.
`reports/the_gap_fix_does_not_remove_duplicated_coverage.md`,
`reports/the_gap_fix_moves_the_surface_radially.md`.

**47. The "1.42% pipeline determinism floor" was one draw, and its mechanism was wrong.** A second
same-mesh pair agreed to four pixels — 892× tighter — because it only re-*scored*. The scorer alone
moves a fixed strip by 0.0032%, 950× too small to produce 1.42%. The four measurements split cleanly:
scorer-only 0.0032%/0.0016%; flatten+render+score 1.42%/3.04%.
`reports/the_determinism_floor_rests_on_one_draw.md`.

**48. The lasagna flatten is stochastic: 3.04% ink and 7.15 voxels from identical input.** Two
renders differing in nothing but being run twice — same meshes, same pinned tree, byte-identical
code — give `total_fg_pixels` +3.04%, and their surfaces sit **7.15 vx apart** in the outer region
(0.535 vx inner). Three renders of geometry identical to float32 ULP span 5.32%, indistinguishable
from what six differently-seeded *fits* produce. So the "seed CV" always contained render noise and
was never decomposed — though **one pair cannot apportion it** (a "59%" share was computed, withdrawn:
its df=1 interval spans 3–100%). Villa's `autoresearch.md` already names "CUDA non-determinism"
alongside the seed; what it lacks is the location (flatten, not fit), the magnitude, and the switch.
Its `test_flatten_state_handoff.py` tests export determinism; this is optimisation determinism, and
it is the one that moves the ink count.
`reports/the_render_is_the_noise_floor.md`, `reports/the_flatten_lands_on_different_surfaces.md`.

**49. Holding the flatten fixed collapses the floor 2000×, to 24 pixels.** Reusing one flatten via
`RENDER_REUSE_FLATTEN=1` (`repro/spiral_render/reuse_flatten.patch`), two renders of a byte-identical
flat surface differ by **0.0014%**. The sampler is byte-deterministic (per-slice TIFFs identical by
md5); all 24 px is the scorer. Every stage is now attributed. **This applies only to studies that
branch from one surface** — fit comparisons need a flatten per arm and get no benefit from reuse.
`reports/holding_the_flatten_fixed_collapses_the_floor.md`.

**50. Displacing the flattened surface 4 voxels costs ink in both directions: −19.77% inward,
−4.48% outward.** The controlled version of finding 46, on one flat surface with the flatten held
fixed. IN loses **1.91×** what the gap fix lost from the same shift, so displacement alone
*over-explains* the fix's cost — the fix is not a pure radial shift. OUT had no prediction and lost
anyway: the fitted surface sits near a local maximum, steep inside, shallow outside. The first design
displaced *input* meshes and let the flatten re-solve; its own ZERO control exposed that the flatten
moves the surface 7.15 vx by itself, 1.8× the manipulation, and the design was declared invalid before
its treatment arms ran. `reports/displacing_the_surface_costs_ink_in_both_directions.md`,
`reports/the_radial_study_design_is_invalid.md`.

**51. The scorer reads texture, not brightness: IN renders brighter than ZERO and scores 20% less.**
Composite bright-pixel fraction IN 1.783% > ZERO 1.751% > OUT 1.435%, yet IN scores lowest. A
brightness reading of the inward loss has the wrong sign. `total_fg_pixels` is "how much looks like
writing to this model", not "how much ink the surface passed through". The first draft of this
finding was built on per-slice intensity profiles and would have concluded the window slid off the
layer; it was overturned only by checking whether the probe tracked the target.
`reports/the_scorer_reads_texture_not_brightness.md`.

**52. The flatten has no seed to set — and is bit-reproducible when asked.** No RNG exists on the
flatten path; every "seed" is a geometric init point. What it has is 174 scatter/atomic sites,
`grid_sample`, a fused Triton kernel, and no request for determinism. Two flattens under
`torch.use_deterministic_algorithms(True)` + `CUBLAS_WORKSPACE_CONFIG` produce **byte-identical
`x/y/z.tif`**, zero escaped-op warnings, at 9.5× flatten cost (~11 min vs ~4, against 2 h renders).
Reduction order is the *whole* cause. The registered prediction — a residual from the Triton
kernel — missed in the good direction. **Reproducible is not correct**: the deterministic surface
sits 6.6–7.3 vx from *both* stock surfaces, an arbitrary member of the same distribution. Available
as `FLATTEN_DETERMINISTIC=1` in `run_render.sh`; the first wiring of it was inert (path resolved after
a `cd`) and was caught by reading the flatten process's environment rather than its banner.
`reports/the_flatten_has_no_seed_to_set.md`, `reports/the_flatten_is_reproducible_when_asked.md`.

**53. With the flatten made deterministic, fit RNG dominates: seed CV 0.09 [0.06, 0.22].** Six
`curbase` seeds re-flattened under `FLATTEN_DETERMINISTIC=1` give a within-group CV of 0.0909
against 0.0742 on the same fits with stock flattens — indistinguishable, F(5,5) p=0.666. So the
flatten's 3% was never the binding constraint on fit comparisons; at 3v3 the floor is ~20% and it is
the fit's own RNG, with no cheap lever. Prediction (a CV in [0.030, 0.055]) missed, the fourth missed
magnitude in a week. `curbase_s6` survived re-flattening as top scorer by +13.2%: a genuine fit
outlier, kept in the floor. The deterministic switch remains decisive for surface-manipulation
studies (finding 49) and irrelevant for fit comparisons — which is most of the corpus and villa's
loop. `reports/fit_rng_dominates_the_flatten_was_never_binding.md`.

## Closing note on the noise line, superseding the one above

Findings 38–43 excluded four routes for the placement instability and left it unexplained. Findings
47–52 explain it: **the lasagna flatten is a stochastic optimiser whose run-to-run variation comes
entirely from CUDA reduction order**, landing on surfaces 7 voxels apart from identical input and
moving the count 3% and the placement far more. It can be switched off. The fit-only floor is now measured (finding 53): **0.09 [0.06, 0.22]**, fit RNG,
indistinguishable from the stock spread. The flatten was the whole explanation for *placement*
instability and *no* part of the binding constraint on *fit comparisons* — two different questions
with two different answers.

Three lessons this line paid for, each more than once: **quote the interval, never the point
estimate** (three retractions of one number, each new value inside the prior CI); **measure the floor,
never inherit it** (a study design invalidated by a floor from a report that named an unmeasured
mechanism); and **validate the probe against the target before interpreting it** (an intensity
analysis with the wrong sign, a `%/vx` law that failed three times in a day).
