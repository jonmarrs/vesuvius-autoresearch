# The incumbent's saved ranking metrics are already available

The October 26 [step-count analysis](loop_steps_vs_ranking_2026-10-26.md)
left open whether the cycles rank ink worse than their unchanged starting
model. Its saved checkpoint already contains ranking metrics. Extracting
them needs no new evaluation, training, data download or GPU job.

The local `best_model.pt` is byte-identical to Git blob
`932dbb4614a9ba89711761688bf4d0482ced932c`, committed by the
[October 17 promotion](https://github.com/jonmarrs/vesuvius-autoresearch/commit/1b7a304cd459420272864ce16d45db304ff3758b).
Its SHA-256 is `6e06598b941bdb6588ccc39499bcaee181decd060a2ab8c8385b426cf01b225a`.
The checkpoint records protocol `seeded-sample-400-v3+z1-27`, all 400 patches
scored without batch errors, and validation-input fingerprint
`75e57cf994a4b5d863c2277b05fa605aa5e5e70d19e908bee7d82e7d7cee2661`.
Its recorded validation fragment is PHercParis2Fr143. These are historical
measurements saved in the checkpoint, not measurements made today.

The comparison uses only the already published 546-cycle record ending
October 25 at 14:10:57 PDT. It reads no confirmation-window measurements.

| Reference / group | Cycles | F1 | ROC AUC | AP prevalence lift |
| --- | ---: | ---: | ---: | ---: |
| Saved incumbent | one saved measurement | 0.265762 | 0.574202 | 1.169277 |
| All pre-window cycles, mean | 546 | 0.267034 | 0.577928 | 1.181224 |
| batchgeneratorsv2, mean | 26 | 0.271027 | 0.589681 | 1.218496 |
| Other tweaks, mean | 520 | 0.266835 | 0.577341 | 1.179361 |

Against that saved reference, 385 cycles have higher recorded AUC and 159
have lower AUC. Two overlap it at the logs' four-decimal precision and are
not assigned a direction. For batchgeneratorsv2, 25 of 26 are above and one
below; none overlap. All 26 have higher F1; 23 have higher AP lift and three
lower. The mean AUC difference is +0.015479 and F1 difference +0.005265.

This answers the narrow descriptive question: the pre-window candidate
cycles do not all score below the checkpoint's saved ranking reference.
These are raw means against one saved measurement, not the epoch-matched
effects against other tweaks in the replication report. No significance
test is performed. The checkpoint was itself selected through promotion.

There are limits to comparability. The cycle rows do not contain per-cycle
validation-input fingerprints, so this comparison cannot independently
verify exact input equality for every cycle. It does not freshly evaluate
the incumbent under each code epoch or today's runtime. A saved model with
zero further updates is also not an unchanged-training control run for the
same wall time or number of steps. Everything remains on the reused Fr143
validation sample; there is no cross-scroll or post-promotion result.

No registered prediction, analysis rule, live-loop setting or checkpoint
was changed. The batchgeneratorsv2 confirmation and replicate-rule test
must still wait for their registered stopping condition and keep their
original readings. The saved reference does not justify promoting a model
or rewriting the October filing as a confirmed ink-model improvement.

Reproduce the [machine-readable record](loop_incumbent_reference_2026-10-27.json):

```sh
python3 scripts/loop_incumbent_reference.py \
  --checkpoint best_model.pt \
  --record reports/loop_tweak_replication_2026-10-25.json \
  --out reports/reference-reproduction.json
```

The tool hashes and reads the same captured input bytes, loads metadata on
CPU without constructing a model, rejects records reaching the confirmation
window or naming another incumbent, and refuses to overwrite either input.
The rounding bounds are ±0.00005 for the four-decimal AUC and AP-lift logs;
they describe serialization precision, not statistical uncertainty.

Verification passed 143 focused checks, including the saved-reference
reproduction, pre-window analyses, registered rule, filing checks and suite
coverage guard. A portability fix to the step-analysis reproduction test
allows last-bit floating-point roundoff (largest observed difference
1.7×10⁻¹⁸), while keeping identities, counts and permutation p-values exact.
The analysis code, published numerical record and registered rules are unchanged.
