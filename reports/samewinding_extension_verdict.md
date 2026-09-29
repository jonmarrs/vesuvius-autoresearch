# Same-winding constraints, six seeds a side: NULL, bounded at about ±9% on reading

**2026-09-29.** Registered in `docs/preregistration/2026-09-28_samewinding_extension.md` (2a3db396,
before the first fit; gate amendment 8debf0b9, before any new arm was rendered). Decided by
`scripts/analyse_samewinding_extension.py`. Output: `reports/samewinding_extension_verdict.json`.
Post-hoc companions: `scripts/samewinding_extension_posthoc.py` and `scripts/seed_as_shared_nuisance.py`.

## Result

All three new arms (`nosamecur_s4-s6`) passed all three gates: rendered on `be09a8503`, no integrity
FAIL against their sequence logs, strip area within ±10%.

| comparison (inkdelta 0.3.0, `--cv 0.0536` floor) | effect | 95% CI | decided by |
|---|---:|---|---|
| **primary: `nosamecur_s1-s6` vs `curbase_s4-s9` (render-matched)** | **+0.72%** | **[−8.13%, +9.57%]** | Welch, df 9.7 |
| secondary: vs all nine `curbase` | +2.32% | [−5.08%, +9.72%] | Welch |
| replication: new seeds only vs `curbase_s4-s9` | +5.85% | [−3.32%, +15.03%] | Welch |

**VERDICT: NULL.** Removing 5,413 same-winding constraints does not resolve a change in recovered ink.
By the registered wording, **the constraints buy at most 8.1% of reading on this ROI**. The interval is
two-sided: a gain from removing them of up to 9.6% is not excluded either. The replicates were noisier
than the floor, so Welch decided every row and the floor did not bind.

| arm | `total_fg_pixels` | strip area vs control mean |
|---|---:|---:|
| nosamecur_s1 / s2 / s3 | 2,893,440 / 2,925,553 / 2,852,335 | +1.8% / −4.0% / −2.2% |
| **nosamecur_s4 / s5 / s6** | **3,160,441 / 3,101,626 / 3,339,905** | **+5.2% / +5.2% / −2.9%** |
| curbase_s4 … s9 (control) | mean 3,023,710, CV 0.0742 | — |

## The prediction, scored

Registered blind: NULL, a point estimate between −1% and −5%, and a lower bound between −6% and −10%.

* NULL: **met**.
* Lower bound −8.13%: **met**.
* Point estimate +0.72%: **missed**, outside −1% to −5%. The three new seeds landed high.

## Disclosure: the gate amendment decided two arms

`nosamecur_s4` (+5.18%) and `s5` (+5.24%) **would have failed the originally registered ±5% strip-area
gate.** It was widened to ±10% on 09-28 while the first fit was running and before any new arm was
rendered. The reasons, recorded then: the 15 existing current-tier arms already spanned −4.0% to
+2.3%, and the gate's remedy (re-rendering) cannot change an area the fit sets. That is a real
pre-data amendment, but it decided two of the three arms, so the reader should know.

Without those two arms the primary comparison is −0.69% [−12.26%, +10.88%] (`s1-s3` + `s6` vs
`s4-s9`). It is still NULL and wider. The verdict does not depend on the amendment.

## A lead that did not survive its own test

Same-seed ink correlates strongly across the ablation: r = 0.916 over seeds 1–6. A paired analysis
would give +0.97% [−2.05%, +3.99%], about three times tighter. That would be a design win if the fit
seed were a shared nuisance across datasets. It was noticed in these data, so before writing it up it
was tested on data that played no part in noticing it, using only arms whose seed is verified from
their fit scripts:

| layout | F(seed) | p |
|---|---:|---:|
| pinned tier: nosame / boot090 / rand090 / strip090 × seeds 1–3 | 0.23 (2, 6) | 0.80 |
| current tier: curbase / nosamecur / anchor10cov × seeds 1–3 | 0.26 (2, 4) | 0.79 |

**Seed explains nothing across configs.** The r = 0.916 rests on seeds 4–6, above all on seed 6,
which is high in both configs. The paired interval is not a result and is not used. Paired-by-seed
designs are not a free power gain here.

What remains unexplained, and is not pursued: in both current configs, seeds 4–6 sit above seeds 1–3.
For `nosamecur` the new triplet is +10.7% over the old one, about 2.5 floor-sd of a triplet mean. The
two triplets were fitted and rendered weeks apart, so seed and date cannot be separated here.

## What it changes

* **The filing.** The September SUBMIT and DRAFT now quote the six-seed result. They also drop the
  09-27 sentence "both rule out a *gain*", which was already too strong for the anchor interval
  (+8.50% upper) and is now false for same-winding (+9.57%). `tests/test_filing_numbers_match_sources.py`
  binds the interval and bans the withdrawn sentence.
* **The claim.** "Winding constraints buy at most ~8–10% of reading here, in either direction" is now
  measured with six seeds a side on a matched render tree. It is no longer carried by three unusually
  tight control seeds.

## Limits

One ROI, one dataset, w120–w129. `total_fg_pixels` is a count, not legibility. The new triplet sits
high for reasons this design cannot separate from date. The control's own CV (0.0742) includes the
corpus's high-ink seed, `curbase_s6`.
