# The fourth baseline seed is high, and that is worth flagging before the study ends

**2026-09-13, written while `curbase_s5` is fitting.** Not a result — a watch item recorded now so it
cannot be discovered after the fact and rationalised.

## What happened

`curbase_s4` is the first arm of the second triplet. It **passes every registered validity check**:

* non-blank control **46.7%** nonzero (the nine existing arms ran 46.8–48.2%);
* `total_fg_pixels` = **3,019,583**, inside the registered gate of 2,700,000–3,050,000.

But it sits **4.0% above the entire s1–s3 span**, and against their spread:

| | mean | sd | CV |
|---|---:|---:|---:|
| `curbase_s1..s3` | 2,882,256 | 35,706 | 0.0124 |
| **with `s4`** | 2,916,588 | 74,597 | **0.0256** |

**s4 is 3.85 sd above the s1–s3 mean, and including it doubles the current-tier ink CV.**

Its `overall_line_score` (0.3888) is also above all three predecessors (0.3291–0.3485).

## Why this is being written now rather than later

This is the **same pattern as the noise-floor retraction earlier today**: a CV estimated from three
fits (df = 2) moved sharply the moment a fourth arrived — there, 0.0125 → 0.0263 when the anchor
triplet was added; here, 0.0124 → 0.0256 with one more baseline.

Having just retracted a claim for exactly this reason, the honest move is to flag it **while the
outcome is still unknown**, not after s5 and s6 have landed and the number can be read either way.

## What it does and does not affect

**Does not affect the registered consensus prediction.** That prediction derives from `r_single =
0.718`, the *placement* correlation, not from the ink-count CV. The gate on ink exists to catch an arm
that is not comparable, and s4 is inside it.

**Does affect confidence in the current-tier ink CV**, which four separate reports quote as ~0.0124
for `curbase`. If s5 and s6 also land high, that figure is too tight and the studies budgeting from it
were under-powered — the same correction already applied once today.

## What would settle it

Three outcomes, named before the data:

1. **s5 and s6 land near s1–s3** → s4 is a genuine high draw; the CV was underestimated but not badly,
   and the pooled six-arm figure is the one to quote.
2. **s5 and s6 also land near s4** → the two triplets differ systematically, which the validity gate's
   cross-triplet single-vs-single check should also catch, and the forward test is compromised.
3. **s5 and s6 scatter widely** → the true seed CV is simply larger than three arms could show, and
   every current-tier power calculation needs revisiting.

**No action is taken on this until all three new arms are scored.** Recording it is the action.
