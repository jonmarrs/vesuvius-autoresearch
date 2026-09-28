# inkdelta reproduces every registered interval, and the one miss was in the pre-registration

**2026-09-27.** Second validation of [inkdelta](https://github.com/jonmarrs/inkdelta) 0.2.0.
Registered in `docs/preregistration/2026-09-27_inkdelta_registered_intervals.md` (committed
c29d8489, before the tool ran on these arms). Runner: `scripts/validate_inkdelta_intervals.py`.
Output: `reports/inkdelta_registered_intervals.json`.

## Result: 5/6 as registered, 6/6 on the registered analyses' own direction

| # | study | required | inkdelta | pass |
|---|---|---|---|:---:|
| 1 | gap-expander, 6v6 | RESOLVED (−), −10.35% [−15.68%, −5.03%], df 8.89 | identical | ✅ |
| 2 | patch bootstrap, 3v3 | NOT RESOLVED, −0.83% [−18.35%, +16.69%], df 3.11 | identical | ✅ |
| 3 | STRIPMATCH, 3v3 | NOT RESOLVED, −3.80% [−20.73%, +13.14%], df 3.56 | NOT RESOLVED, **+3.95% [−13.65%, +21.55%]**, df 3.56 | ❌ |
| 4 | same-winding (pinned), 6v3 | NOT RESOLVED, −1.74% [−10.27%, +6.79%], df 4.41 | identical | ✅ |
| 5 | same-winding (current), 3v3 | NOT RESOLVED, +0.28% [−2.56%, +3.13%], df 4.00 | identical | ✅ |
| 6 | anchor ablation, 3v3 | NOT RESOLVED, −0.86% [−10.21%, +8.50%], df 2.35 | identical | ✅ |

"Identical" means verdict, rel/lo/hi to 4 d.p. and df to 2 d.p. No case carried a FAIL finding. The
warnings were the expected ones: `SCORER_SNAPSHOT_UNRECORDED` everywhere, and `LOG_NOT_FOUND` for
the chain-rendered pinned arms.

**Case 3 fails as registered, and the fault is mine, not the tool's.** `scripts/analyse_stripmatch.py`
computes (BOOTSTRAP − STRIPMATCH) / STRIPMATCH, because its question is whether BOOTSTRAP beats its
control. I transcribed the direction as A = BOOTSTRAP, B = STRIPMATCH. The equal df and the swapped
means show it. With the registered direction (A = STRIPMATCH, B = BOOTSTRAP) inkdelta gives
**−3.80% [−20.73%, +13.14%], df 3.56, exactly**. That rerun is post-hoc and labelled so. The table in
the prereg is not edited; a dated amendment records the error.

Taken with the first validation's case 2, inkdelta has now reproduced **seven registered intervals**.
They span both tiers, 3v3/6v3/6v6 designs and Welch df 2.35–8.89, all to 4 d.p. The stdlib t
quantile and the run discovery are not a source of error on this corpus.

## What the validation found beyond the tool

The miss sent me to every other place that quotes STRIPMATCH. One of them was wrong in a way the
registered reports are not:

* **`scripts/survey_manipulation_effects.py` (09-19) published a "stripmatch" row of +3.08%.** That
  row compared STRIPMATCH against RANDOM, two *controls*, not the registered BOOTSTRAP-vs-STRIPMATCH
  test. Corrected to −3.80%.
* The same survey had swapped the anchor study's control to `curbase_s4-s9` as "tree-matched", and
  left the same-winding (current) study on `curbase_s1-s3`, although both have the same split. That
  opened a further check, `reports/control_sensitivity.md`. It found:
  * the split is at the render, not the fit;
  * the render change had been measured inert;
  * the same-winding (current) "tightest bound in the corpus", [−2.56%, +3.13%], is a property of
    three unusually tight control seeds.

None of this changes a verdict. Every study that was null is still null. The one HARMED result
(gap-expander) reproduces exactly. No manipulation improved reading.

## Limits

inkdelta's Welch formula is algebraically the one the registered scripts use, so this validates
discovery, arithmetic and the stdlib quantile. It is not an independent check of the statistics.
The arms were chosen as "every registered replicated Welch interval on `total_fg_pixels`". The rerender and
consensus studies use single-run or correlation designs and are outside that set.
