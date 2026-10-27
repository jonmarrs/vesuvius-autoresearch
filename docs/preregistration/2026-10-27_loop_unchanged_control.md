# Pre-registration: does batchgeneratorsv2 beat the unchanged config, not only the loop's other tweaks?

**Written 2026-10-27 (about 15:05 PDT), before either arm's first cycle; revised about 15:20, before any cycle could
count, to open the window with #263's recorded identities.** The window starts no earlier than
**2026-10-27 16:00:00 PDT**.

## The question

[The batchgeneratorsv2 confirmation](2026-10-25_loop_batchgeneratorsv2.md) found it above the loop's other tweaks on
new cycles: val_f1 +0.0043, ROC AUC +0.0110, AP prevalence lift +0.042 (the audited reading, accepted post hoc in its
Amendment 2). It could not compare it with the config as it was: the loop never ran a cycle without a tweak. Beating
the other tweaks' mean is not beating the unchanged config if the other tweaks are on average harmful.

Since the 2026-10-27 promotion (#262) the base config trains with batchgeneratorsv2, and two arms now run on the same
incumbent:
- **control_unchanged** (#259): config.json as it is, so batchgeneratorsv2;
- **aug_mode_albumentations**: the aug_mode tweak's one remaining value, the old recipe, everything else unchanged.

Old against new, directly. If batchgeneratorsv2 is the better recipe, the reverse arm scores lower than the control.

## Reachability

Both arms come from the loop's own sampler; nothing is added. The sampler repeats no config run in its last 20 cycles,
so each arm runs at most once in 20, about 4 times a day at the loop's pace. Ten of each takes about three days. Every
cycle's record, with its result and its incumbent's sha256, is in `cycles.jsonl` (#245, #258): no join to the run
logs, the fault that left the confirmation's registered command without a reading. The window needs #263 in the
loop's checkout (its stop, pull and start): its records carry each cycle's code digest and baseline config, which
this window is held to. Nothing counts before that rollout. **Once the window opens, another pull into the loop's
checkout ends it.**

## Window

It opens with the first cycle in `cycles.jsonl` that starts at or after 2026-10-27 16:00:00 PDT and is recorded with
#263's identities: `code_sha256`, and a `baseline_config` matching its `baseline_config_sha256`. It holds every later
cycle that faced the incumbent `c80885969cc5b3d4c1dfeebc46d1c0c4c62f55fbe758ce48b263050dc293f18d` (best_model.pt as
promoted), in the first cycle's code digest and baseline config, ran the 900 s budget, and was scored (not crashed,
not blocked from comparison). A control cycle counts only if its `config` is its baseline; a reverse cycle only if its
`config` is its batchgeneratorsv2 baseline with `aug_mode` albumentations and nothing else. A cycle whose identities
are missing or do not verify is left out. The window ends at the first of:
- each arm's first 10 cycles (later cycles of an arm are dropped);
- a promotion (the promoted cycle is the last), or a cycle on another incumbent;
- a cycle in another code digest or baseline config than the window's first (a pull, or a changed config.json);
- 2026-11-03 16:00:00 PDT.

With fewer than 6 cycles of either arm, there is no reading.

## Predictions, fixed now

Each is the reverse arm's mean minus the control's, about half the confirmation's effect with its sign reversed.

1. **Q1, val_f1: ≤ −0.002.** High.
2. **Q2, ROC AUC: ≤ −0.005.** High.
3. **Q3, AP prevalence lift: ≤ −0.015.** Reported; changes no reading.

Power (normal approximation, 10 cycles each; per-cycle SDs from the confirmation's window: batchgeneratorsv2's own
cycles 0.00137 val_f1, 0.0067 AUC, and the other tweaks' pooled within-tweak 0.00192 and 0.0063, df 103):

| true difference | Q1 holds | Q2 holds |
|---|---:|---:|
| the confirmation's effect (−0.0043, −0.0110) | 1.00 | 0.98 |
| half of it | 0.58 | 0.57 |
| none | 0.004 | 0.04 |

With 6 each: 0.99 and 0.95 at the full effect, 0.019 and 0.09 at none.

## Decision rule

| outcome | reading |
|---|---|
| fewer than 6 cycles of either arm when the window ends | INCOMPLETE: no reading |
| Q1 and Q2 hold | BEATS_UNCHANGED: on this validation sample, from this incumbent, batchgeneratorsv2 fine-tunes better than the old recipe, in F1 and ranking |
| Q1 holds, Q2 fails | F1_ONLY: the F1 gain over the old recipe recurs, the ranking gain does not |
| Q1 fails | NOT_SHOWN: no F1 gain over the unchanged config is shown; the confirmation's gain may be over tweaks that cost F1 |

Reported beside it, changing no reading: each arm against the window's other tweaks (the confirmation's comparison),
and the two arms' step counts at [#250's](../../reports/loop_steps_vs_ranking_2026-10-26.md) within-tweak slopes
(batchgeneratorsv2 trains about 300 fewer steps in a cycle).

`scripts/loop_unchanged_control.py` implements the window and the table (`REGISTERED`, `window`, `read`);
`tests/test_loop_unchanged_control.py` checks each row of the table, the window's ends, which cycles count, and that
this document states the script's rule. Until the window is complete only the counts are read:

    python3 scripts/loop_unchanged_control.py status --cycles cycles.jsonl
    python3 scripts/loop_unchanged_control.py read --cycles cycles.jsonl \
        --steps reports/loop_steps_vs_ranking_2026-10-26.json --out reports/<X>.json

`read` refuses until the window is complete.

## What the result cannot do

- **Say anything off this validation sample.** Every cycle is scored on the loop's 400 Fr143 patches (protocol v3).
- **Compare the recipes from scratch.** Both arms fine-tune an incumbent whose last cycle trained with
  batchgeneratorsv2; switching back may cost something of its own.
- **Name the mechanism.** The recipes differ in more than the step count.
- **Hold for the replicate rule's decisions.** The rule reads the same cycles; a promotion by it ends the window.

## Disclosure

Since the promotion I have read the names and start times of the loop's first three cycles (multi_task_heads_False,
loss_fiber_bce_0.1, consistency_weight_0.2), the val_f1 of the first two, and the replicate rule's record on them.
None is either arm. The window starts after this registration is committed.

## Cost

None beyond the loop's own cycles: no GPU time, no pause. The reading takes seconds of CPU.
