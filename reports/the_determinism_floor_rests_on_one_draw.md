# The pipeline determinism floor was measured twice, 892× apart, and only one number was published

**2026-09-19.** Found while surveying the 16 scored arms my listings had never included
(`reports/can_the_objective_be_won_without_reading.md`). No new compute.

## The published floor

`reports/pipeline_determinism_and_which_floor_applies.md` states: *"The pipeline is deterministic to
1.4%"*, from re-rendering `baseline01`'s meshes:

| run | `total_fg_pixels` |
|---|---:|
| original (`render_lasagna`) | 240,088 |
| repeat (`dup_armREPEAT`) | 236,683 |

**ΔT = −1.4182%.** That floor is what reinstated arms B and D in the duplicate-coverage verdict,
which they clear by 8.9× and 12.4×.

## A second measurement of the same thing

`probe_innerprob` re-renders `seedarm_04`'s meshes. Same comparison, never used as a floor:

| run | `total_fg_pixels` |
|---|---:|
| `seedarm_04` | 250,936 |
| `probe_innerprob` | 250,940 |

**ΔT = +0.0016%.** Four pixels.

**Both pairs verified byte-identical: 30/30 mesh tifs match by md5**, and both share `fg_threshold`
0.5, folds `[0,1,2]`, and the same model. **The two measurements differ by 892×.**

## What this does and does not change

**It does not overturn the duplicate-coverage verdict.** 1.42% is the *larger* of the two, so using it
as a floor was the conservative choice, and arms B and D clear it comfortably either way.

**It does undercut the characterisation.** *"The pipeline is deterministic to 1.4%"* reads as a
property of the pipeline. It is one draw. A second draw of the same quantity gives 0.0016%, and the
floor's report quotes neither a spread nor a second sample.

## Two explanations, and why I cannot choose between them

**Run-to-run non-determinism** — the report's own reading, "threshold-boundary pixels under three-fold
nnU-Net ensembling and GPU non-determinism". If so, the effect is wildly heteroscedastic: sometimes
four pixels, sometimes 3,405.

**A render-code difference.** `reports/rerender_test_verdict.md` measured **+1.44%** from a
render-code change — within rounding of this floor's 1.42%, and that coincidence is hard to ignore.

**The timing argues against the code explanation**, which is why I am not claiming it: the tightly
reproducing pair was rendered **six days apart** (2026-08-31 → 09-06) while the 1.42% pair was
rendered **5.5 hours apart** on one day. More elapsed time, tighter agreement.

**And neither pair recorded a `VILLA_SHA`** — all four predate the provenance fix of 2026-09-14. So
which villa tree each ran on is unrecoverable, and the question cannot be settled from what is on
disk.

## What would settle it

Re-render one mesh set twice under a pinned `VILLA_REF`, back to back. That is ~5 h and it is the kind
of measurement the `VILLA_SHA` recording now makes interpretable — the reason that fix exists.

Worth doing only if a floor is load-bearing for a future verdict. It is not load-bearing for any
current one: every verdict resting on it used the conservative number.
