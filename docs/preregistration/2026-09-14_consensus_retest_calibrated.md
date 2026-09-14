# Pre-registration: the consensus forward test, with the gate calibrated from measured spread

**Written 2026-09-14, before any new fit starts.** Replaces
`2026-09-13_consensus_forward_prediction.md`, which returned **VOID** because its ink gate was
calibrated from three arms (CV 0.0124) and applied to six (CV 0.0740), rejecting `curbase_s6` — an arm
with no independent sign of being wrong. `reports/consensus_forward_verdict.md` has that post-mortem.

## The two constraints this design has to satisfy

**1. It must be forward.** The comparison `{s1,s2,s3}` vs `{s4,s5,s6}` has already been computed and
seen (0.876). Re-running it with a wider gate would be choosing a threshold to admit a number I
already know. **That comparison is retired and will not be re-reported as a test.**

**2. The gate must come from measured spread, fixed before any comparison.** Not from a guess, and not
from the arms it will judge.

## Design

Fit **three new arms**, `curbase_s7/s8/s9` (seeds 7–9), identical to `s1–s6` in every other respect.
That creates **triplet C**, and with it **two comparisons neither of us has seen**:

* **A vs C** — `mean(s1,s2,s3)` against `mean(s7,s8,s9)`
* **B vs C** — `mean(s4,s5,s6)` against `mean(s7,s8,s9)`

Two independent forward tests for the cost of three fits (~18 h), rather than six fits for one.

## The prediction, recalibrated from all six existing arms

Single-vs-single over **all 15 pairs** of `s1–s6`: **r = 0.7040** (range 0.630–0.808). Under the
independent-noise model that implies a noise/signal ratio of 0.4204 and:

| k | predicted r for k-consensus vs k-consensus |
|---:|---:|
| 1 | 0.704 |
| 2 | 0.826 |
| **3** | **0.877** |

**Predicted: r = 0.877 for both A-vs-C and B-vs-C.** The earlier registration predicted 0.884 from
three arms; 0.877 is the same model on better data.

## Decision rule, fixed now

Applied to **each** comparison separately, and both are reported whatever they show:

| observed r | conclusion |
|---|---|
| **0.85 – 0.91** | **CONFIRMED** — the independent-noise model predicts k-seed consensus reproducibility |
| **> 0.91** | better than predicted |
| **0.79 – 0.85** | **PARTIAL** — averaging helps less than independence predicts |
| **< 0.79** | **REFUTED** — a floor averaging cannot remove; the k-seed projection is withdrawn |

Band width ±0.033 around 0.877 mirrors the previous registration's ±0.03; it is not widened to make
confirmation easier.

**If A-vs-C and B-vs-C disagree** (one confirms, one refutes), that is reported as **INCONSISTENT** and
neither is claimed. Two comparisons exist to make that visible, not to let me pick one.

## Validity gate, calibrated from the six existing arms

Ink of each new arm must fall inside the **95% prediction interval for a new draw** from `s1–s6`
(mean 3,019,001, sd 223,329, n=6, t=2.571):

> **2,398,918 – 3,639,084**

That interval contains all six existing arms **including `s6`**, which is the point: a gate that
rejects an arm the process actually produces is a broken gate, and that is what voided the last run.
It is ±20.5%, wide enough to catch only an arm that is not from this process at all — a failed render,
a wrong dataset — which is the only thing a validity gate should catch.

Also required, unchanged:

* non-blank control 40–55% nonzero for each new arm;
* every arm rendered from a ref verified **interchangeable** with `be09a8503` by
  `scripts/check_render_equivalence.py`, recorded via `<workdir>/VILLA_SHA`. **`VILLA_REF` is pinned
  for the whole run** so a mid-study fetch cannot split it, which happened twice on 09-11 and 09-14.

## What this cannot settle

* k = 3 only. The k = 4+ rows stay projections.
* Reproducibility is not correctness. There is no ground truth on this ROI.
* Baseline configuration only.

## Prediction, on the record

**r = 0.877 for both comparisons**, band 0.85–0.91, refuted below 0.79. I expect confirmation — the
retired comparison landed at 0.876 against a 0.877 model prediction — and that expectation is exactly
why the band, the gate and the INCONSISTENT rule are all written down first.

---

## Amendment, 2026-09-14, made while `curbase_s7` is at 76% and triplet C does not exist

Smoke-testing `scripts/analyse_consensus_retest.py` before the data lands — it had never
been executed, and a crash after 18 hours of compute is the expensive kind of mistake —
turned up a defect in the gate, and a second, smaller discrepancy in its constants.

**The gate was applied to the wrong quantity.** `GATE_INK` was computed from
`total_fg_pixels` in `<arm>/ink_metric/metrics.json`, whose `s1–s6` mean is **3,019,001
exactly**, reproducing the registered constant. The module gated `H.sum()` from the volume
map instead. That runs about **0.2% lower on every arm**, because the histogram's validity
mask drops non-finite and non-positive coordinates before binning.

Against a ±20% gate this changes nothing — every arm passes either way, and the tightest
margin is **14.9% of the gate width** — but calibrating on one measurement and applying it
to another is precisely what voided the previous run. It is fixed rather than tolerated:
the gate now reads `total_fg_pixels`, `H.sum()` is still reported as a diagnostic, and the
module refuses outright if an arm is rendered but has no metrics file, rather than falling
back to the other quantity. `tests/test_consensus_gate_quantity.py` holds the two apart and
was confirmed to fail when the defect is reintroduced.

**The registered bounds carry a rounding slop of about 100 units.** Recomputing the interval
gives `2,398,817–3,639,184` against the registered `2,398,918–3,639,084`; the original
computation rounded `sqrt(7/6)` to 1.07994 instead of 1.08012. That is **0.008% of a
1.24M-wide gate**. The registered constants are kept unchanged. Adjusting a pre-registered
threshold by 0.008%, when no arm sits within 14.9% of an edge and no verdict could turn on
it, would be tampering with a registration for no gain.

**Nothing about the prediction, the band, the retirement of A-vs-B, or the INCONSISTENT rule
is touched.** The prediction stands at **r = 0.877 for both comparisons, band 0.85–0.91,
refuted below 0.79**.
