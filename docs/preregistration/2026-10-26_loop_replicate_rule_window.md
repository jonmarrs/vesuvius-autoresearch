# Pre-registration: does the replicate rule, frozen before the window, take batchgeneratorsv2 on the confirmation's cycles?

**Written 2026-10-26 (about 08:30 PDT), during the window of
[the batchgeneratorsv2 confirmation](2026-10-25_loop_batchgeneratorsv2.md) and before any analysis of it.** Of the
window I have seen cycle names and start times (to count batchgeneratorsv2's cycles toward the stopping rule) and two
`history.tsv` rows that carry no measure this or the confirmation reads (disclosed in #244). No val_f1, AUC or AP
lift of a window cycle has been read.

## The question

[#244](../../reports/loop_replicate_rule_2026-10-26.md) replayed a promotion rule over replicates on the 546 cycles
before the window: promote a tweak's cycle when the tweak has at least 6 cycles and Student's t of its epoch-matched
differences from the other tweaks exceeds c on both val_f1 and ROC AUC. It chose c = 4.5, the smallest threshold
with at most 1% false promotions per window under two shuffle nulls (1 in 1,000 under each). On those cycles the rule
took batchgeneratorsv2 at its 7th cycle and nothing else, but that was the record the tweak was found in. The window's
cycles did not exist when c was chosen. If the rule, unchanged, takes the confirmed gain on them and nothing else, the
owner has an out-of-sample case for it. If it promotes something else, or a gain the confirmation does not confirm,
the case is against it as specified. If it takes nothing, the question is how slow it is, which is answered below
before the window closes.

This tests the rule, not batchgeneratorsv2. It reads the same cycles as the confirmation, so its outcome is not
further evidence about the tweak.

## Reachability

The rule needs each window cycle's tweak, code epoch, start, val_f1 and ROC AUC, in the order they ran. The
confirmation's registered command writes exactly these (`rows` in its output) and its verdict. On the 546 cycles
before the window the same join matched every cycle to its run, AUC included. The rule's checkpoint would be the
promoted cycle's own candidate: `last_model.pt`, overwritten by the next cycle. From 2026-10-26 08:03 every cycle's
candidate is copied to `local_data/loop_candidates/window_2026-10-25/` by `scripts/snapshot_loop_candidates.sh`
(read-only towards the loop). The window's first three batchgeneratorsv2 cycles ran before that, and the rule cannot
fire before a tweak's 6th cycle, so any candidate it would promote is kept.

## The floor

The false-promotion rate of the rule at c = 4.5: 1 in 1,000 546-cycle windows under each of #244's two shuffle nulls
(95% interval up to 0.56%). The simulation below gives the same order: 1 false promotion in 2,000 windows like this
one, and 1 in 1,000 run on to the standing tweak's 20th cycle.

## The rule, frozen

`scripts/loop_replicate_rule.py`, `REGISTERED`: tweak `aug_mode_batchgeneratorsv2` standing; measures val_f1 and
ROC AUC, both required; at least 6 of the tweak's cycles; each difference against at least 10 other cycles of its
epoch; c = 4.5. Scores are computed as in #244's `scores`, at the end of each cycle, from cycles that have ended.

## Window

The confirmation's window, cycle for cycle: from 2026-10-25 16:00 PDT to the end of the 8th batchgeneratorsv2 cycle,
2026-10-29 16:00 PDT, or a promotion, whichever is first. Cycles after the 8th batchgeneratorsv2 cycle are dropped,
as the confirmation's verdict drops them. The rule starts at the window's first cycle: no earlier cycle counts. Code
epochs are the confirmation's: a merge into the loop's checkout during the window splits them as its Amendment 1 and
Window section say.

The input is the confirmation's own output, from Amendment 1's command:

    python3 scripts/loop_replicate_rule.py --window reports/<the confirmation's output>.json --out reports/<X>.json

It refuses an output whose registered window differs, or with a cycle before the window. When the confirmation gives
no reading (INCOMPLETE, UNMATCHED_RUNS), this gives none.

## Power, computed before the window closes

`python3 scripts/loop_replicate_rule.py --record reports/loop_tweak_replication_2026-10-25.json --power` runs
2,000 simulated windows per row, built from the 546 cycles before the window only
(`reports/loop_replicate_rule_window_power_2026-10-26.json`). Noise: every cycle with its tweak's effect taken out and
its epoch's mean removed. A simulated cycle is batchgeneratorsv2 at the record's rate (26 in 546), with the next of its
own 26 cycles' noise plus a share of its measured effect (val_f1 +0.0043, AUC +0.0122). Otherwise the noise is the
next of the other 520 cycles, and the tweak is drawn apart from it. The window ends at the 8th batchgeneratorsv2 cycle
or at 273 cycles, the deadline's count at the pace of the cycles before the window (the window's own pace is faster,
which only makes "no reading" rarer).

| batchgeneratorsv2's effect in the window | first promotion: batchgeneratorsv2 | another tweak | none | no reading |
|---|---:|---:|---:|---:|
| the exploratory effect | 41% | 0.0% | 56% | 2.3% |
| half of it | 2% | 0.0% | 96% | 2.1% |
| none | 0% | 0.1% | 98% | 2.1% |

Run on to batchgeneratorsv2's 20th cycle with no deadline (1,000 simulated windows each; reported, not part of the
reading): at the exploratory effect the rule takes it by the 9th cycle in 53% of windows and by the 12th in 80%. At
half the effect it takes it by the 20th in 7.8%. The confirmation's own thresholds assume about half the effect.

So the rule is safe and slow. At c = 4.5 it takes an effect of batchgeneratorsv2's exploratory size in about 9
replicates, nearly three days at the 3.2 cycles a day the loop gave that tweak before the window, and almost never
takes one half that size.

## Predictions, fixed now

1. **Q1: the rule's first promotion in the window, if any, is batchgeneratorsv2.** Another tweak first has
   probability about 0.1% under the null. High.
2. **Q2: the rule does not take batchgeneratorsv2 within the window.** It takes it in 41% of windows at the full
   exploratory effect and 2% at half; a picked winner usually regresses. Moderate.

## Decision rule

| rule's first promotion | confirmation reads CONFIRMED | confirmation reads F1_ONLY or NOT_REPLICATED |
|---|---|---|
| batchgeneratorsv2 | TAKES_CONFIRMED_GAIN: the rule chosen before the window took the confirmed gain and nothing else, within 8 replicates | PROMOTES_UNCONFIRMED: it promoted a gain the confirmation does not confirm; against adopting it as specified |
| another tweak | PROMOTES_ANOTHER_TWEAK: 0.1% under the null, so the shuffle nulls understate the live loop's false promotions, or another tweak has an effect; against adopting it at c = 4.5 without more study | PROMOTES_ANOTHER_TWEAK, as left |
| none | MISSES_CONFIRMED_GAIN: the rule needs more than 8 replicates for this effect, as the power table expects; says nothing against its false-promotion rate | ABSTAINS: consistent with the rule; says nothing about its power |

INCOMPLETE or UNMATCHED_RUNS from the confirmation: no reading here either. The tests check that these two give no
outcome and no promotion.

`scripts/loop_replicate_rule.py` implements the table (`window_test`, `READINGS`).
`tests/test_loop_replicate_rule.py` checks each cell on synthetic windows, the cut at the 8th standing cycle, the
refusals, that the rule is the one #244 chose (c from its committed record), that the confirmation's cut and minimums
are the ones its script registered, and that the power record and this document agree.

The window test also reports the rule's null on the window's own cycles (1,000 shuffles, plain and centred, as in
#244). It changes no reading.

## What the result cannot do

- **Say anything new about batchgeneratorsv2.** It reads the confirmation's cycles.
- **Measure the rule after a promotion.** Every window cycle fine-tunes the same incumbent.
- **Stand for the rule over a longer stretch.** One window, at most 8 looks at the standing tweak. The power table and
  the 20-cycle run above are simulations: they assume the noise is exchangeable across tweaks and in one code epoch,
  and they draw tweaks independently at the record's rates, where the loop's sampler weights tweak families by past
  success and avoids recent repeats.

## Disclosure

My first version of the simulation drew each simulated cycle's tweak together with that cycle's own noise, so a
tweak with 13 cycles re-drew those 13. The repeats shrank its spread and gave 1.1% false promotions per window and
1.8% over the 20-cycle run, ten times #244's nulls. I saw those numbers and the first power figures (43% and 3.6%)
before fixing it. The rule, its threshold and the window were fixed by #244 and the confirmation before that, and are
unchanged.

## Cost

None beyond the loop's own cycles. The window test takes about a minute of CPU after the window closes. The candidate
copies take about 41 MB a cycle, at most about 12 GB to the deadline.

## Amendment (2026-10-27, after the readout; the owner's decision)

The confirmation's registered command gave UNMATCHED_RUNS, so this test, as registered, gives no reading either. With
the confirmation's audited join, which the owner accepted on 2026-10-27
([readout](../../reports/loop_confirmation_readout_2026-10-27.md)), it reads TAKES_CONFIRMED_GAIN. The rule first
promotes batchgeneratorsv2, at its 6th window cycle (score 7.17). Q1 holds and Q2 fails. That reading is post hoc for
the same reason as the confirmation's. The owner decided to adopt the rule in the live loop beside the 0.01 margin.
