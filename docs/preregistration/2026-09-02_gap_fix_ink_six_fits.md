# Pre-registration: does the gap-expander fix change recovered ink, at power?

**Written 2026-09-02, while `gap133s3` is fitting and before either new outer render exists.** This
is the arm that decides finding 13.

## Why now

`reports/outer_winding_noise_floor.md` measured the outer floor at **8.4%**, well under the 21.7%
transferred from the inner windings, and the single-pair observation of **-11.03%** exceeds it. The
verdict was UNRESOLVED only because a floor from n=4 is an interval that straddles the observation.
The fix is not a better floor, it is more fits.

## Arms

* **BASE**, n=4: `baseline01`, `seed02`, `seed03`, `seed04`.
* **GAP**, n=3: `gap133`, `gap133s2`, `gap133s3`.

All differ only in `optimizer_random_seed`; GAP additionally sets
`model_gap_expander_num_windings` 130 -> 133. All measured on **w120-w129**, identical tooling,
villa pin `c935851c3`, serial-fold scoring.

**Disclosure, because it cannot be avoided: 5 of the 7 values are already known to me.** The four
BASE values and `gap133` are published in `reports/outer_winding_noise_floor.md` and
`reports/gap_fix_outer_windings_still_not_established.md`. Only `gap133s2` and `gap133s3` are new.
This registration therefore constrains the *test*, not my ignorance of the existing data, and that is
a real weakness of building on published arms rather than a formality. It is stated so a reader can
discount accordingly. What it cannot do is let me choose the rule after seeing the two new numbers,
because the rule and its code are committed before either render starts.

## Quality gates, fixed now

* **Within-arm** `satisfied_area_fraction` spread <= 0.01. Applied **per arm, never pooled across
  arms**: the arms are supposed to differ on this quantity, that difference being finding 12, so a
  pooled gate would be testing the very effect that defines the arms. (Pooled, the seven span 0.0098
  and would scrape through by 0.0002, which is the kind of accident worth designing out.)
* A fit failing its arm's gate is reported separately and not pooled.

**Control on the new fit:** `gap133s3` should land above the BASE maximum of 0.8404, as `gap133`
(0.8480) and `gap133s2` (0.8465) did. If it does not, the established geometry effect failed to
reproduce on a third seed, which is a finding in its own right and is reported as such; the ink arm
still proceeds, flagged.

## Primary test, fixed now

`total_fg_pixels`, villa's objective, on w120-w129.

* **Welch's t-test, two-sided, alpha = 0.05** on the 4 vs 3 values.
* Effect reported as the **relative difference of means** with a 95% CI.

**Assumption-free confirmatory check**, reported alongside and never in place of the above: complete
separation, all three GAP below all four BASE (or all above). Under the null this has probability
1/C(7,3) = **2.86%** in a named direction, 5.7% either way.

## Power, computed now and not after

At the measured outer CV of 0.0421, the standard error of the relative difference of means is
`0.0421 * sqrt(1/4 + 1/3)` = **3.2%**. Two-sided alpha 0.05 with 80% power therefore needs an effect
of about **9.0%** (`(1.960 + 0.842) * 3.2%`).

The single-pair observation was -11.03%, just above that. **So this arm is adequately powered for an
effect of the size already seen, and underpowered for anything much smaller.** A null must
accordingly be reported as "no effect larger than roughly 9%", never as "no effect".

## Decision rule

| outcome | conclusion |
|---|---|
| p < 0.05, mean difference negative | The fix **reduces** recovered ink on the windings it acts on. Established, with effect size. Finding 13 resolves against the fix. |
| p < 0.05, mean difference positive | The fix **increases** recovered ink. Established, with effect size. |
| p >= 0.05 | **Not established at this power.** Report the CI and state the smallest effect the arm could have detected. Finding 13 stays open and no further seeds are added without a new registration. |

`overall_fg_fraction`, `overall_line_score` and `overall_column_score` are reported for all seven
fits with the same test, **as secondary and clearly labelled**. `column` in particular is known to be
the noisiest quantity in this work (outer CV 0.2139); nothing about it is promoted to a claim here.

## Prediction, fixed now

**The difference of means is negative**, following the single-pair point estimate. I do **not**
predict significance. My last two registered predictions were wrong (the ink direction I declined to
call, and the outer noise level, which I called backwards), so this one is recorded to be scored, not
because I trust it.

## Cost

One fit (~2.5h, running), two outer renders (~2h each), two scorings (~15 min each). About 7 hours,
strictly sequential.
