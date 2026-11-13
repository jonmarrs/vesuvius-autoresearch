# Retained historical artifacts with undefined fields

The [status catalogue](historical_artifact_status.json) identifies four retained
JSON artifacts containing 30 nonstandard `NaN` tokens. It records each original
SHA256 digest and every affected JSON Pointer. The source files are preserved
byte for byte; the catalogue itself is strict JSON. This is a disposition of
those four audit findings, not validation of all historical reports.

| Artifact | Status and interpretation |
| --- | --- |
| [Old active-learning queue](active_learning_queue.json) | Unusable as a ranking: all twenty uncertainty scores are undefined. The saved order is not evidence of uncertainty. |
| [Detector scorecard](detector/PHercParis2Fr143_scorecard.json) | Partial historical metrics: `centerline_dice` is undefined. |
| [Interpolation comparison](interp_vs_labels.json) | Partial historical metrics: two alignment AUC fields are undefined. |
| [Tracking-gap description](scorer_tracking_gap_descriptive.json) | Partial historical metrics: seven within-segment correlations are undefined. |

An undefined field is not a zero measurement. Do not fill, rank or compare these
fields numerically. Unaffected finite fields keep their original historical
scope; this catalogue does not remeasure or newly validate them. Historical
tests and analyses can still read the original files, whose permissive Python
JSON parsing is not strict JSON interchange.

New queues should come from the maintained
[active-learning sampler](../scripts/active_learning_sampler.py); new scientific
measurements need retained source inputs, provenance and a new versioned output
path. Do not overwrite these originals to make an old result appear current.
