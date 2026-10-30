# Unchanged-control readout: batchgeneratorsv2 fine-tunes better than the old recipe, BEATS_UNCHANGED (2026-10-30)

**Readout of [the registered comparison](../docs/preregistration/2026-10-27_loop_unchanged_control.md).** The window
opened with the first cycle recorded with #263's identities, which started 2026-10-27 16:21:27 PDT. It ended at a
promotion: the cycle started 2026-10-29 12:40:35 (`lr_1e-05`, promoted by the replicate rule) is its last. It holds 161
cycles, in one code digest and one baseline config, all facing the incumbent `c80885969cc5…`.

The arms ran 7 times (`control_unchanged`) and 8 times (`aug_mode_albumentations`). That is fewer than the registered
10 each but at least the 6 that give a reading. The registered command ran on 2026-10-30 at about 09:10:
`python3 scripts/loop_unchanged_control.py read`. It read a byte-identical copy of the loop's `cycles.jsonl`
(`local_data/unchanged_control/cycles_2026-10-30.jsonl`, 242 records, sha256 `ae552943…`).
Record: `reports/loop_unchanged_control_2026-10-30.json`.

## The registered result

The reverse arm's mean minus the control's:

| measure | reverse | control | difference | se | t | p | registered | holds |
|---|---:|---:|---:|---:|---:|---:|---:|:---:|
| val_f1 (Q1) | 0.26728 | 0.27000 | −0.00271 | 0.00060 | −4.51 | 0.0006 | ≤ −0.002 | yes |
| ROC AUC (Q2) | 0.57607 | 0.58629 | −0.01022 | 0.00336 | −3.04 | 0.013 | ≤ −0.005 | yes |
| AP prevalence lift (Q3, reported) | 1.17598 | 1.21161 | −0.03563 | 0.01472 | −2.42 | 0.036 | ≤ −0.015 | yes |

**Reading: BEATS_UNCHANGED.** On this validation sample, from this incumbent, batchgeneratorsv2 fine-tunes better than
the old recipe, in F1 and in ranking. Each effect is about two thirds or more of the confirmation's (+0.0043 F1,
+0.0110 AUC, +0.042 AP lift), sign reversed.

Reported beside it, as registered (no reading changes):
- **Steps.** The old recipe trained 325 more steps a cycle (about 1,300 against 980). At #250's within-tweak slopes,
  that gap alone predicts −0.00016 F1, −0.0028 AUC and −0.0145 AP lift: 6%, 27% and 41% of the effects. With those
  parts removed, F1 and AUC remain past their thresholds, and AP lift (−0.021) still passes its threshold too.
- **Against the window's other tweaks** (the confirmation's comparison): the control is −0.0004 F1 and −0.0010 AUC
  from their mean, the reverse arm −0.0031 and −0.0112. The unchanged config is at the other tweaks' level; the old
  recipe is below everything.

## Audit (written after the reading; changes nothing)

The sampler placed the arms at different times: the reverse arm's cycles fall earlier in the window. A score that
drifted over the window could make one arm look better. `scripts/loop_unchanged_control_audit.py` gives these checks
on the same window (`reports/loop_unchanged_control_audit_2026-10-30.json`):

| check | val_f1 | ROC AUC | AP lift |
|---|---:|---:|---:|
| the 146 other cycles' drift per day (p) | −0.00007 (0.79) | −0.00128 (0.23) | −0.0075 (0.14) |
| difference, each arm cycle against its 6 nearest other cycles in time (p) | −0.00228 (0.011) | −0.00975 (0.041) | −0.0313 (0.11) |
| Mann–Whitney p | 0.0012 | 0.0093 | 0.029 |
| difference with each cycle left out, range | [−0.00302, −0.00240] | [−0.01217, −0.00792] | [−0.04199, −0.02504] |

No drift is detectable. Matched in time, the F1 and AUC differences stay past their thresholds. No single cycle carries
the result: every leave-one-out difference stays past its threshold. AP lift, reported only, is the weakest when
matched in time (p 0.11).

## What the result cannot do

As registered:
- It says nothing off the loop's 400 Fr143 validation patches (protocol v3).
- It does not compare the recipes from scratch: both arms fine-tune an incumbent whose last cycle trained with
  batchgeneratorsv2.
- It does not name the mechanism: the recipes differ in more than the step count.

The window ended at the replicate rule's promotion of `lr_1e-05`, before either arm reached 10 cycles. That promotion
does not enter the reading, which reads only the two arms, but it is a separate finding about the rule. Its six
`lr_1e-05` cycles scored val_f1 0.27117 with a standard deviation of 0.00004, against 0.27021 and 0.00193 for the
other cycles. It cleared the rule's t of 4.5 through low variance, and beat the incumbent by 0.0002.
