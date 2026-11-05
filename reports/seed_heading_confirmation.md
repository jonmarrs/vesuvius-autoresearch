Finding 103: on ten hand-traced cubes never traced here, no cube skipped 20% of its seed dots, so the queued seed-heading fix's coverage gain went untested; its cost stayed within the registered bounds (2026-11-03)

The result of `docs/preregistration/2026-11-02_seed_heading_confirmation.md`, registered at f7145c5d (PR #330) before
any cube was traced. Traced 2026-11-03 12:32–13:15 PST with the autoresearch loop stopped, from the registration
commit (the wrapper that stopped the loop, ran both registered chains and restarted it:
`reports/evidence/gpu_window_2026-11-03_wrapper_script.txt`, its log `reports/evidence/gpu_window_2026-11-03_wrapper.txt`);
scored on the CPU afterwards with ScrollGT 6d05d642 (scoring version 3). Villa `39a8cf3a`,
`scrollprize/fiber_single_small` at its defaults, finding 97's protocol. Every NML and image matched its registered
SHA-256 (`data_sha256` in the JSON). Results: `reports/seed_heading_confirmation.json`.

**Status OK; decision `NO_HIGH_SKIP_CUBE`.** No unseen cube skipped 0.20 of its seed dots on the 35° test (the most,
0.167), so P3, the coverage gain, went untested. The gain in the villa draft still rests on finding 100's two Scroll-5
cubes. The registered cost bounds held on all ten cubes at tolerance 2. Precision fell by at most 0.013 (bound 0.03),
and merge-penalized ERL (ERLpen) by at most 2.7% (bound 5%).

* **The smoke passed.** `before` on `s5_13497_01497_02497_256` reproduced finding 97's run point for point.
* **The manipulation check passed.** `after` skipped no dot on any of the ten cubes, so `no_heading` was 0 on each.
* **No trace failed**, and no cube had a zero baseline.

## The predictions

`s` is each cube's share of seed dots that `before` skipped. Factors are after over before, at tolerance 2.

| | prediction | result |
|---|---|---|
| **P1** (high) | coverage factor in 0.99–1.01 on every cube with s < 0.02 | **held**: 0.9998–1.0063 on the 7 such cubes |
| **P2** (moderate) | precision at most 0.03 lower on every cube | **held**: −0.013 to +0.002 |
| **P3** (moderate) | coverage factor at least 1.05 on every cube with s ≥ 0.20 | **not tested**: no such cube |
| **P4** (low) | Spearman ρ between s and the coverage factor at least 0.5 | **missed**: ρ = 0.21 |
| **P5** (moderate) | ERLpen factor at least 0.95 on every cube | **held**: 0.973–1.009 |

The registration anticipated P3 going untested ("P3 may well go untested") and registered that outcome as an
outcome, not as a reason to add cubes or move the threshold. P1 and P4 are reported, not decisive. The median
coverage factor over the ten is 1.0004.

## Per cube

Tolerance 2. Presence held out = the cube is outside `fiber_hz_vt`'s training set.

| cube | presence held out | dots skipped before | coverage | precision | ERLpen | merges |
|---|---|---|---|---|---|---|
| s1_02494_01494_03994_512 | no | 297 of 14,079 (0.021) | 0.489 → 0.488 | 0.436 → 0.431 | 14.97 → 14.83 | 395 → 407 |
| s1_08994_02494_03494_512 | yes | 213 of 13,865 (0.015) | 0.520 → 0.523 | 0.472 → 0.473 | 20.74 → 20.24 | 198 → 201 |
| s1_09997_02497_03497_256 | yes | 12 of 1,376 (0.009) | 0.623 → 0.624 | 0.499 → 0.498 | 25.63 → 25.86 | 5 → 5 |
| s5_05497_01997_02997_256 | no | 3 of 1,255 (0.002) | 0.650 → 0.650 | 0.740 → 0.740 | 29.54 → 29.49 | 13 → 13 |
| s5_05497_02497_02497_256 | no | 0 of 1,248 (0.000) | 0.484 → 0.484 | 0.437 → 0.437 | 16.00 → 16.00 | 28 → 28 |
| s5_08994_02994_03994_512 | no | 45 of 6,469 (0.007) | 0.521 → 0.521 | 0.449 → 0.445 | 14.61 → 14.64 | 101 → 102 |
| s5_08997_02497_04997_256 | no | 7 of 1,256 (0.006) | 0.594 → 0.594 | 0.640 → 0.638 | 24.68 → 24.74 | 10 → 10 |
| s5_11497_05497_03997_256 | no | 8 of 1,837 (0.004) | 0.744 → 0.745 | 0.659 → 0.661 | 41.15 → 40.80 | 17 → 17 |
| s5_15494_04494_02494_512 | yes | 1,497 of 8,983 (0.167) | 0.497 → 0.517 | 0.584 → 0.571 | 19.17 → 19.03 | 234 → 274 |
| s5_16997_03497_03997_256 | no | 70 of 1,227 (0.057) | 0.626 → 0.624 | 0.575 → 0.571 | 28.67 → 27.89 | 31 → 31 |

On `s5_05497_02497_02497_256`, which skipped no dot, `before` and `after` traced the same fibers; on the other nine
they differ.

## What the numbers show beyond the predictions (not registered; decides nothing)

* **The cube that skipped most gained most, short of the threshold.** `s5_15494_04494_02494_512` skipped 0.167 of its
  dots and gained 1.040× coverage (1.048× at tolerance 4), the largest factor of the ten. It also took the largest
  cost: 40 more merges and 0.013 less precision, and its ERLpen fell 0.7% at tolerance 2 (it rose 5.4% at tolerance
  4). That is the direction of finding 100, but one cube below the registered threshold is not a replication, and the
  registration rules out moving the threshold after the fact.
* **The second-highest skip lost slightly.** `s5_16997_03497_03997_256` skipped 0.057 and lost: coverage 0.997×,
  ERLpen 0.973×, the lowest of the ten. Its padded CT context shares a 12 × 12-voxel column with finding 100's
  `s5_16997_03997_04497_256`, which gained 1.28× there; their cubes and labels do not overlap.
* **At tolerance 4, one cube would fail the cost bound.** P5 is registered at tolerance 2. At tolerance 4, ERLpen
  factors run 0.938–1.054, and `s5_16997_03497_03997_256` loses 6.2% (0.938×), past the 5% bound;
  `s5_11497_05497_03997_256` loses 3.9%. Precision at tolerance 4 falls by at most 0.0115. A claim that the fix costs at
  most 5% of ERLpen holds at tolerance 2 only.
* **P4's miss.** Seven of the ten cubes skipped under 2% of their dots, and their coverage factors lie within
  0.9998–1.0063. Ranking ten factors that close to 1 orders mostly changes of a few traces. P4 was registered at low
  confidence.

## What it changes

The villa draft (`docs/VILLA_DRAFT_volume_seed_heading.md`) now says what the decision rule allows. No unseen cube
skipped 20% of its dots, so the coverage gain rests on finding 100's two cubes. On each of ten unseen cubes the fix
cost at most 0.013 precision and 2.7% of ERLpen at tolerance 2, and at tolerance 4 one cube lost 6.2% of ERLpen. Where
under 2% of the dots were skipped, coverage stayed within 1%. Nothing here licenses saying the gain replicated.

The draft's "Before posting" step 3 still stands: re-check at villa's main of the day. This study ran at `39a8cf3a`.
Villa main (`deb1b6953` on 11-03) needs its native `vc_object_store` rebuilt before its tracer imports here, and the
re-check was skipped in this GPU window because that build had not been made.

## What it cannot say

* **One checkpoint at its defaults, one presence model, and finding 97's protocol**, at `39a8cf3a`.
* **Presence quality and skip share are confounded.** Seven of the ten cubes have in-sample presence. The one cube
  that came near the threshold, `s5_15494_04494_02494_512`, is one of the three held out from the presence model.
* **Ten cubes, three of them held out from the presence model.** Scroll 1 and Scroll 5 only.
* **The freeze covers `scripts/` only**, as registered: the chain ran from the registration commit, and the scorer
  imported this repository's `src/` at that commit.
