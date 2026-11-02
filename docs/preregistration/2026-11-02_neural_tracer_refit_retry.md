# Pre-registration: does villa's own refit retry at confidence stops raise its neural tracer's continuity on the held-out cubes?

**Status: PROPOSED 2026-11-02, not registered.** This is the development-pilot proposal that finding 102 names as the
next step. Running it is the owner's GPU decision: the chain needs the autoresearch loop stopped for about 80 minutes.
It becomes the registration, unchanged or amended in the open, when the owner approves and before any arm is traced.
The launcher, the chain and the scorer below are committed with it.

## The question

Finding 101 (`reports/neural_tracer_confidence_stops.md`) closed villa's neural tracer's confidence stops as a coverage
lever. Finding 102 (`reports/neural_tracer_continuity_ceiling.md`) measured them on continuity instead. Perfect
continuation from every confidence stop where the hand-traced fiber goes on, joining the trace it reaches where neither
trace merges, would raise ScrollGT's merge-penalized ERL (ERLpen) by a median 0.314 on the ten held-out cubes
(0.149–0.479). Bounded to 20 voxels past each stop, the ceiling is 0.061; bounded to 50 voxels, 0.130. Two-thirds of the
tracer's interior confidence stops are off the reference (finding 101).

A ceiling is not a rule. **This runs the one continuation rule villa's tracer already has**, its refit retry, against
the stock tracer, on the same 21 cubes and inputs. If it raises held-out ERLpen by at least 10% with no more merges and
the same precision, the confidence-stop line has a candidate worth a registered test on new cubes, and villa a small
change worth proposing: exposing the retry in its volume tracer. If it does not, the one ready-made rule fails to
realize the ceiling, and any further work on the line needs a new rule.

## Reachability, checked before designing the arms

All in villa's source at the pin, `ccb431818`, the tracer of findings 91–102. `tests/test_neural_tracer_refit_retry.py`
asserts each line quoted here.
* **The retry exists and is off by default.** `tracing/trace.py`: `refit_retry: bool = False`, documented as "a
  decision that would stop on confidence first retries once at the same head with its crop refit to its own prediction
  (frames.learned.predicted_axis over the gate horizon); only a second stop then ends the trace". The checkpoint's gate
  horizon is 16 voxels (`gate_horizon` 16, `future_step` 1; read from the checkpoint on CPU).
* **It acts only at a would-be confidence stop, once per stop.** `if would_stop and pp.refit_retry and not retried[i]
  and not recovery_blocked:`. The flag is reset on every advance (`retried[i] = False`, the only such line), so every
  stop along a trace gets one retry.
* **villa's volume tracer never sets it.** `tracing/volume.py` holds no `refit`; its `build_tracer` builds
  `TraceParams.from_policy(policy, max_len=args.max_len, ...)`, and its `main` calls `build_tracer(args)` by the module's
  global name. villa exposes the retry only in its single-seed CLI (`tracing/inference.py --refit-retry`).
* **The retry can be switched on without touching villa's source.** `scripts/neural_tracer_refit_arm.py` runs villa's
  own `main()` with `build_tracer` wrapped: the tracer it builds gets `refit_retry` set by the arm
  (`dataclasses.replace` on the tracer's `p`, which the trace loop reads as `pp = self.p`). Each run's
  `refit_arm.json` records the value the tracer held. Its tests cover the wrap, the record and a refused resume.
* **The inputs exist and are unchanged.** Findings 97 and 98's padded CT and presence are on disk in
  `spiral_out/neural_tracer/ct_context_run` and `ct_context_512_run`, with their identity checks recorded in each
  `prepared.json`.
* **Not checked, because it needs the model on the GPU:** whether any retry succeeds. A retry that fails leaves the
  trace as it was, so a refit arm identical to the baseline would mean no retry ever succeeded. The scorer records, by
  cube, whether each run's `.afv` equals the baseline's.

Every arm keeps villa's volume tracer's confidence threshold, 0.5, as findings 91–102 did. The checkpoint's own
operating policy says 0.7. villa's `--confidence` default, 0.5, overrides it, and each run's `run.json` records 0.5.

## The floor

villa's tracer is deterministic on these inputs: finding 91 measured a repeat difference of 0, and the smokes of
findings 93, 97, 98 and 100 each reproduced a run point for point. But the retry changes which heads share a model call:
a retrying head stays in the batch one more round. villa notes that in bf16, the precision of all these runs,
batch composition can matter: "fp32 keeps batch-composition rounding differences from growing into flipped decisions"
(`tracing/trace.py`).

So a **floor arm** runs villa's tracer, through the launcher with the retry off, with `--forward-chunk 64` in place of
villa's default 128, on the ten held-out cubes. villa's resume check counts `forward_chunk` among the settings that only
change speed. Whatever the floor arm moves, batch composition moved. **If its median |ERLpen change| over the held-out
cubes is not below 0.03, the status is FLOOR_TOO_LARGE and no reading is made.** It also sets P2's allowance for
merges.

## Arms

All arms use findings 97 and 98's command and inputs: checkpoint `scrollprize/fiber_single_small` at 4511825, villa
`ccb431818`, `--ct-level 0 --ct-grid-scale 1 --grid-scale 2 --base-um 7.91`, the CT padded by 128 voxels of the real
scan, finding 91's presence in the padded frame, the parent `.afv` as frame template and the cube as the box.

| arm | work dir | what varies | cubes | verified how |
|---|---|---|---|---|
| baseline | findings 97 and 98's runs, `ct_context_run/neural`, `ct_context_512_run/neural` | nothing: villa's tracer | 21 | their reports |
| smoke | `refit_retry_run/smoke/s5_13497_01497_02497_256` | nothing, through the launcher (`--arm villa`) | 1 | `.afv` equals finding 97's point for point |
| refit | `refit_retry_run/refit/<cube>` | `refit_retry` on (`--arm refit`) | 21 | `refit_arm.json` records it in effect |
| floor | `refit_retry_run/floor/<cube>` | `--forward-chunk 64`, retry off (`--arm villa`) | 10 held out | `refit_arm.json` records it off |

`repro/fibers/run_neural_tracer_refit_retry_chain.sh` runs the smoke, then refit on the held-out cubes, the floor on
them, and refit on the in-sample cubes. It refuses to start while the loop or another GPU job runs and freezes the
scripts it runs.

## The cubes

All 21, in finding 100's two sets:
* **Held out (10), which decide:** the two Scroll-5 256³ cubes the reference mask never trained on and the eight
  Scroll-3 512³ cubes, the cubes of finding 102's ceiling.
* **In sample (11), described only:** the three other Scroll-5 256³ cubes, the five Scroll-1 256³ cubes and the three
  Scroll-5 512³ cubes.

Findings 91–102 developed on all 21. This is a development pilot, a screen, not a confirmation.

## Predictions

Gains are over the baseline's ERLpen on the same cube, at tolerance 2 (ScrollGT `score_tracing`, scoring version 3).

**What sets the sizes.** Directly, the retry adds only what lies past a confidence stop. Finding 102 puts the ceiling
for continuing along the right fiber at a held-out median of 0.314 (0.149–0.479 by cube), and of 0.061 within 20 voxels
of each stop. A retry that succeeds
re-enters the ordinary loop, so it can go on for tens of voxels; one that fails ends the trace as before. **For:**
villa built the retry for this failure. **Against:** finding 101 found most interior confidence stops already off the
reference 20 voxels before they stop, so many retries would extend wrong traces; and a refit to the decision's own
low-confidence prediction may leave the model as unsure as before. The retry also changes what later traces own, so
the ceiling does not bound this arm: a gain above 0.314 would not be an error.

1. **P1: the retry raises continuity.** A median held-out ERLpen gain of at least 0.10, the strategy's
   useful-continuity bar. Confidence low.
2. **P2: no more wrong connections.** The held-out cubes' total ScrollGT merge count in the refit arm exceeds the
   baseline's by no more than the floor arm's own change in that total, in either direction. Confidence moderate:
   finding 102's joins inherited merges at tolerance 4, and a retry that crosses to another fiber makes one.
3. **P3: the retry keeps the precision.** Its precision is at most 0.03 below the baseline's, or above it, on at least
   8 of the 10 held-out cubes (finding 100's P3). Confidence moderate.

**Manipulation check:** every refit run records `refit_retry` in effect, and every floor and smoke run records it
off. Otherwise the status is MANIPULATION_FAILED.

**Descriptive, no prediction:**
* each held-out cube's gain as a share of finding 102's ceiling U;
* the in-sample median gain;
* coverage, precision and merges by cube, and every row at tolerance 4;
* each run's trace and stop counts and its runtime, beside the baseline's;
* by cube, whether the refit run's `.afv` equals the baseline's (no retry succeeded).

## Decision rule

| outcome | status and conclusion |
|---|---|
| the smoke does not reproduce finding 97's run | SMOKE_FAILED; no arm runs |
| a run records the retry other than its arm sets it | MANIPULATION_FAILED; no reading |
| a run fails, writes nothing, or no smoke is on record | INCOMPLETE |
| the floor arm's median \|ERLpen change\| is not below 0.03 | FLOOR_TOO_LARGE; no reading: batch composition alone moves ERLpen too far to read a 0.10 bar |
| P1, P2 and P3 hold | "villa's refit retry raises held-out ERLpen by a median X, without more merges and keeping its precision": propose a registered test on cubes outside these 21 and, separately, exposing `--refit-retry` in villa's volume tracer, checked again on villa's main |
| P1 holds, P2 or P3 fails | "..., but with more merges and/or at a cost in precision": the strategy stops a candidate whose gain depends on wrong connections or lost precision |
| P1 fails | "..., under the 0.10 bar: it does not realize the continuity ceiling; close it as a continuation rule", adding whether it also adds merges or costs precision |

`scripts/neural_tracer_refit_retry.py` (`verdict`, `reading`, `status`) implements this table. Its tests pin each
threshold to this document, refuse a partial sample, and check that each failure branch emits no reading. A villa
change, whatever the reading, is a separate decision by the owner.

## What the result cannot do

* **It cannot show that a gain comes from rescued stops.** The retry changes which traces own which voxels downstream,
  so ERLpen can move on cubes where no retry succeeded in the scored region. The run counts and the unchanged-run check
  bound this, but do not separate it.
* **It is not independent review.** ERLpen and merges are measured against one WEBKNOSSOS reference per cube, which
  stands in for the strategy's "independently reviewed continuity" and "wrong connections". A positive pilot needs
  human review of the added traces before a larger test.
* **It is not confirmation.** All 21 cubes are development data. ScrollGT holds no other fiber cubes (21 on its main,
  1605fadb); whether villa's fiber datasets hold references outside these 21 is unchecked.
* **It describes the pinned tracer.** villa #2359 (merged 2026-10-29) added full-volume tracing and chunk-cache
  scheduling to the volume tracer; a villa change would have to be checked again on villa's main.

## Limits

One checkpoint, one operating policy (confidence 0.5), one protocol (128 voxels of CT context), one reference per cube,
bf16 arithmetic. Eight of the ten held-out cubes are from Scroll 3. The floor arm perturbs one setting; batch
composition under the retry may differ from batch composition under a smaller forward chunk.

## Cost

GPU, with the autoresearch loop stopped: the smoke (about a minute) and 31 runs. The baseline's 21 runs took 2,684 s of
tile time (1,701 s on the held-out cubes). Finding 100's chain ran 42 such runs in 104 minutes, so this chain should take
about 80 minutes, more if retries are frequent. That is inside the strategy's four-GPU-hour pilot ceiling. Scoring runs
on the CPU afterwards, with the loop running. No new data are fetched.
