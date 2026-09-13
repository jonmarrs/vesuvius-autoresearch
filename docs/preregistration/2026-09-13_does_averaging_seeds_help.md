# Pre-registration: how much reproducibility does averaging seeds buy?

**Written 2026-09-13, before computing anything.**

## The question, and why it is practical rather than mechanistic

`reports/ink_placement_in_volume.md` established that fits differing only by RNG seed agree on ink
placement at r ≈ 0.70 in the scroll's frame. Two attempts to explain *why* have now failed
(`ink_offsets_are_not_coherent.md`, `the_sanity_check_caught_a_false_positive.md`). This asks
something that does not need the mechanism:

**If a single run's ink map is only ~0.70 reproducible, does averaging several runs give a map that is
more reproducible — and by enough to justify the compute?**

That is directly actionable. villa's loop runs two seeds already; if a consensus map is materially
more stable than either input, the cheap change is to keep the consensus rather than the winner.

## Design: leave-one-out with three seeds

For each of the three baseline arms held out in turn, with the other two as `a` and `b`:

* **single** — correlation of arm `a`'s (z, θ) ink map with the held-out arm's;
* **consensus** — correlation of the *mean* of `a` and `b`'s maps with the held-out arm's.

Six single values (each of the two non-held-out arms against the held-out one) and three consensus
values. Same 96 × 256 binning and shared axis as the published volume comparison, unchanged.

## This has an expected direction, and that is not the point

Averaging two maps with independent noise and correlating against a third will *generally* beat a
single map, so a positive result is close to arithmetic. **The informative quantity is the size of the
gain**, because that is what decides whether the compute is worth spending.

The decision rule is therefore about magnitude, not sign:

| mean gain (consensus − single) | conclusion |
|---|---|
| **≥ +0.05** | Worth it. Averaging two seeds buys real reproducibility, and the loop should keep the consensus. |
| **+0.01 to +0.05** | Marginal. Real but small; not obviously worth 2× the render cost. |
| **< +0.01, or negative** | **Not worth it.** Averaging does not stabilise the map, which would itself be surprising and would point at correlated rather than independent error between seeds. |

## The outcome that would be most interesting

**A gain below +0.01 would mean the seed-to-seed differences are NOT independent noise** — because
independent noise is exactly what averaging removes. That would be evidence the disagreement is
systematic per-run structure, which no amount of averaging fixes, and would reframe the whole
placement finding.

## Limits, fixed now

* Three seeds only, so "consensus" means two maps. Larger consensus would do better and is not tested.
* Correlation against a held-out *single* seed, which is itself only ~0.70 reproducible, caps how high
  any of these numbers can go. The comparison between them is what carries, not the absolute value.
* Binning is frozen at the published 96 × 256 and **will not be swept**. Four results in this thread
  have already moved with binning.
* Baseline arms only. Whether consensus helps under a manipulation is a different question.

## Prediction

**None registered.**
