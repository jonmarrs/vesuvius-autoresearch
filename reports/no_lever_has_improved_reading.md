# Six manipulations, none improved reading, and the one that moved it made it worse

**2026-09-19.** A synthesis, not a new measurement: every number comes from arms already scored.
`scripts/survey_manipulation_effects.py`, output in `reports/manipulation_effects_survey.json`.

Each study below was registered, run and reported on its own. None of them can answer the question
this asks: **across everything we have tried, has anything improved the endpoint villa scores?**

## The table

Endpoint `total_fg_pixels`, w120-w129. Controls are **tree-matched** (see below). MDE is the
design-stage floor for that tier; the CI is what these data actually exclude.

| study | n | effect | p | 95% CI | MDE | verdict |
|---|---|---:|---:|---|---:|---|
| gap-expander fix | 6v6 | **−10.35%** | 0.002 | [−15.7%, −5.0%] | 8.3% | **HARMED** |
| patch bootstrap | 3v3 | −0.83% | 0.892 | [−18.4%, +16.7%] | 11.8% | null |
| stripmatch | 3v3 | +3.08% | 0.519 | [−9.2%, +15.4%] | 11.8% | null |
| same-winding ablation (pinned) | 6v3 | −1.74% | 0.611 | [−10.3%, +6.8%] | 10.2% | null |
| same-winding ablation (current) | 3v3 | +0.28% | 0.796 | **[−2.6%, +3.1%]** | 12.3% | null |
| anchor ablation 59→10 | 6v3 | −5.49% | 0.192 | [−14.5%, +3.5%] | 10.6% | null |

**Six manipulations. Zero improved reading. One moved it, downward.**

## Two things that make the table trustworthy

**It reproduces an independent result exactly.** The gap-expander row computes −10.35%, 95% CI
[−15.7%, −5.0%], against `reports/gap_fix_costs_ink_established.md`'s independently derived
"−10.35%, 95% CI −15.68% to −5.03%". The machinery is not inventing effects.

**Controls are tree-matched, and for one study that is not the registered control.** The anchor
ablation's registered baseline (`curbase_s1-s3`) was fitted before a villa bump and its treatment
after; using the tree-matched `curbase_s4-s9` moves its ink estimate from −0.86% to −5.49%.
`reports/the_anchor_control_was_cross_tree.md`.

## The nulls are not equal, and the MDE column understates two of them

MDE answers "what could this design have seen"; the CI answers "what do these data exclude". They
diverge sharply here:

* **same-winding (current) bounds ±3%** despite a 12.3% MDE — those arms happened to land tight, so
  that null genuinely excludes small effects. It is the strongest null in the corpus.
* **patch bootstrap bounds only ±18%** at the same nominal 11.8% MDE. That null excludes almost
  nothing and should not be cited as evidence the avenue is dead.

Quoting the design-stage MDE for both would have called them equally informative. They are not.

## What this does and does not say

**It does not say the spiral fit cannot be improved.** Every null is a bound, and the loosest of them
admits an 18% gain. Nor does it cover levers nobody has tried.

**It does say the levers we chose have not worked, and that they share a shape.** Patch selection,
constraint sets, anchor counts, gap handling — all manipulate the *geometry the fit is solving for*,
and the corpus-wide correlation says that quantity does not predict ink
(`reports/geometry_ink_correlation_corpus.md`: current tier r = −0.424, a positive relationship
capped at +0.11). **A programme of geometry manipulations searching for a reading gain is searching a
space the data say is uncorrelated with the target.** Six results at zero is what that predicts.

**The one manipulation that did move reading moved it down, and it was villa's own correctness fix.**
The gap-expander change is a genuine geometry improvement (130→133 windings) that costs ~10% of the
ink objective. That is the sharpest single statement this corpus supports: on this pipeline,
correcting the geometry and reading the text are not the same goal.

## Limits

One dataset (`spiral_datasets/PHercParis4`), one ROI, one frozen scorer, w120-w129. `total_fg_pixels`
is an area count, not legibility — it cannot distinguish more text from more false positives, which
is exactly why the gap-expander row needs the geometry context above to interpret. Studies differ in
seed count and tier; the table is six separate comparisons, not one experiment.
