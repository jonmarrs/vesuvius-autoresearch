# The anchor ablation's control came from a different villa tree than its treated arm

**2026-09-19.** No new compute. Found while surveying every manipulation in the corpus against the
corrected noise floor (`reports/six_unused_seeds_double_the_current_floor.md`), when the anchor
study's ink effect recomputed to −5.49% where the published verdict says −0.86%.

## The mismatch

`docs/preregistration/2026-09-12_anchor_ablation.md` names `curbase_s1..s3` as BASELINE, "already
fitted and scored", and states the arms are **"identical in every other respect"**. They are not:

| arms | fitted | villa tree |
|---|---|---|
| `curbase_s1, s2` | 2026-09-07 | `d8c5f488a` |
| `curbase_s3` | 2026-09-08 | `d8c5f488a` |
| **`anchor10cov_pilot, s2`** | **2026-09-12** | **`be09a8503`** |
| **`anchor10cov_s3`** | **2026-09-13** | **`be09a8503`** |

Our submodule moved `d8c5f488a` → `be09a8503` on **2026-09-11 13:22**, between the control and the
treatment. The registration could not have caught this: `curbase_s1..s3` *were* "current villa" when
they were fitted, and "current" moved underneath the label.

**Not a process failure at analysis time.** The tree-matched control used below (`curbase_s4..s9`)
was not available: `s4`-`s6` were fitted 09-13, the same day the verdict was written, and `s7`-`s9`
only on 09-14/15. This is a confound that became *correctable* later, not one that was ignored.

## Ink: the published estimate was confounded, the verdict was not

| control | effect | p | 95% CI |
|---|---:|---:|---|
| published, `curbase_s1-s3` (different tree) | −0.86% | 0.760 | [−10.21%, +8.50%] |
| **tree-matched, `curbase_s4-s9`** | **−5.49%** | 0.192 | **[−14.52%, +3.53%]** |

**The NULL verdict stands either way** — neither is significant. What changes is the picture it
leaves: the published interval sits roughly symmetric about zero, while the tree-matched one leans
harmful and only barely includes it. Removing 49 of 59 anchors looks *more* costly than reported,
though still not established.

## Geometry: unaffected, and the study's significant result survives

| control | effect | p |
|---|---:|---:|
| published, `curbase_s1-s3` | +1.39% | 0.0032 |
| **tree-matched, `curbase_s4-s9`** | **+1.32%** | **0.0013** |

**The one significant finding in that study is robust to the control swap**, and marginally stronger.

## Why one endpoint moved and the other did not

Switching the control moves the **ink** estimate by 4.63 points and the **geometry** estimate by
0.07. The two controls differ by +4.91% in mean ink and +0.07% in mean satisfied area.

**Stated carefully: neither between-tree shift is established on its own** — ink p=0.1871, geometry
p=0.7422, both `curbase`-only comparisons at 3 vs 6. So this is a statement about **estimate
sensitivity**, not a demonstration that the code change moved ink. The useful form is: *this
comparison's ink endpoint is fragile to which control it uses, and its geometry endpoint is not.*

## What it does to the study's conclusion

It **strengthens** it. The anchor ablation was recorded as geometry-up/ink-null — the decoupling
pattern. Tree-matched, that reads geometry **+1.32% at p=0.0013** while ink is **−5.49% and
negative**. The two endpoints do not merely fail to move together; on the matched comparison they
point opposite ways.

## Limits

`curbase_s4..s9` are seed replicates of the same configuration, so they are a valid control by
construction, but they were fitted 1-2 days after the ablated arms rather than alongside them. No
`VILLA_SHA` was recorded for any fit involved (all predate that fix), so tree attribution rests on
directory dates against the submodule bump time. One dataset, one ROI, `w120-w129`.
