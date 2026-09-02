# The outer windings are QUIETER than the inner ones, and that makes yesterday's margin wrong

**2026-09-02.** Registered in `docs/preregistration/2026-09-01_outer_winding_noise_floor.md`, with
`scripts/analyse_outer_floor.py` written before any of the three renders finished.
**My registered prediction is a MISS**, and the miss is the finding.

## Why this was measured

`reports/gap_fix_outer_windings_still_not_established.md` judged two **outer-winding** numbers against
floors measured on the **inner** windings, and disclosed that transfer as a limit rather than
defending it. All four honest seeds already carried w120-w129 meshes, so the outer floor cost three
renders and no new fits.

## Result

Four honest seeds, w120-w129, pooled (`satisfied_area` spread 0.0022, inside the 0.01 band):

| fit | `total_fg_pixels` | strip px | `line` | `col` |
|---|---:|---:|---:|---:|
| baseline01 | 1,789,206 | 352,174,200 | 0.346 | 0.243 |
| seed02 | 1,732,741 | 368,730,300 | 0.364 | 0.154 |
| seed03 | 1,620,364 | 361,393,800 | 0.336 | 0.163 |
| seed04 | 1,682,825 | 356,178,400 | 0.358 | 0.203 |

| metric | CV outer | CV inner | floor outer | observed | verdict |
|---|---:|---:|---:|---:|---|
| `total_fg_pixels` | **0.0421** | 0.1086 | 8.4% | -11.03% | **UNRESOLVED** |
| `overall_line_score` | 0.0356 | 0.0342 | 7.1% | -2.39% | reported only |
| `overall_column_score` | 0.2139 | 0.1343 | 42.8% | -46.57% | CANDIDATE |

## The prediction was wrong in the direction that matters

I registered that the outer CV of `total_fg_pixels` would be **higher** than the inner 0.1086, on the
reasoning that half the ink density on a larger canvas makes the same absolute jitter a larger
relative one. It is **0.0421**, two and a half times **quieter**. Recorded as a miss.

The reasoning failed because ink density is not the only thing that changes. `line` is essentially
unchanged between regions (0.0356 against 0.0342), so this is specific to the objective, and the
plausible mechanism -- more windings averaging over more independent surface -- is a reading, not
something measured here.

## What this does to the published conclusion

**The 21.7% floor used yesterday is too wide for this region.** The right point floor out there is
**8.4%**, and the observed **-11.03% exceeds it**. Yesterday's report described that delta as sitting
"far inside" its floor. That description was wrong; on the point estimate alone the rule returns
REVERSES.

It is nonetheless **UNRESOLVED**, because the floor from n=4 is an interval, not a number: 95% CI
**4.8% to 31.4%**, which straddles 11.03%. The registered rule resolves only when the whole interval
sits one side of the observation.

So the earlier conclusion survives *in letter* -- the ink effect is still not established -- and its
**stated margin was wrong**. The honest position is that -11.03% is **borderline, not comfortably
null**, and a properly powered arm could plausibly find the gap fix costs ink in the windings it acts
on. That is a materially different thing to report than "uninterpretable, far inside the floor", and
it moves the six-fit arm from a formality to the thing that decides it.

Both decision rules agree here, which is worth recording: the "factor of two" band discarded before
the data would also have returned UNRESOLVED. The rule change did not manufacture this answer.

## The column observation survives, weakly, and my registration was inconsistent

`overall_column_score` has outer CV **0.2139**, floor 42.8%, just under the observed 46.57%, so under
the rule as registered it **survives as a candidate** -- licensing a properly registered arm, not a
claim.

**Disclosed rather than smoothed over:** I registered an *interval* test for `total_fg_pixels` and a
*point* test for the column, and did not notice the asymmetry until the verdicts printed. Applying
the interval test the column would be unresolved too, and by a wide margin: its floor's 95% CI is
**24.2% to 159.5%**. The column is the noisiest quantity measured anywhere in this work, and
"survives" here means "not excluded by a test that could barely exclude anything".

### Why the column score is the noisy one, from the detail the scorer already writes

`col_score` combines two terms, and they behave completely differently across the four seeds:

| quantity | mean | CV |
|---|---:|---:|
| `col_score` | 0.1906 | **0.2139** |
| `col_width_conformity` | 0.2343 | **0.2152** |
| `col_gap_contrast` | 0.8133 | **0.0082** |
| `col_median_width_px` | 271.5 | 0.0826 |
| `line_median_pitch_px` | 211.3 | 0.0288 |

`col_score`'s CV (0.2139) is essentially `col_width_conformity`'s (0.2152); the gap-contrast term is
one of the *steadiest* things measured here at CV 0.0082. So the whole of the column score's noise is
the conformity term.

And conformity is noisy for a structural reason: it asks what fraction of detected columns fall in
**722 to 977 px** (850 +/- 15%), while the detected median column width out here is **240 to 293 px**
— about **3x narrower than the target**. A statistic that counts how much of a distribution lands in
a band three widths away from its centre is a tail statistic, and tail statistics are noisy. The line
side shows the same mismatch (expected pitch 80-120 px, detected 204-218 px) but is far steadier,
CV 0.0288.

**What this does and does not establish.** It explains the noise mechanically, from numbers the
scorer already writes, and it strengthens the case for treating the -46.57% column observation as
weak: the quantity is dominated by a term evaluated far outside its design range. What it does *not*
settle is which side is wrong — whether the outer windings genuinely carry ~270 px columns, or the
detector mis-segments them out there. Either way the score is being read outside the regime it was
tuned for, and `col_gap_contrast` looks like the more informative half for this region.

## A caution for reading `total_fg_pixels` out here

Strip area is itself seed-varying: **352.2M to 368.7M px, CV 0.0199**, across fits differing only in
`optimizer_random_seed`. So part of the objective's outer CV is canvas, not ink. Dividing it out does
not rescue the comparison -- `overall_fg_fraction` has CV **0.0521**, *higher* than `total_fg_pixels`'
0.0421, and gap133's deficit on that measure is -13.48% against a 10.4% floor. The verdict is the
same either way, which is the useful part: the answer does not depend on which of the two is chosen.

**Part of that canvas spread is not seed variation at all.** `gap133s2`'s render was OOM-killed and
re-run, which re-flattened the *identical* mesh set with identical code on the same machine, and gave
a different grid:

| flatten of gap133s2 | flat grid |
|---|---|
| first attempt | 8268 x 447 |
| after the retry | 8267 x 452 |

**5 rows in 447, 1.1%**, from re-running the pipeline rather than from changing anything. That sits
inside the 1.42% pipeline re-run floor already on record, corroborating it from an independent angle
-- at the mesh level rather than the metric level. Against a canvas CV of 0.0199 across seeds, it
means a substantial share of what looks like seed-driven canvas variation is flatten
nondeterminism instead. One re-flatten pair bounds nothing precisely, so this is a demonstration, not
a decomposition.

Worth noting because it is counterintuitive: **normalising by canvas ADDS noise here rather than
cancelling it.** A ratio sheds variance only when numerator and denominator move together, and these
do not. Across the four seeds `corr(total_fg, canvas)` is **-0.29**, and the observed ratio CV
(0.0521) sits above even the independence prediction of `sqrt(0.0421^2 + 0.0199^2)` = 0.0466. So a
bigger canvas does not bring proportionally more ink with it.

**The correlation itself is not claimed.** At n=4 an r of -0.29 has a 95% interval spanning almost
the whole range, so the mechanism -- whether canvas and ink are genuinely anti-correlated or merely
uncorrelated -- is unestablished. What *is* measured is the practical consequence: `total_fg_pixels`,
villa's own objective, is the better-behaved of the two out here, and swapping to `fg_fraction` on
the intuition that normalising must help would make a comparison noisier, not cleaner.

## Limits

Seed noise within one config, one dataset, one ROI, one winding decade. It fixes the yardstick and
says nothing about whether the gap fix helps ink. A CV from n=4 is uncertain by a factor of 0.57x to
3.73x, which is exactly why the verdict is UNRESOLVED rather than a number. Three of the four arms
were rendered and scored in a single overnight run on one machine; the scorer's own re-run
nondeterminism (0.0032%) is negligible beside these spreads.

**What answers it:** three seeds per arm on baseline and gap133, six fits, about nine hours of
fitting plus roughly two hours per arm of outer render and score.
