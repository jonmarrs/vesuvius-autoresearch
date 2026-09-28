# The tightest null in the corpus was a property of its control seeds

**2026-09-27. Post-hoc, no new compute.** Script: `scripts/analyse_control_sensitivity.py`. Output:
`reports/control_sensitivity.json`. Tree evidence: `scripts/check_villa_copy_tree.py`, output in
`reports/villa_copy_tree.txt`. Found while following up the second inkdelta validation
(`reports/inkdelta_registered_intervals.md`).

## Which code each arm ran on

**Fits: all one tree.** Every current-tier fit script `cd`s into `villa-spiral-current`, a plain copy
made on 09-07. No file in it (outside `.venv`) is newer than 09-07 18:00. Villa's compare API lists
19 files under `spiral-fitting/`, `lasagna/` and `vesuvius/src/` that differ between `d8c5f488a` and
`be09a8503`. The copy's git blob hash equals the `d8c5f488a` blob for all 19. No `spiral-fitting/`
file differs between the two trees at all.

**Renders: split.** Each render work dir carries its own extracted tree. `curbase_s1-s3` hold
`d8c5f488a` for all 19 files. `curbase_s4-s9`, `nosamecur_s1-s3` and `anchor10cov_*` hold
`be09a8503` for all 19.

So `reports/the_anchor_control_was_cross_tree.md` had the stage wrong (it said "fitted"), and the
split it found is the render split that `reports/URGENT_render_code_changed_mid_corpus.md` raised.
`reports/rerender_test_verdict.md` measured it as +1.44% on one fit, inside 3.04% same-code render
noise. **Neither control is biased by a known effect. They are two samples of the same
configuration.**

## Result

| control (`curbase_*`) | n | CV |
|---|---:|---:|
| registered s1-s3 (old render) | 3 | **0.0124** |
| s4-s9 (render-matched) | 6 | 0.0742 |
| all nine | 9 | 0.0644 |

| study | control | effect | 95% CI | df |
|---|---|---:|---|---:|
| same-winding (current) | registered s1-s3 | +0.28% | [−2.56%, +3.13%] | 4.00 |
| | s4-s9 | −4.41% | [−12.18%, +3.37%] | 5.51 |
| | all nine | −2.89% | [−7.98%, +2.19%] | 9.40 |
| anchor 59→10 | registered s1-s3 | −0.86% | [−10.21%, +8.50%] | 2.35 |
| | s4-s9 | −5.49% | [−14.52%, +3.53%] | 6.80 |
| | all nine | −4.00% | [−11.79%, +3.80%] | 5.82 |

Every row is NOT RESOLVED.

## What it means

**The "no gain" half of both nulls is robust.** Under every control, removing same-winding
constraints or cutting anchors does not improve reading by more than +2.2% to +3.8%.

**The "no loss" half is not.** The same-winding interval's lower bound is −2.56% only because the
three registered control seeds agree to CV 0.0124. That is a fifth of the spread across all nine
(0.0644) and a sixth of the measured fit-only floor (0.0736). Against the six other seeds, or all
nine, the constraints could be buying **up to 8–12%** of the ink objective. The URGENT report
already warned about this set: "a df=2 spread has already been shown twice today to be unreliably
tight".

**This matters where the number was used as a bound on what constraints buy.** The September filing
says the two ablations "bound what winding constraints buy for reading". What the constraints buy is
the *negative* of the removal effect, so its bound is the lower end of the interval, the fragile end.
The filing now discloses this; see `tests/test_filing_numbers_match_sources.py`.

**No verdict changes.** The registered analyses used the control named before the data existed and
are reported as registered. This report adds the sensitivity; it does not replace them.

## Limits

* Post-hoc, with the choice of alternative controls made after the registered results were known.
  Quoting all three rows is the safeguard.
* `curbase_s6` is the corpus's high-ink seed (a fit effect, `docs/preregistration/2026-09-21_fit_only_noise_floor.md`).
  It inflates the s4-s9 spread, and it is a legitimate member of the configuration.
* The render trees of s4-s9 are not all `be09a8503` outside the 19 files checked. `curbase_s6`
  recorded `bfef6abe`, and s4, s5 and the treated arms recorded nothing. Only the
  `d8c5f488a`→`be09a8503` diff was checked.
