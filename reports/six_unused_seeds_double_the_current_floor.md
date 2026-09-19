# Six curbase seeds existed and were never used; the current-tier floor doubles

**2026-09-19.** No new compute — nine `curbase` fits were already on disk and the floor was being
estimated from three of them. Found while checking whether other analyses shared the arm-survey blind
spot that produced `reports/the_determinism_floor_rests_on_one_draw.md`.

## What was being used

`measure_noise_floor.py` defined `curbase = (curbase_s1, curbase_s2, curbase_s3)`. On disk:
`curbase_s1` through **`curbase_s9`**. The six extra fits are not variants — every fit script is
byte-identical after stripping comments **except `optimizer_random_seed`, which runs 1..9**. They are
textbook seed replicates, and they are what a seed-noise floor is supposed to be made of.

## They are not all on one tree, and that had to be handled first

Our villa submodule moved `d8c5f488a` → `be09a8503` on **2026-09-11 13:22**, and the fit directory
dates straddle it:

| fits | dated | tree |
|---|---|---|
| `s1, s2` | 2026-09-07 | `d8c5f488a` |
| `s3` | 2026-09-08 | `d8c5f488a` |
| `s4, s5, s6` | 2026-09-13 | `be09a8503` |
| `s7, s8` | 2026-09-14 | `be09a8503` |
| `s9` | 2026-09-15 | `be09a8503` |

**The script headers on `s4`-`s6` still say `submodule d8c5f488a`** — copied from `s1` and never
updated. The directory dates are the reliable record; no `VILLA_SHA` was written for any of the nine
(they predate that fix). The two groups' means differ by **4.91%**, so pooling them as one group
would book a code difference as seed noise. They are kept as two groups, and the pooled
**within**-group statistic takes both.

## The floor

| | arms | pooled CV | df | 95% CI | MDE at 3v3 |
|---|---:|---:|---:|---|---:|
| published (3 curbase seeds) | 3 | 0.0263 | 6 | [0.0169, 0.0578] | **6.0%** |
| **with all 9** | 4 | **0.0536** | **11** | [0.0380, 0.0911] | **12.3%** |

**Designs budgeted on the published figure are optimistic by 2.0×.** Any current-code null that
claimed to bound ~6% actually bounds ~12%.

### The published interval contained the new estimate — for the third time

[0.0169, 0.0578] contains 0.0536. This is now the third occurrence of one pattern:

| | published point | later value | was it inside the published CI? |
|---|---|---|---|
| 2026-09-12 → 09-13 | 0.0125 | 0.0263 | yes, [0.0075, 0.0360] |
| 2026-09-13 → today | 0.0263 | 0.0536 | yes, [0.0169, 0.0578] |

The intervals have been right every time. The **point estimates** carried confidence the data never
supported. `reports/noise_floor_by_tier.md` already drew this lesson once — "quote the interval,
never the point estimate's apparent agreement" — and the number quoted downstream was the point
estimate again, because that is what a table's headline column invites.

## "Current code is quieter" is now dead, not merely unestablished

| | pinned | current | ratio | test |
|---|---|---|---|---|
| published 09-12 | 0.0514 | 0.0125 | 4.1× | F(18,4)=16.79, p=0.0143 |
| after the anchor arm | 0.0514 | 0.0263 | 2.0× | F(18,6)=3.83, p=0.104 |
| **all 9 seeds** | 0.0514 | **0.0536** | **1.0×** | **F(18,11)=0.92, p=0.8416** |

**The two tiers have indistinguishable seed noise.** The quietness was three seeds landing close
together. This closes the question rather than leaving it underpowered.

**Strategic consequence, and it is a retraction of one.** `noise_floor_by_tier.md` concluded that
current code "REOPENS research" because 3v3 would detect 2.9% where the pinned tier needed six seeds
to approach 8%. **That is withdrawn.** Current-code studies are no cheaper per unit of detectable
effect than pinned ones, and levers dismissed as underpowered stay dismissed.

## One fit carries most of it, and it is not excludable

`curbase_s6` is the outlier: 3,454,937 against 2.82-3.02M for the other five in its group. Dropping
it takes that group's CV from 0.0742 to 0.0287.

**It is kept, because nothing identifies it as broken:**

* strip area **414,313,800** — mid-range (others 403M-425M), so not a bigger canvas
* satisfaction **0.8468** — normal (range 0.8457-0.8543)
* `overall_fg_fraction` **0.00834** against 0.00678-0.00738 for every other seed

So it genuinely fires ~13% more ink per unit area on an identical config. Excluding a fit because it
is inconvenient is how a floor gets quoted too low, which is the error this report is correcting.

**Stated honestly: the CVs are not significantly different from each other.** s1-s3 at 0.0124 carries
CI [0.0065, 0.0779] and s4-s9 at 0.0742 carries [0.0463, 0.1819] — these **overlap**, so "6× noisier"
is *not* established and is not claimed. The defensible statement is about the pooled floor, which
uses all the data and does not rest on the outlier: **0.0536, df=11**.

## Knock-on: the two-seed check catches less than reported

Recomputed with the same rule A (both new seeds beat both old), 400,000 simulations:

| true effect | at CV 0.0263 | at CV 0.0536 |
|---:|---:|---:|
| 0% (false positive) | 16.7% | 16.7% |
| +3% | 50.9% | 31.9% |
| **+5%** | **74.4%** | **44.0%** |
| +10% | 98.3% | 73.0% |

**"Two seeds catch a 5% gain 75% of the time" becomes 44%.** The false-positive half is untouched at
exactly 1/C(4,2) = 1/6 — distribution-free, so no CV enters it, exactly as documented.

## Limits

One dataset, one ROI, `w120-w129`, one scorer. The tree attribution for `s4`-`s9` rests on directory
dates and the submodule bump time, not on a recorded `VILLA_SHA`, because none was written; the
pooled within-group figure is robust to that attribution being wrong in either direction, since
splitting a homogeneous set into two groups only costs df. Whether `curbase_s6` reflects a heavy tail
in seed noise or something specific to that fit is **not settled here**.
