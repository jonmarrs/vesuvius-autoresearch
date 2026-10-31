# Pre-registration: does flooring the replicate rule's SD at the field's stop near-no-op promotions and keep batchgeneratorsv2?

**Written 2026-10-31, after the rule promoted lr 1e-5 (2026-10-29 12:40) and before the amended rule runs in the
loop.** Every window replayed below had been seen in full before the floor was chosen. The floor was designed after the
lr 1e-5 promotion, to stop it, so its refusal of lr 1e-5 is in-sample by construction.

## The question

The live rule ([the 10-26 registration](2026-10-26_loop_replicate_rule_window.md), adopted by the owner on 10-27)
takes Student's t of a tweak's cycles minus the other tweaks' epoch mean. Only the tweak's own spread enters that t.
A tweak that barely changes the model therefore scores high on any steady offset. Every cycle fine-tunes the incumbent
for 15 minutes, and at lr 1e-5 that leaves the model almost as it was. Against the 10-27 incumbent, lr 1e-5's six
cycles spread 0.00004 in val_f1, against 0.0019 for all 161 cycles. The rule fired at t 5.57 and promoted it on
+0.0002 val_f1, which set every later cycle's lr to 1e-5 until the owner restored 5e-4 on 10-30. Against the next
incumbent it was on course to fire again.

The amendment floors each t's SD at the field's. If that stops promotions like lr 1e-5's and still takes
batchgeneratorsv2, the owner can run the loop on it. If it also loses batchgeneratorsv2, the floor costs the rule
its one demonstrated gain.

The amendment does not change what the rule compares against. A tweak is still set against the other tweaks' mean,
not against the unchanged control or the incumbent. Comparing against `control_unchanged` was considered and set
aside. The control runs at most once in 20 cycles, so 6 control cycles take about 32 hours. And no control cycles
existed when batchgeneratorsv2 was found, so that version cannot be checked against the one known gain.

## The rule, frozen

`scripts/loop_replicate_rule.py`, `LIVE`: `REGISTERED` with `sd_floor` true. That means val_f1 and ROC AUC, both
required; at least 6 of the tweak's cycles; each difference against at least 10 other cycles of its epoch; c = 4.5.

At the end of cycle j of tweak T, each of T's cycles i has d_i = x_i minus the mean of the other tweaks' cycles so
far in i's epoch, as before. The field is every other tweak's cycle o so far, with d_o = x_o minus the mean of the
cycles of tweaks other than o's in o's epoch, under the same 10-cycle minimum. Then t = mean(d) / (s / sqrt(n)), with
s = max(sd(d), sd(field)). Without the floor, s = sd(d). The score is the smaller t over the two measures. It fires
above c. A firing still promotes only if every other gate passes (`replicate_rule.eligible`), as before.

Each cycle record's `replicate_rule` now also carries `unfloored_score`, the live rule's score, and `sd_floor`. The
record therefore shows every cycle where the floor changed the outcome.

**The floor only lowers positive scores.** For mean(d) > 0, s ≥ sd(d), so the floored t is at most the live one. A
cycle where the amended rule fires is a cycle where the live rule fires. Its false-promotion rate under any null is
therefore at most the live rule's, which #244 measured at 1 in 1,000 windows under each shuffle null.

## The three windows, replayed (`reports/loop_replicate_rule_sd_floor_2026-10-31.json`)

`python3 scripts/loop_replicate_rule_floor.py --cycles local_data/unchanged_control/cycles_2026-10-30.jsonl --out
reports/loop_replicate_rule_sd_floor_2026-10-31.json`. Each window is replayed cycle by cycle, as the loop would see
it.

| window | cycles | live rule's first promotion | amended rule's first promotion |
|---|---:|---|---|
| batchgeneratorsv2 found, 10-17 to 10-25 | 546 | batchgeneratorsv2, 7th cycle (5.13; best 8.20) | batchgeneratorsv2, same cycle (5.13; best 8.12) |
| confirmation, 10-25 to 10-27 | 135 | batchgeneratorsv2, 6th cycle (7.17) | batchgeneratorsv2, same cycle (4.82) |
| what the loop read when it promoted lr 1e-5, 10-27 to 10-29 | 161 | lr 1e-5, 6th cycle (5.57) | none (lr 1e-5's best: 0.55) |

In the third window the amended rule's highest score is 1.00, for `multi_task_heads_False`. In the confirmation
window batchgeneratorsv2's own spread was below the field's, so the floor lowers its score from 7.17 to 4.82, still
over 4.5. That margin is thin, so the power below matters more than the replays.

## The floor's cost: power under the registered simulation

`scripts/loop_replicate_rule.py`'s `power` was the 10-26 registration's simulation: 2,000 windows per row, built from
the 546 cycles before the confirmation window, ending at batchgeneratorsv2's 8th cycle or the deadline. It is run
here unchanged with `reg=LIVE`.

| batchgeneratorsv2's effect | live rule takes it (10-26 record) | amended rule takes it | amended: another tweak first |
|---|---:|---:|---:|
| the exploratory effect | 824 of 2,000 (41.2%) | 794 of 2,000 (39.7%) | 0 |
| half of it | 41 of 2,000 (2.1%) | 5 of 2,000 (0.25%) | 0 |
| none | 0 (another tweak first: 1) | 0 of 2,000 | 0 |

In both rules 43–46 windows of each 2,000 give no reading. At the exploratory effect the floor costs 30 windows in
2,000: the rule takes it at the 6th cycle in 400 rather than 451. At half the effect it costs nearly all of what was
already rare, 41 windows down to 5. The amended rule almost never takes an effect half batchgeneratorsv2's size in 8
replicates.

The simulation's noise is exchangeable across tweaks: each simulated tweak draws from the pooled cycles. So it holds
no tweak like lr 1e-5, and it measures only what the floor costs, not what it prevents.

## The nulls

#244's two shuffle nulls on the 546 cycles, the same 1,000 shuffles (same seed), scored with the floor: 0 in 1,000
shuffled windows promote anything (95% interval up to 0.37%; live rule: 1 in 1,000). With the tweak effects centred out
first, also 0 in 1,000 (live: 1 in 1,000). The largest floored score in any shuffle is 3.89 (centred: 3.81).

## Predictions, fixed now

1. **Q1: from the pull to 2026-11-14, every cycle where the live rule would fire and the amended rule does not is a
   tweak whose own spread, on at least one measure, is below the field's.** This holds by construction. It is listed so the record's
   `unfloored_score` gets read: each such cycle is a promotion the floor refused.
2. **Q2: in that time the amended rule promotes nothing.** No tweak in the current window has shown an effect of
   batchgeneratorsv2's size. In simulation the amended rule takes an effect that size by its 8th cycle in 39.7% of
   windows, and one half that size in 0.25%. Moderate.

## Decision rule

| by 2026-11-14 | reading |
|---|---|
| the amended rule promotes a tweak | read its cycles against the incumbent before keeping it; a promotion is still one cycle's candidate |
| the floor refuses a firing the live rule would have made | that tweak gets a registered confirmation before anyone promotes it by hand |
| neither | the floor changed nothing in the window; says nothing about its power |

## What the result cannot do

- **Make the comparison the right one.** A tweak still has to beat only the other tweaks. In the 10-27 window the
  161 cycles averaged 0.00076 val_f1 below the incumbent, and the 7 control cycles 0.00101 below it. A near-no-op
  that keeps the incumbent's score sits above that bar. The floor is not an effect-size threshold either. At the
  field's 0.0019, the amended rule fires on a steady offset of 4.5 × 0.0019 / sqrt(n): 0.0035 val_f1 at 6 cycles,
  0.0011 at 60.
- **Stand for windows unlike these three.** The field's SD includes the other tweaks' real differences, so a window
  with a large real effect has a higher floor for every other tweak.

## Disclosure

On 10-31 I first recommended comparing each tweak against `control_unchanged`. That rested on 3 control cycles in
the current window, where the control led the field by 0.0025 val_f1. In the 10-27 window (161 cycles, 7 control) the
control was no better than the field: 0.00101 below the incumbent, against the other tweaks' 0.00075. I replayed that design too. It does not fire in the 10-27 window, but it cannot
be checked against batchgeneratorsv2. The lr 1e-5 stopgap (#311) removes that value from the search regardless of this
amendment.

## Cost

The live rule scores each cycle twice, with and without the floor, which takes well under a second.
