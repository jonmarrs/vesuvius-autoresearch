Finding 104: villa's refit retry at confidence stops raises held-out ERLpen by a median 0.003, under the 0.10 bar, and adds merges: it closes as a continuation rule (2026-11-03)

The result of `docs/preregistration/2026-11-02_neural_tracer_refit_retry.md`, registered at f7145c5d (PR #330) before
any arm was traced. Traced 2026-11-03 13:15–14:38 PST with the autoresearch loop stopped, from the registration
commit; scored on the CPU afterwards with ScrollGT 6d05d642 (scoring version 3). Villa `ccb431818`,
`scrollprize/fiber_single_small` at 4511825, findings 97 and 98's inputs and command. Results:
`reports/neural_tracer_refit_retry.json`.

**Status OK. The registered reading:** "villa's refit retry raises held-out ERLpen by a median 0.003, under the 0.10
bar: it does not realize the continuity ceiling; close it as a continuation rule; it also adds merges."

| | prediction | result |
|---|---|---|
| **P1** (low) | median held-out ERLpen gain at least 0.10 | **missed**: 0.003 (−0.023 to +0.126) |
| **P2** (moderate) | held-out merges rise by no more than the floor arm's change | **missed**: 1,740 → 1,959 (+219), against the floor's +35 |
| **P3** (moderate) | precision at most 0.03 lower on at least 8 of the 10 held-out cubes | **held**: on 9 |

The checks all passed:
* **Smoke.** The launcher's `villa` arm reproduced finding 97's run of `s5_13497_01497_02497_256` point for point.
* **Baseline.** All 21 baseline runs, re-scored with the scorer the arms used, gave findings 97 and 98's recorded rows
  exactly, at both tolerances.
* **Manipulation.** Every refit run records the retry in effect, and every floor run and the smoke record it off.
* **Floor.** Its median |ERLpen change| over the held-out cubes is 0.008, below the 0.03 limit.
* **No run failed.** Every refit run differs from its baseline, but so does every floor run, so a difference alone
  does not show that a retry succeeded. The stop counts do (next section).

## The retry works, and most of what it adds is off the reference

The retry does what villa built it for. On the ten held-out cubes, confidence stops fall from 16,524 to 13,092 (−21%;
−16% to −30% by cube), while the floor arm leaves them at 16,539. The traces keep 5.3% more voxels, and coverage
rises on every cube (a median 1.020×, 1.009–1.085×).

But most of what the retry adds lies off the reference. Precision falls on all ten held-out cubes, by 0.010 to 0.041.
Over the ten, the refit traces are 159,157 longer than the baseline's (ScrollGT's predicted length), and only 0.202 of
that added length lies within 2 voxels of the reference, as precision counts it. The baseline's own precision is
0.364–0.664 on these cubes. Merges rise on all ten, by 7 to 39. The merge penalty cancels the added length: the net
ERLpen gain is a median 0.003, positive on 5 of the 10 cubes. As a share of finding 102's ceiling U on each cube, it
is a median 0.007.

Finding 101 predicted this. Two-thirds of the tracer's interior confidence stops lie off the reference, most of them
already off it 20 voxels before they stop. A rule that retries every confidence stop extends those too. Finding 102
said a useful rule must go on "only where the trace is on a fiber". The retry has no such test: it refits the crop to
the decision's own prediction.

**The one large gain is half floor.** `s5_13497_01497_02497_256` gains 0.126, the only held-out cube above the bar.
The floor arm, which changes only villa's forward chunk, moves the same cube by +0.059. Nine of the ten refit gains are
smaller in size than that floor change, the largest of the ten.

| Held-out cube | ERLpen | Gain | Floor | Coverage | Precision | Merges | Confidence stops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| s5_13497_01497_02497_256 | 11.41 → 12.85 | +0.126 | +0.059 | 1.085× | -0.010 | 24 → 31 | 392 → 300 |
| s5_16997_03997_04497_256 | 9.87 → 9.80 | -0.007 | -0.012 | 1.066× | -0.022 | 30 → 39 | 290 → 216 |
| s3_00994_00494_01994_512 | 34.65 → 34.09 | -0.016 | +0.003 | 1.011× | -0.019 | 180 → 196 | 1,982 → 1,636 |
| s3_00994_01994_00494_512 | 42.08 → 42.52 | +0.010 | -0.003 | 1.011× | -0.012 | 219 → 236 | 1,250 → 926 |
| s3_00994_02494_01494_512 | 29.60 → 29.81 | +0.007 | +0.009 | 1.022× | -0.011 | 257 → 284 | 1,909 → 1,500 |
| s3_01994_01494_00994_512 | 32.12 → 32.11 | -0.000 | +0.007 | 1.027× | -0.041 | 114 → 144 | 3,503 → 2,852 |
| s3_01994_01994_01494_512 | 32.06 → 32.66 | +0.019 | -0.023 | 1.028× | -0.029 | 187 → 208 | 3,743 → 3,127 |
| s3_02994_02494_01994_512 | 41.50 → 41.76 | +0.006 | -0.007 | 1.009× | -0.012 | 169 → 194 | 869 → 612 |
| s3_03494_01494_00494_512 | 35.03 → 34.22 | -0.023 | +0.003 | 1.019× | -0.012 | 300 → 339 | 962 → 736 |
| s3_04494_00994_01494_512 | 26.25 → 26.12 | -0.005 | -0.010 | 1.012× | -0.014 | 260 → 288 | 1,624 → 1,187 |

| In-sample cube | ERLpen | Gain | Coverage | Precision | Merges | Confidence stops |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| s5_03997_01497_03997_256 | 12.50 → 12.26 | -0.019 | 1.006× | -0.004 | 0 → 1 | 102 → 90 |
| s5_07997_02997_05497_256 | 14.64 → 14.49 | -0.010 | 1.014× | -0.003 | 5 → 5 | 49 → 32 |
| s5_14997_01497_01497_256 | 13.76 → 13.79 | +0.002 | 1.019× | -0.000 | 36 → 46 | 177 → 126 |
| s1_00497_01497_03997_256 | 10.03 → 9.55 | -0.048 | 1.003× | -0.013 | 21 → 21 | 379 → 270 |
| s1_00497_02497_02997_256 | 15.70 → 15.85 | +0.010 | 1.015× | -0.003 | 33 → 34 | 92 → 56 |
| s1_00997_02497_02997_256 | 11.80 → 11.82 | +0.002 | 1.001× | -0.005 | 22 → 23 | 24 → 17 |
| s1_08997_02997_02497_256 | 13.15 → 13.28 | +0.010 | 1.008× | -0.001 | 31 → 32 | 47 → 38 |
| s1_10997_02997_02997_256 | 20.49 → 20.73 | +0.012 | 1.005× | +0.001 | 5 → 5 | 47 → 36 |
| s5_06494_01994_03994_512 | 17.41 → 16.94 | -0.027 | 1.007× | -0.009 | 137 → 144 | 705 → 507 |
| s5_06994_00994_04994_512 | 11.43 → 11.45 | +0.002 | 1.014× | -0.011 | 280 → 309 | 1,670 → 1,191 |
| s5_07994_01994_05494_512 | 11.65 → 11.54 | -0.009 | 1.011× | -0.005 | 151 → 170 | 654 → 464 |

Gain is ERLpen over the baseline's, at tolerance 2. Floor is the floor arm's ERLpen change on the same cube
(`--forward-chunk 64`, retry off). Coverage is a factor, precision a difference, both refit against baseline.

**In sample** (described only), the median gain is 0.002. Confidence stops fall by 28% in total, coverage rises on all
11 cubes, and merges rise on 8 of them and fall on none.

**At tolerance 4** (described only), the held-out median ERLpen gain is 0.023 (−0.019 to +0.044), and held-out merges
rise by 271.

**Cost.** The held-out refit runs took 1,856 s in total against the baseline's 1,701 s (+9%).

## What it changes

**The confidence-stop line has no ready-made rule.** Finding 102 kept it open as a continuity lever, and this pilot
ran the one continuation rule villa's tracer already has. It gains a median 0.003 against a bar of 0.10 and adds
merges, so it closes as a continuation rule, as registered. Further work on the line needs a new rule. Findings 101 and 102 say
what that rule would have to do: go on for tens of voxels, and only where the trace is on a fiber. This pilot adds a
third requirement: decide whether the continuation is on the fiber before keeping it. A rule must not keep every
retry that clears the confidence gate.

**No villa proposal.** The registered positive outcome was to propose exposing `--refit-retry` in villa's volume
tracer. That does not follow. villa's single-seed CLI already exposes it, and nothing here argues for changing its
default.

**The ten unseen cubes stay unused for this.** A negative pilot needs no confirmation set. Finding 103 has since traced
the stock tracer (villa `39a8cf3a`) on all ten, so they are no longer cubes nothing here has traced. A future rule
that registers its confirmation on them must say that its stock baseline there is already on record.

## What it cannot say

* **One checkpoint, one operating policy (confidence 0.5), one protocol (128 voxels of CT context)**, and bf16
  arithmetic, at villa `ccb431818`. villa #2359 (merged 2026-10-29) refactored the volume tracer since.
* **It cannot show where the gain and the cost come from.** The retry changes which traces own which voxels
  downstream, so ERLpen and merges move beyond the rescued stops. The stop counts show retries succeeded; they do not
  attribute each merge to a retry.
* **One reference per cube.** Merges and precision are measured against one WEBKNOSSOS reference, which stands in for
  the strategy's "independently reviewed" wrong connections.
* **Development data.** Findings 91–103 developed on these 21 cubes. A negative screen on them closes this rule; it
  says nothing about rules not run.
