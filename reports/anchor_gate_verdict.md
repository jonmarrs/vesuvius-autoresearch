# Gate: PROCEED. A winding name still means the same papyrus at 10 anchors

**2026-09-12.** Decides `docs/preregistration/2026-09-12_anchor_ablation_gate.md`, whose rule was
fixed before the pilot was launched. **This is a feasibility gate and says nothing about anchors or
about ink.**

## Result

`anchor10cov_pilot` (10 z-coverage-matched anchors, current villa, seed 1, 29,999/30,000 iterations,
120 windings) against `curbase_s1`, over w120–w129:

| | offsets at 0 | median self-distance | median margin |
|---|---:|---:|---:|
| **forward** (ref `curbase_s1`) | **10/10** | 24.06 vx | 2.85 vx |
| **reverse** (ref pilot) | **10/10** | 23.98 vx | 2.73 vx |

**VERDICT: NUMBERING PRESERVED → PROCEED.** The registered robustness condition is also met: every
one of the 10 windings beats its runner-up by a positive margin (2.02–5.51 vx), against a requirement
of at least 9 of 10.

The reverse direction was not registered. The measure is asymmetric, so it was run as a free check and
is reported whichever way it came out; it agrees.

## The one anomaly, chased to an explanation

The margin here (2.85 vx) is **41% tighter** than the two-seed positive control's 4.86 vx, while the
self-distance is unchanged (24.06 vs 24.01). Identification is therefore less comfortable than the
control, and the tool says so itself.

**First hypothesis — the ablated fit has tighter winding spacing — is REFUTED.** Median distance
between consecutive windings: baselines 26.44 vx pooled over three fits, ablated 26.35 vx. A 0.3%
difference, Mann-Whitney p = 0.32.

**What actually explains it: a small systematic inward radial displacement.** Median radius of each
matched winding, measured from a single fixed centre (`curbase_s1`'s strip centroid — a per-fit centre
would absorb exactly the shift being looked for):

| arm | signed displacement vs `curbase_s1` | |
|---|---:|---|
| `curbase_s2` | −1.47 vx | seed control |
| `curbase_s3` | −0.88 vx | seed control |
| **`anchor10cov_pilot`** | **−2.34 vx** | ablated |

An inward shift moves each ablated winding slightly away from the reference and toward the reference's
*inner* neighbour, compressing the margin by roughly the amount observed. **The anomaly is the
displacement, and the displacement is small.**

## Why that is reassuring rather than concerning

* **2.34 vx is 8.9% of one winding's 26.4 vx pitch.** The strip spans radius 2,337–2,466; a 2.3 vx
  shift is not a different wrap.
* **It is only ~1.6× the seed-to-seed displacement** (−0.88 and −1.47 vx). Removing 40 of 50 anchors
  moves the surface barely more than changing the RNG seed does.
* **Compare what blocked this study before:** ~15 vx at 10 anchors on the pinned tree (measured by
  radius, at 200 steps), and ~70 vx from zeroing `loss_weight_abs_winding` entirely. Neither figure
  survives on current code at convergence with a proper instrument.
* Every displacement, including both seed controls, is **inward**, so `curbase_s1` sits slightly
  outward of its own siblings and the ablated arm continues an existing trend rather than departing
  from one.

## Disclosure

The fit log prints `satisfied_area = 0.859` for the pilot, so **arm 1's geometry endpoint has been
seen before the study completed.** Unavoidable — it is fit output, not a render. It cannot bias the
verdict: the registered decision takes ink alone, no prediction was registered on either endpoint, and
the pilot is still unrendered so no ink number exists.

## Arm 2 also passes (added 2026-09-12 20:25)

`anchor10cov_s2` (seed 2, 30,000/30,000, 120 windings) against `curbase_s1`: **10/10 offsets at 0,
10/10 positive margins**. Two of three ablated arms have now cleared the gate; arm 3 is not yet
fitted, and `scripts/run_anchor_gate.py` refuses to emit an analysis invocation until it is.

Run the gate with that script rather than by hand — it applies the registered rule and generates the
`analyse_anchor_ablation.py` command with `--excluded` already filled in, so an exclusion cannot be
lost between the check and the analysis.

## Geometry so far, recorded because it is visible and because it will be tempting later

The fit logs print `satisfied_area` before any render exists:

| arm | `satisfied_area` | |
|---|---:|---|
| `curbase_s1..s3` | 0.8472 / 0.8494 / 0.8503 | baselines, from the earlier study |
| `anchor10cov_pilot` | **0.859** | arm 1 |
| `anchor10cov_s2` | **0.860** | arm 2 |

Both ablated arms sit ~1.3% above every baseline. **Unlike the same-winding study, this number is
interpretable here** — that manipulation removed 5,413 of the patches satisfaction is computed
against, so a rise could mean "less left to satisfy"; this one changes only `abs_winding.json` and
leaves the patch set identical at 38,442.

**It is recorded now, with no interpretation, precisely because a geometry rise is the result I would
be most tempted to narrate after seeing the ink.** The registered verdict takes ink alone. Whatever
the ink does, this table was written before it existed.

## What happens next

Arms 2 and 3 (`fit_anchor10cov_s{2,3}.sh`, seeds 2 and 3) are launched. The pilot serves as arm 1 per
amendment 2, recorded before this gate was read. **Each arm gets this same check**, and any arm that
fails it is excluded by name.
