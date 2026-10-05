# An unthresholded ink count is not shown to be a better objective for villa's loop

**2026-10-04.** Result of `docs/preregistration/2026-10-04_soft_count.md`, committed `17739f03` before any soft
count existed for a pinned or offset arm. Amendment 1 (`8709476e`) added a secondary analysis. Data:
`reports/soft_count_study.json` (registered) and `reports/soft_count_thresholds.json` (secondary). Scores:
`spiral_out/softcount_study/`; the published `ink_metric/` was never written to.

**Question.** villa's objective `total_fg_pixels` (H) counts pixels where its scorer's probability is ≥ 0.5. Would
the soft count S = Σ probability make keep/discard decisions less noisy, without losing sensitivity to a known
ink loss?

## Validity gates: all passed

* **V1.** All 35 re-scored arms reproduce their published `total_fg_pixels`, the largest deviation being
  0.0038%. The gate was 0.1%; the scorer's known GPU nondeterminism is about 0.003%.
* **V2.** A byte-identical re-render matches the zero-offset render: H −0.0104%, S −0.0024% (gate 0.1%).
* **V3.** Re-scored seed noise reproduces the published values: sd(ln H) 0.0423 (pinned), 0.0608 (current).

## Registered results

| question | statistic | 95% CI | verdict | prediction |
|---|---:|---|---|---|
| Q1, pinned seeds (df 10) | R = sd(ln S)/sd(ln H) = **0.907** | [0.563, 1.466] | no detectable difference | **P1 FAILED** |
| Q2, offset sweep | D = **1.606** | [0.994, 2.586] | no detectable difference | P2 held (barely) |
| Q1, current seeds (df 12) | R = **0.523** | [0.345, 0.910] | S less noisy | P3 held |

Seed noise, pooled within groups:

| tier | sd(ln H) | sd(ln S) |
|---|---:|---:|
| pinned | 0.0423 | 0.0384 |
| current | 0.0608 | 0.0318 |

**Recommendation rule: NOT MET.** It required Q1 on the pinned tier to say "S less noisy", and that failed. **S is
not recommended to villa.**

## The offset result needs one caveat (found when writing up)

Response to radial displacement of one pinned-tier surface, a(k) = Δln S / Δln H:

| offset (vx) | Δln H | Δln S | a | H in noise units | S in noise units |
|---:|---:|---:|---:|---:|---:|
| −4 | −0.2203 | −0.0793 | 0.36 | 5.20 | 2.06 |
| −2 | −0.0931 | −0.0439 | 0.47 | 2.20 | 1.14 |
| +1 | −0.0288 | −0.0376 | 1.30 | 0.68 | 0.98 |
| +2 | −0.0224 | −0.0360 | 1.61 | 0.53 | 0.94 |
| +3 | −0.0340 | −0.0726 | 2.13 | 0.80 | 1.89 |
| +4 | −0.0459 | −0.1020 | 2.22 | 1.08 | 2.66 |

* **S trades sensitivity by direction.** It responds about half as much as H when the surface moves inward,
  where H's loss is largest. It responds 1.3–2.2× as much when the surface moves outward, where H's loss is
  smallest. Split by direction (post hoc): inward D = 0.46, outward D = 2.06.
* **The registered statistic averages over this asymmetry.** It is a median over six offsets, four of them
  outward, so D > 1 comes from the outward side. That is a property of the offset set I registered, not of S.
  A symmetric sweep could have given D < 1.

## Secondary (Amendment 1, descriptive, no predictions): lower thresholds

villa's scorer already takes `--fg-threshold`. H_t counts probability ≥ t, from the same maps.

| t | R pinned | R current | D (offsets) |
|---:|---|---|---|
| 0.1 | 0.911 [0.553, 1.583] | 0.480 [0.197, 1.053] | 1.690 [0.972, 2.784] |
| 0.2 | 0.967 [0.595, 1.657] | 0.522 [0.212, 1.140] | 1.400 [0.817, 2.277] |
| 0.3 | 1.073 [0.660, 1.797] | 0.594 [0.236, 1.293] | 1.171 [0.700, 1.904] |
| 0.4 | 0.932 [0.867, 1.005] | 0.899 [0.866, 0.991] | 1.165 [1.080, 1.251] |
| 0.5 | 1.000 | 1.000 | 1.000 (consistency check: H from the float16 maps) |

* Low thresholds behave like S: no difference on the pinned tier, about half the noise on the current tier,
  with wider intervals.
* t = 0.4 is the only setting whose intervals mostly exclude 1: about 7–10% less seed noise, D 1.17. Its
  intervals are narrow because H_0.4 is almost H.
* **As registered, no threshold is recommended.** t = 0.4 was picked after seeing four options. It is a lead
  for a fresh test, not a result.

## What it means

* **For villa: no recommendation.** The registered primary test did not show S to be less noisy, and S's
  sensitivity depends on which way the surface is wrong.
* **The tiers disagree, and that is worth knowing.** On current code, the code villa's loop runs, S has about
  half H's seed noise (R 0.52 [0.35, 0.91]). On pinned code it does not. S's seed noise is similar in the two
  tiers (3.2–3.8%), while H's is larger on current code (6.1% vs 4.2%). So current code's extra noise sits in
  H's threshold crossings, not in the ink the fits produce.
* **A properly registered follow-up, if wanted:** current tier only, more seeds, a symmetric offset sweep on a
  current-tier surface, and S and t = 0.4 named in advance.

## Limits

One region (outer w120–129) and one offset surface, which is pinned-tier while the current tier has no offset
sweep. The offsets are asymmetric (4 outward, 2 inward). Neither metric is checked against labels here: the
labels sit on segment meshes, not spiral fits. The pinned and current groups differ in code, not only in seeds.
