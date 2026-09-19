# The loop's knobs do not move strip extent — the pilot's question, answered with no compute

**2026-09-19.** Answers the question `docs/preregistration/2026-09-19_strip_extent_pilot.md` was
launched to size and then abandoned over
(`reports/the_bounds_knob_clips_it_does_not_reshape.md`). Existing arms, zero new compute.

## The comparison that was already on disk

Seven arms share the **w010–011** winding range — a different region from the w120–129 arms, and one
where four genuinely distinct config manipulations were run, two of them zeroing a loss weight
outright:

| arm | manipulation | `total_pixels` | `total_fg_pixels` |
|---|---|---:|---:|
| `seedarm_03` | seed 3 only | 26,666,600 | 221,576 |
| `seedarm_04` | seed 4 only | 26,785,200 | 250,936 |
| `seedarm_densespace0` | `loss_weight_dense_spacing` 12 → **0** | 26,938,400 | 205,455 |
| `seedarm_gap133` | gap expander 130 → **133** | 26,782,400 | 249,913 |
| `seedarm_gap133s2` | gap expander 133, seed 2 | 26,636,400 | 214,923 |
| `seedarm_margin0` | `output_winding_margin` → **0** | 26,843,200 | 248,365 |
| `seedarm_minspace0` | `loss_weight_min_spacing` 2 → **0** | 26,578,300 | 242,128 |

**Strip area spans 1.35% across all seven. Seeds alone account for 0.44%. Ink spans 22%.**

## What that settles

**The manipulation the six-arm study needed does not exist among the knobs tried.** Turning the
dense-spacing loss off entirely, turning the min-spacing loss off entirely, zeroing the winding
margin, and changing the gap expander each move strip extent by **no more than about three times what
reseeding does** — and reseeding moves it by half a percent.

So the study is not merely hard to size; **there is nothing to vary.** That is why the arm-level slope
test was uninformative, and no amount of care with the statistic would have rescued it: the predictor
does not move because nothing the loop tunes moves it.

**And it strengthens the negative.** `reports/the_strip_area_test_was_uninformative.md` could only say
"no detectable relationship between area and ink, weakly". This says something better founded: villa's
loop cannot raise `total_fg_pixels` by enlarging the strip, **because its knobs do not enlarge the
strip.** The objective is not purchasable with surface area by any means tested here.

## Why this was available all along

These seven arms have been on disk since 2026-08-31. The pilot spent 40 minutes of GPU and an hour of
design to ask a question that four already-run config variants had answered.

The reason I did not see it: I was reasoning about the **w120–129** arms, where the only variation is
incidental (6.5%), and did not look for a region where deliberate config variants already existed.
**`seedarm_*` is a different naming prefix from `outer_*`**, so the arms did not appear in any of the
listings I had been building all week.

## Limits

* **Four config manipulations, not 122.** This does not prove no key moves extent; it shows that four
  aggressive ones — two of them zeroing a loss term — do not.
* One winding range, pinned tier (`6847063f`).
* `output_winding_margin → 0` is the closest thing here to a deliberate extent knob, and it moved area
  by 0.6% against the seed-only pair. If any key were going to do it, that was a reasonable candidate.
