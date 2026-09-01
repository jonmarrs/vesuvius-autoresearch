# Pre-registration: does GAP133's satisfaction gain reproduce on a second seed?

**Written 2026-09-01, before the second fit is run.**

## What is being confirmed, and why it needs confirming

`GAP133` (`model_gap_expander_num_windings` 130 -> 133, removing the shortfall warning) returned:

* its **registered** prediction FAILED: duplicate coverage 0.0909%, inside the honest range;
* an **unpredicted** observation: `satisfied_area_fraction` **0.8480**, against a four-seed mean of
  0.8396 with sd 0.00095. That is **+8.8 sd**.

I explicitly declined to predict satisfaction for that arm. That protects the result from having
been rationalised into a prediction, but it also means nothing was fixed in advance to stop me
reading noise as signal, and my own registered confound branch fires on exactly this movement. So it
is an observation, not a finding, until it reproduces.

## Arm

**GAP133S2**: identical to `GAP133` except `"optimizer_random_seed": 2`, matching the seed used by
the `seed02` honest fit. So the comparison is gap=133 at two seeds against gap=130 at four seeds,
with the seed values overlapping.

## Prediction, fixed now

**`satisfied_area_fraction` above 0.8404**, the top of the honest four-seed range. If the effect is
real at anything like the observed size, a second seed lands well clear of that band.

## Decision rule

* **above 0.8404**: reproduces. The config fix improves fit quality on villa's own diagnostic, and
  `reports/spiral_default_config_gap_expander_shortfall.md` gains a measured consequence.
* **inside 0.8382 to 0.8404**: does NOT reproduce. The 0.8480 was a single-fit excursion, the
  observation is withdrawn, and the config report keeps saying the consequence is unestablished.
* **below 0.8382**: the change is harmful on this measure, which would be reported as such.

Duplicate coverage is also recorded but is **not** under test here: GAP133 already returned a null on
it and that stands whatever this arm shows.

## Why two seeds is enough THIS time

`reports/two_seed_check_lets_through_one_in_six.md` found the two-seed check accepts 16.6% of null
changes on `total_fg_pixels`, whose CV is 0.1086. That objection does not apply here: the quantity
under test is `satisfied_area_fraction`, whose four-seed sd is **0.00095**, and the effect is 8.8 sd.
At that ratio two seeds is not marginal. Using the noise measurement to justify a sample size is the
point of having made it.

## Limits

Two fits against four, one dataset, one ROI. A reproduction shows the fix moves satisfaction, not
why, and satisfaction is villa's geometry diagnostic rather than the ink objective; `total_fg_pixels`
moved +4.1% in GAP133, inside its 21.7% floor and therefore uninterpretable.
