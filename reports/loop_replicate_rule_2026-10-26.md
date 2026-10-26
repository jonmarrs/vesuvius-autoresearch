# A rule over replicates would have promoted batchgeneratorsv2 on 2026-10-20 (2026-10-26)

**Question.** The loop promotes a cycle only when its val_f1 clears the stored incumbent by 0.01. From the
2026-10-17 promotion to 2026-10-25 none did, though `aug_mode_batchgeneratorsv2` beat the other tweaks on every
cycle it ran ([the replication report](loop_tweak_replication_2026-10-25.md)). Would a rule over a tweak's
replicates have taken it, and how often would that rule promote a tweak that does nothing?

**Source.** The 546 cycles of `reports/loop_tweak_replication_2026-10-25.json`, 26 tweaks in 8 code epochs, replayed
in the order they ran by `scripts/loop_replicate_rule.py`. It reads no cycle of the registered confirmation's window,
which began 2026-10-25 16:00. Every figure below is in `reports/loop_replicate_rule_2026-10-26.json`.

**The rule.** At the end of each cycle, take that cycle's tweak, T. Compare each of T's cycles so far with the mean of
the other tweaks' cycles so far in the same code epoch. Then take Student's t on those differences, once for val_f1
and once for ROC AUC. The rule promotes the cycle's candidate when T has at least 6 cycles and both t values exceed a
threshold c. It uses only cycles that have ended, as a live loop would.

**The false-promotion rate.** The tweak labels were shuffled 1,000 times within each code epoch, and the rule was
replayed on each shuffle. A window in which it promoted anything counts as a false promotion. The plain shuffle also
spreads batchgeneratorsv2's real gain over other labels. So a second, centred null first removes each tweak's measured
effect from its cycles, then shuffles. A threshold is accepted only if both nulls promote in at most 1% of windows.

**This is exploratory.** batchgeneratorsv2 was found in these cycles, so the date the rule would have taken it is
in-sample. The false-promotion rates come from shuffled labels and are not in-sample. Before choosing the 1% target
and the grid of thresholds I saw a prototype: 200 plain shuffles, and the real cycles' first promotion at c = 3 to 6.

## Result

| rule | smallest c at ≤ 1% | false promotions per 1,000 windows (plain, centred) | first promotion on the real cycles |
|---|---:|---:|---|
| val_f1 and AUC, ≥ 6 cycles | 4.5 | 1, 1 | batchgeneratorsv2, cycle 143, 2026-10-20 19:59 |
| val_f1 and AUC, ≥ 8 cycles | 4.0 | 1, 6 | batchgeneratorsv2, cycle 167, 2026-10-21 02:38 |
| val_f1 alone, ≥ 6 cycles | 6.0 | 5, 10 | batchgeneratorsv2, cycle 143, 2026-10-20 19:59 |

* **With both measures, the rule takes batchgeneratorsv2 and nothing else.**
  * At c = 4.5 it would have promoted at batchgeneratorsv2's 7th cycle: 3 days after the incumbent, and nearly 5
    days before the replication report found the tweak.
  * That cycle's candidate scored val_f1 0.2712 and AUC 0.590. It was 0.0054 above the stored incumbent, under the
    current rule's bar of 0.2758.
  * batchgeneratorsv2's score peaks at 8.2. The next tweak's peak is 3.11 (`use_uamt_False`).
  * Both nulls promoted in 1 window of 1,000 (95% interval up to 0.56%).
* **The threshold has to be high.** The rule looks at each of 546 cycles, and some tweaks have only 6 replicates.
  At c = 3 it promotes in 37 and 88 windows of 1,000 under the two nulls.
* **val_f1 alone is not enough.** On val_f1 alone the same rate needs c = 6.0, and the rule would then also promote
  `use_uamt_False`, whose val_f1 t peaks at 12.8. Its AUC does not move (the replication report), so the gain is in
  the threshold grid's F1, not in ranking ink. The AUC requirement is what keeps it out.
* **The current rule promoted nothing in these 546 cycles**, real or false.

## What this means for the loop

These are the owner's decisions, after the registered confirmation reads out.
* **The rule needs a record the loop does not keep.** Each cycle's tweak and val_f1 are in the sprint log, and its
  AUC is in the run log. `history.tsv` has neither, and no file names the code a cycle ran: this study joined the
  logs by val_f1 and took the code epochs from the checkout's reflog. The rule would need each cycle's tweak, val_f1,
  ROC AUC, code commit and incumbent in one record, written when the cycle is scored.
* **It promotes one cycle's candidate.** Like the current rule, it would make that checkpoint the incumbent and keep
  the tweak in `config.json`. It would then start over against the new incumbent's cycles.
* **It can run beside the current rule.** The single-cycle rule still takes a large one-cycle gain; this one takes a
  small gain that recurs.

## What it does not say

* **That a promoted batchgeneratorsv2 checkpoint reads ink better.** Every score is on the loop's 400 Fr143
  validation patches, as in the replication report.
* **How the rule behaves after a promotion.** Every cycle here fine-tunes the same incumbent. The window after a
  promotion is not measured.
* **How it does over a longer window.** The rates are per window of 546 cycles. A longer window between promotions
  gives the rule more looks, and its false-promotion rate grows.
* **That beating the other tweaks means beating an unchanged config.** The loop runs no unchanged cycle, so the
  reference is the other tweaks, as in the replication report.
