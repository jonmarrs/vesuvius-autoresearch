# The model holds at k = 2, the case the recommendation actually rests on

**2026-09-15.** Registered in `docs/preregistration/2026-09-15_two_seed_consensus.md`, written and
committed before any k=2 number was computed. The k=3 result is
`reports/consensus_retest_confirmed.md`.

## Why this existed

The confirmed study measured **k = 3**. The advice it licenses — *"a loop already paying for two seeds
should keep the consensus rather than the winner"* — is about **k = 2**, and villa's loop runs two
seeds. The recommendation rested on an untested point of the model. This tests it.

## Result

Render-clean arms only (`s4–s9`, all on `be09a8503`), so the confound the k=3 study had to bound does
not enter.

| comparison | r |
|---|---:|
| `s4+s5` vs `s7+s8` | 0.8606 |
| `s4+s6` vs `s7+s9` | 0.8612 |
| `s5+s6` vs `s8+s9` | 0.8329 |
| **mean** | **0.8516** |

Predicted **0.826**, registered band 0.796–0.856. **VERDICT: CONFIRMED.**

## The part the registration made me report

**Two of the three individual comparisons fall above the band** (0.8606 and 0.8612 against an upper
bound of 0.856); only `s5+s6` vs `s8+s9` sits inside it. The mean confirms, the parts lean high, and
the registration required the spread be quoted rather than buried.

Read honestly: **the independent-noise model slightly under-predicts at k = 2**, by +0.026 on the
mean. The same direction appeared at k=3 (+0.007 on the mean of 0.875 and 0.893 against 0.877), so
across both tests the model is a good predictor and mildly conservative.

The three comparisons **are not independent** — they reuse the same six arms in different groupings —
so the 0.833–0.861 spread understates true sampling variability and the mean carries nowhere near
three degrees of freedom. This is why the registration fixed the decision on the mean and demanded the
parts be shown.

## Where the curve now stands, all measured

| k | predicted | measured |
|---:|---:|---|
| 1 | 0.7040 | **0.7040** (15 pairs of `s1–s6`) |
| 2 | 0.8263 | **0.8516** (3 comparisons, `s4–s9`) |
| 3 | 0.8771 | **0.875 / 0.893** (A-vs-C, B-vs-C) |

Diminishing returns, as the model says: the jump from one seed to two is worth ~0.15 in correlation,
the jump from two to three about ~0.03.

## What this changes

**The k=2 recommendation is now supported by direct measurement rather than by extrapolation.** A loop
running two seeds and using them to pick a winner is discarding the better use of the same compute.

## What it still does not show

**Nothing about accuracy.** It measures whether two runs agree, not whether either is right. Two
confirmations of a reproducibility model do not make it an accuracy result, and the limit is unchanged
from k=3.
