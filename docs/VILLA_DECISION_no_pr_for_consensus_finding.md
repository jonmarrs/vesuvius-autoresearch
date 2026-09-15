# Decision: the consensus result does NOT go upstream as a PR

**2026-09-15.** Recorded so it is not rebuilt. Evaluated and declined, not overlooked.

## What was considered

Adding to `spiral-fitting/autoresearch.md`, in the **Stochasticity** paragraph, that the two seeds the
loop already runs are worth more **averaged** than **compared**: a 2-seed consensus reproduces at
**r = 0.8516** against **0.7040** for a single fit
(`reports/two_seed_consensus_confirmed.md`, pre-registered and confirmed forward).

## Why not

**1. It is a recommendation, not a defect.** Every PR of ours that merged fixed something objectively
wrong or missing in villa's own tree:

| PR | what it fixed |
|---|---|
| #1721 | `autoresearch.md` named a script that does not exist |
| #1722 | `get_ink_metrics.py` writes two metrics, neither documented |
| #1780 | the doc did not say what its own robustness rule accepts |
| #1805 | `metrics.json` recorded the repo id but not which snapshot produced the score |

Eleven feature-shaped PRs were closed before that pattern was understood. This one is shaped like the
eleven, not like the four.

**2. #1780 already fixed the actual defect in that paragraph.** It now states the false-pass rate
correctly. There is nothing left there that is *wrong*.

**3. The claim is weaker than the venue needs.** Our result is **reproducibility, not accuracy**. In a
document that drives a keep/discard loop, "average them" reads as "the average is better", which is
not what was measured. We would be putting a stronger implication into villa's guidance than our own
report licenses.

**4. It concerns the artifact, not the decision.** villa's loop consumes `total_fg_pixels`, a count.
Our finding is about ink **placement**. Averaging improves the map a run leaves behind; it does not
change the keep/discard comparison the paragraph is about. Useful, but not to the thing that paragraph
governs.

## Where it lives instead

* `reports/consensus_retest_confirmed.md` and `reports/two_seed_consensus_confirmed.md` — the results.
* `reports/SPIRAL_FINDINGS_SUMMARY.md` finding 36 — the consolidated view.
* `docs/PRIZE_FILING_2026-09_SUBMIT.md` Field 1 — where a measurement about someone else's loop is
  the appropriate contribution.

**If this is ever revisited**, the thing that would change the answer is an accuracy result: evidence
that a consensus map reads *better*, not just more repeatably. That needs positional ground truth on
PHercParis4, which `reports/` records as not existing.
