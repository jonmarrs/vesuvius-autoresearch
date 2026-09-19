# The nine consensus arms differ only by RNG seed — verified, not assumed

**2026-09-18.** A validity audit, not a finding. Third axis of the question opened by the
config-override check: *could any study here have silently measured nothing?*

## Why this one matters most

Every result in the consensus line rests on one sentence: the arms are **"fits differing only by RNG
seed"**. If two arms had accidentally shared a seed they would be near-identical, inflating every
correlation. If an arm carried a different config, it would not be a seed replicate at all, and the
noise model underneath findings 36, 40, 42 and 43 would be measuring something else.

It had never been checked directly.

## Result

**Seeds are distinct**, one per arm:

| arm | s1 | s2 | s3 | s4 | s5 | s6 | s7 | s8 | s9 |
|---|---|---|---|---|---|---|---|---|---|
| `optimizer_random_seed` | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 |

**Configurations are identical.** Stripping comments and blank lines, and normalising the run tag and
the seed value, all nine fit scripts hash to **`6b7e794634b2f1d6`** — a single distinct value.

**The seeds demonstrably took effect**: all nine arms produced distinct `total_fg_pixels`
(2,818,864 – 3,454,937). A seed that was set but ignored would have given identical outputs.

So the claim holds on all three counts: distinct seeds, identical configuration, and observable effect.

## The false alarm, and what caused it

A first pass hashed the scripts after normalising only the tag and the seed, and reported **seven
distinct hashes** — which would have meant the arms were not seed replicates and would have undercut
the whole line.

The difference was **entirely comment text**: each script carries a header naming which triplet it
belongs to and which registration it serves (`"Baseline seed 4 of the SECOND independent triplet…"`).
Those headers are good practice and they are what the crude hash was counting.

**The lesson is about the check, not the data.** A normalisation that does not strip comments compares
documentation, not configuration, and a study's own careful annotation is exactly what makes its
scripts textually different. The corrected check ignores comments and blank lines.

## Audit status across the three axes checked

| axis | question | result |
|---|---|---|
| config overrides | could a typo'd key silently run defaults? | **no** — `fit_spiral.py` raises |
| dataset subsets | did any arm use a defective subset? | **no** — defective ones are smoke-only |
| seed replication | do the arms differ only by seed? | **yes** — verified here |

Three ways a study could have silently measured nothing, all closed.
