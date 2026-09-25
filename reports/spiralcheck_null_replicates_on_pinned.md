# The spiralcheck ink null replicates on the pinned tier, at a tighter bound

**2026-09-25.** Result of `docs/preregistration/2026-09-25_spiralcheck_pinned_replication.md`, decided by
`scripts/analyse_spiralcheck_pinned_replication.py`. The rule and tests were committed at `3054d6a1`
before spiralcheck ran on any pinned fit.

* Data: `reports/spiralcheck_pinned/collected.json`.
* Verdict: `verdict.json`.
* Unregistered leave-one-out: `leave_one_out.json`.

## Result: NO DETECTED RELATION

On 24 pinned-tier fits in six configs (df 17, critical |r| 0.561, Bonferroni α 0.0125), none of
spiralcheck's metrics tracks ink within a config. They were measured on the scored windings
w120–w129.

| metric | r | p | leave-one-fit-out r range | current tier r (df 8) |
|---|---:|---:|---|---:|
| violated_bin_fraction | +0.344 | 0.149 | +0.232 … +0.438 | −0.17 |
| collapsed_bin_fraction | −0.069 | 0.778 | −0.171 … +0.102 | +0.13 |
| inflated_bin_fraction | +0.162 | 0.507 | +0.044 … +0.332 | −0.51 |
| median_pitch | +0.058 | 0.812 | −0.036 … +0.126 | +0.54 |

**Gates passed:** for all 24 fits the two runs were identical, and the scored meshes are
byte-identical to what was rendered and scored.

**The prediction was a null on all four, at moderate confidence.** It held.

## Reading

* **The current-tier null was not just low power.** On independent data, with the bar lowered from
  |r| 0.750 to 0.561, nothing registers. No single fit's removal lifts any |r| above 0.438.
* **The two tiers do not even agree on sign** for three of the four metrics (violated,
  collapsed, inflated). That is what the absence of a relation looks like, not a weak shared one.
* **Combined verdict on spiralcheck and reading, across both tiers and 36 fits:** its winding checks
  do not predict how much ink a fit reads. They may still be sound geometry checks; that was never
  tested, because there is no positional ground truth here.

## Limits

* One region. Pinned ink is from stock (stochastic) flattens, which is noise in y and weakens r
  slightly.
* A relation with |r| < 0.56 is not excluded.
* Pinned-tier render provenance was established by content (identical render-path code in all 24
  work dirs, and one render image), not by recorded SHAs. The arms predate that recording.
