# Pre-registration: does tracing the seeds villa's tracer skips on tilted sheets add coverage on the held-out cubes?

**Status: REGISTERED 2026-10-25, before any arm was traced.** The owner approved the GPU test on 2026-10-25. The run
pauses the autoresearch loop. **Run 2026-10-25, 01:09–02:55 PDT, with the loop paused: finding 100,
`reports/neural_tracer_steep_heading.md`. P1, P3, P4 and P5 held; P2 failed.**

## The question

Given 128 voxels of the real scan around each cube, villa's neural tracer still skips 0.266 and 0.353 of its seed dots
on the two held-out Scroll-5 256³ cubes (finding 97), and 0.011–0.088 on Scroll 3 (finding 98). Those shares are over
all its dots. Of the dots it offered, it skipped 242 of 611 and 316 of 604 on the two Scroll-5 cubes, and 127–960 on
Scroll 3 (0.06–0.28 of those offered).

Finding 99 (`reports/neural_tracer_heading_residual.md`, exploratory) traced every classified skip to one check in
villa's `_seed_heading`. The dot is skipped when the CT's axis for its fiber family lies more than 35° from its
presence direction. Near the ground truth, the presence direction is the closer of the two to the fiber's tangent. The
skips are associated with sheets tilted far from vertical, where villa takes an H fiber to run along the sheet's
horizontal line. Its review scoped that finding to an association: nothing was traced again.

**This traces those dots and measures what they add.** If they add coverage on the held-out cubes and keep the
precision, the skip costs villa's tracer real fiber where the papyrus tilts. A small change to villa's own active code
would recover it, and its in-sample cubes say whether that change is safe there. If they add little, the skip is not
what limits coverage there. A second arm asks whether the heading matters or only the skip does.

## Reachability, checked before designing the arms

* **Training never applies the skip.** villa's training seeds take the CT axis signed along the fiber's tangent,
  whatever the angle between them (`data/seeds.py::make_seeds` and `directed_seed`, `data/targets.py`). They are
  skipped only when the CT gives no axis (`SeedHeadingError`). The 35° test exists only in `tracing/volume.py`, at
  inference. So tracing from villa's own axis at those dots (`keep`) is the training distribution, not a new input.
* **The heading is replaceable without touching villa's source.** villa calls `seed_headings(self.vol, batch,
  self.tracer.axis_pool)` by its module-global name. That function maps `_seed_heading` over spawned axis workers.
  `scripts/neural_tracer_heading_arm.py` replaces `seed_headings` in the main process with the same lines. It maps a
  function the workers import by module name, and that function reads villa's own `_WORKER_VOL`, set by villa's own
  initializer.
* **The heading enters the trace only as its start.** Each dot is traced both ways from it (`volume.py`: heading and
  minus heading). Owned-dot tests use the presence direction, not the heading.
* **The inputs exist and are unchanged.** Findings 97 and 98's padded CT and presence are on disk in
  `spiral_out/neural_tracer/ct_context_run` and `ct_context_512_run`, with their identity checks recorded in each
  `prepared.json`.

## The floor

villa's tracer is deterministic on these inputs. Finding 91 measured a repeat difference of 0, and the smokes of
findings 93, 97 and 98 each reproduced a run point for point. A difference between an arm and the baseline is
therefore the arm's, including the downstream effect of changed seeds on which fibers own which voxels. No noise floor
enters the thresholds.

## Arms

All arms use findings 97 and 98's command and inputs. That is finding 91's command (checkpoint
`scrollprize/fiber_single_small` at 4511825, villa `ccb431818`, `--ct-level 0 --ct-grid-scale 1 --grid-scale 2
--base-um 7.91`, the parent `.afv` as frame template). The CT is padded by 128 voxels of the real scan, the presence
is finding 91's own level in the padded frame, and the box is the cube.

| arm | work dir | a dot whose CT axis lies more than 35° from its presence direction | every other dot | verified how |
|---|---|---|---|---|
| baseline | findings 97 and 98's runs, `ct_context_run/neural`, `ct_context_512_run/neural` | skipped (villa) | villa's heading | their reports |
| smoke | `steep_heading_run/smoke/s5_13497_01497_02497_256` | skipped, through the launcher (`--arm villa`) | villa's heading | `.afv` equals finding 97's point for point |
| sheet | `steep_heading_run/sheet/<cube>` | traced from its presence direction projected into the CT's sheet (normal to villa's own `ct_normal`) | villa's heading | `heading_arm.json` tally; skips fall |
| keep | `steep_heading_run/keep/<cube>` | traced from villa's own CT axis, signed along the presence direction | villa's heading | `heading_arm.json` tally; skips fall |

Only a dot with no CT axis (`SeedHeadingError`, as villa) is still skipped. In `sheet`, so is a dot whose projection
is shorter than villa's own ambiguity floor, 1e-3. Projections of a presence direction more than 45° out of the sheet
are counted, never acted on. villa's `run.json` records the arm in its seed-heading policy, so villa itself refuses a
resume with another arm.

## The cubes

All 21, in two sets judged apart:
* **Held out (10):** the two Scroll-5 256³ cubes the reference mask never trained on, `s5_13497_01497_02497` and
  `s5_16997_03997_04497`, and the eight Scroll-3 512³ cubes.
* **In sample (11):** the three other Scroll-5 256³ cubes, the five Scroll-1 256³ cubes and the three Scroll-5 512³
  cubes.

The chain traces the held-out set first (sheet, then keep), then the in-sample set.

## Predictions, fixed now

Factors are over the baseline's value on the same cube, at tolerance 2 (ScrollGT `score_tracing`, scoring version 3).

**What sets the sizes.** In findings 97 and 98, the seeds the scan around each cube recovered raised coverage about
as the traced-seed count to the power 0.65 (the median; 0.50–1.36 over the 21 cubes). Precision moved by −0.06 to
+0.07. If every skipped dot here were traced, traces would rise 1.66× and 2.10× on the two Scroll-5 cubes, and
1.06–1.38× on Scroll 3. Suppose three in four end up traced; that is a guess, and the rest become owned once their
neighbours are traced. Then coverage would rise about 1.3× and 1.5× on the two Scroll-5 cubes. On Scroll 3 it would
rise a median 1.10× (1.03–1.18). **Against:** the rescued dots lie in tilted sheets, where
the network may trace worse than where its seeds agree.

1. **P1: sheet adds coverage on the two held-out Scroll-5 cubes.** Coverage factor at least 1.15 on both. Confidence
   moderate.
2. **P2: sheet adds coverage on Scroll 3.** Coverage rises on at least 6 of the 8 cubes, with a median factor of at
   least 1.05. Confidence moderate.
3. **P3: sheet keeps the precision.** On at least 8 of the 10 held-out cubes, its precision is at most 0.03 below the
   baseline's, or above it. Confidence moderate.
4. **P4: the heading matters.** Sheet's coverage is above keep's on at least 7 of the 10 held-out cubes. Confidence
   low. **For:** keep starts each rescued trace 35–90° off the presence direction, which near the ground truth is the
   closer to the fiber (finding 99). **Against:** the network was trained from exactly such starts, and every trace
   re-aims along its own path once 12 voxels of it fit a trusted line (`trace_heading`).
5. **P5: in sample, nothing moves much.** Both arms' coverage factors lie in 0.95–1.05 on all 11 in-sample cubes.
   Confidence high. Those cubes' runs skipped 3–166 dots, at most 0.061 of the dots offered.

**Manipulation check:** on every held-out cube, each arm skips at most a fifth of the baseline's share of dots.
Otherwise the status is MANIPULATION_FAILED.

**Descriptive, no prediction:**
* merge-penalized ERL at both tolerances, coverage and precision at tolerance 4, output over ground-truth length;
* keep's own factors, beside sheet's;
* the launcher's tally of how the offered dots were headed, including rescued dots more than 45° out of the sheet;
* seed, trace and stop counts;
* the runtime of each run;
* our tracer's published rows, for context only.

## Decision rule

| outcome | conclusion |
|---|---|
| the smoke does not reproduce finding 97's run | SMOKE_FAILED; no arm runs |
| an arm misses the manipulation check | MANIPULATION_FAILED; no reading |
| a run fails or writes nothing | INCOMPLETE |
| P1 and P2 hold | "a seed heading that follows the sheet recovers coverage on the held-out cubes" |
| only P1 holds | "... recovers coverage on the two held-out Scroll-5 cubes, not as registered on Scroll 3" |
| only P2 holds | "... recovers coverage on Scroll 3, not as registered on the two held-out Scroll-5 cubes" |
| neither holds | "tracing the skipped dots adds less coverage than registered: on the held-out cubes the skip is not the main limit on coverage" |

Where coverage is recovered, the reading adds ", keeping its precision" if P3 holds and ", at a cost in precision" if
it fails. It also adds:
* if P4 holds: "the heading matters: villa's own axis, kept, recovers less";
* if P4 fails: "but villa's own axis, kept, recovers about as much: what loses the coverage is the 35° skip, not the
  heading".

Where coverage is not recovered, a failed P3 adds ", and the added traces cost precision". P5 is reported apart, true
or false. A villa change, whatever the reading, is a separate decision by the owner.

`scripts/neural_tracer_steep_heading.py` (`verdict`, `reading`, `status`) implements this table. Its tests pin each
threshold to this document.

## What the result cannot do

* **It does not show tilt is the cause.** Both arms change the same dots, and those dots were selected by the 35° test,
  not by tilt. A gain says the skip costs coverage. P4 says whether the sheet heading beats villa's axis on those
  dots.
* **It does not show that a villa change would help elsewhere.** It covers one checkpoint, its defaults and two
  held-out sets, and the presence comes from a mask model that trained on the in-sample cubes.
* **The presence is unchanged.** It is finding 91's, zeros outside the cube.
* **Our tracer is not re-run.** Its rows are from the cube alone, as in findings 97 and 98.
* **On Scroll 3, scroll and split cannot be told apart.** All eight of its cubes are held out.

## Cost

* **GPU, loop paused:** the smoke and 42 runs. Findings 97 and 98's runs took 48–63 s per 256³ cube and 159–221 s per
  512³ cube, about 45 minutes for all 21. So about 1.6–2 hours, more where more seeds are traced.
* **CPU, loop running, nice 19:** scoring 42 runs, about 5 minutes per 512³ run, so about 2 hours.
* **No download.**
