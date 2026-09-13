# Pre-registration: a forward numeric prediction, and what would refute it

**Written 2026-09-13, before the three new fits are started.** This is the first test in this thread
where the model makes a **quantitative prediction in advance** rather than a directional guess, so
unlike the recent registrations it carries one.

## The prediction

`reports/averaging_seeds_buys_what_noise_theory_predicts.md` found that seed-to-seed ink-placement
differences behave like independent noise, replicated on three triplets at 1.10–1.15× the predicted
gain. Under that model, the reproducibility of a *k*-seed consensus against an independent *k*-seed
consensus is `r = 1 / (1 + 0.393/k)`:

| k | predicted r |
|---:|---:|
| 1 | 0.718 *(measured)* |
| 3 | **0.884** |

Allowing the observed ~12% excess on the gain, the band the model actually supports is
**0.884 to 0.904**.

## What is being run

Three new baseline fits, `curbase_s4/s5/s6`, seeds 4–6, **identical in every other respect** to
`curbase_s1..s3` — same dataset `spiral_s1`, same z-ROI, same current-code tree, same 30,000 steps.
Then render and score each, exactly as the existing arms were.

That gives two **independent** triplets of the same configuration: {s1,s2,s3} and {s4,s5,s6}. No arm
appears in both, which is what makes this a forward test rather than a re-analysis.

Cost ≈ 15–18 hours sequential. Disk 34 GB free against ~15 GB needed.

## Decision rule, fixed now

Primary quantity: **r between mean(s1,s2,s3) and mean(s4,s5,s6)** on the published 96 × 256 (z, θ) ink
map, shared axis, exactly as `compare_ink_in_volume.py` computes it today.

| observed r | conclusion |
|---|---|
| **0.86 – 0.92** | **Model confirmed.** Seed differences are independent noise and averaging is the right response to them. |
| **> 0.92** | Better than predicted. The noise is more averageable than the model says, and the ~12% excess is larger at k=3 than at k=2. |
| **0.80 – 0.86** | **Partial.** Averaging helps but less than independence predicts, implying some shared per-run structure. |
| **< 0.80** | **Model refuted.** A floor this high at k=3 means a systematic component that averaging cannot remove, and the k-seed projection must be withdrawn. |

## Validity gate, which must pass for any of the above to count

Learned from `reports/the_sanity_check_caught_a_false_positive.md`, where a decision rule would have
reported a significant artefact:

* **single-vs-single across the two triplets must land in 0.65–0.78.** This is the same quantity
  already measured within triplets (0.650–0.730). If cross-triplet singles fall outside that, the new
  arms are not comparable to the old and every number here is void, not null;
* each new arm must pass the **non-blank control** (nonzero fraction 40–55%, as all nine existing arms
  did);
* each new arm's `total_fg_pixels` must fall within the existing current-tier spread; an arm outside it
  is reported, not silently kept.

## What this cannot settle

* It tests the model at **k = 3 only**. The k = 5 and k = 8 rows of the published table stay
  projections.
* It says nothing about whether a consensus map is *more accurate* — only more reproducible. There is
  no ground truth on this ROI, and reproducibility is not correctness.
* Baseline configuration only.

## Prediction, on the record

**r = 0.884, with 0.884–0.904 the band the model supports.** I expect confirmation. If it lands below
0.80 the independent-noise result is wrong and the report built on it needs withdrawing, not
qualifying.
