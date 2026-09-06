# Equalising outer evidence does not rescue the method: FAILURE

**2026-09-05.** Three new fits against the three existing BOOTSTRAP arms, analysed by
`scripts/analyse_stripmatch.py` exactly as committed **before the first STRIPMATCH fit started**.
Registration: `docs/preregistration/2026-09-04_stripmatch_followup.md`, written blind on 2026-09-04
while the parent study's endpoints were still unread.

## The question this answers

`reports/patch_bootstrap_verdict.md` returned FAILURE: refitting on well-satisfied patches raised
`satisfied_area` 17.66% and moved recovered ink not at all. It could not say **why**, because its
RANDOM control matched BOOTSTRAP on *global* area while BOOTSTRAP carried ~11% less relative area
inside the scored strip. Two explanations survived:

1. selecting on satisfaction picks **worse** evidence for reading ink; or
2. it simply leaves **less** evidence where the ink is measured.

STRIPMATCH equalises the strip by construction, so a remaining difference is selection quality alone.

## Result

| endpoint | STRIPMATCH | BOOTSTRAP | relative | p |
|---|---:|---:|---:|---:|
| `total_fg_pixels` | 1,693,013 | 1,628,729 | **-3.80%** | 0.5527 |
| `satisfied_area_fraction` | 0.8430 | 0.9799 | +16.24% | 0.0000 |

| arm | geometry | total_fg |
|---|---:|---:|
| boot090s1 | 0.9798 | 1,488,420 |
| boot090s2 | 0.9795 | 1,768,292 |
| boot090s3 | 0.9804 | 1,629,476 |
| strip090s1 | 0.8419 | 1,757,237 |
| strip090s2 | 0.8434 | 1,581,728 |
| strip090s3 | 0.8438 | 1,740,073 |

**VERDICT: FAILURE**, by the rule committed before the first fit. Registered prediction — "no ink
advantage for BOOTSTRAP; equalising outer evidence does not rescue the method" — **met**.

**The +16.24% geometry number carries no credit and is not evidence of anything.** BOOTSTRAP was
selected on satisfaction; STRIPMATCH was not. A large positive value there is guaranteed by
construction, and the analysis prints that caveat beside the figure rather than trusting a reader to
supply it.

## What it settles

**The coverage explanation is not supported.** The parent study's null was reached while BOOTSTRAP
carried ~11% less relative area in the scored strip, which left open that a real selection benefit was
being masked. With that evidence deficit removed, BOOTSTRAP's ink point estimate moves **further
against** it, from -0.83% to -3.80% — the opposite direction from a masked benefit. The outer deficit
was a **side effect of selecting on satisfaction, not the cause** of the parent's null.

**Two independent controls, same answer.** Three BOOTSTRAP arms have now been compared against an
area-matched random draw and against a strip-matched random draw. Neither comparison finds an ink
benefit, and neither point estimate favours BOOTSTRAP.

## What it does not settle

**Both nulls are bounded, not empty.** At three per arm and the measured outer CV of 0.0421, 80%
power reaches only ~9.6%, computed and recorded before either study ran. Neither result excludes an
ink effect smaller than roughly a tenth. "No measurable benefit at this budget" is the claim; "no
benefit" is not.

The manipulation was real and large throughout — BOOTSTRAP mean patch satisfaction 0.9908 against
STRIPMATCH's 0.8084 — so this is a negative result about a genuine contrast, not a null from a
manipulation that never happened.

## Validity

* the control matches BOOTSTRAP on total area (100.00%) **and** in-strip share (0.4120, gap 0.0000),
  removing the outer deficit: outermost radial band 12.68% vs 12.66%, against 12.26% vs 14.21% for
  the parent's RANDOM (`check_patch_spatial_balance.py`);
* the single-draw limitation is discharged: four independent draws under the same constraints agree
  to 0.0001 on in-strip share and 0.0029 on mean satisfaction while overlapping only 76-79%
  (`reports/stripmatch_draw_stability.md`);
* the six `fit_*.sh` differ only in dataset, tag and seed; seeds 1/2/3 in each arm;
* fits pinned to villa-spiral `6847063f`, renders to `5479453a`, enforced by
  `tests/test_villa_spiral_refs_pinned.py`;
* all three arms passed the registered non-blank control (47.2%, 47.9%, 48.0% nonzero) and produced
  240 mesh entries with all ten outer windings, matching the BOOTSTRAP arms structurally;
* the BOOTSTRAP arms are **reused, not refitted**, so their numbers are identical to the parent
  report by construction.

## For villa

Cropping a spiral fit's well-satisfied regions and refitting on them does not measurably improve
recovered ink — and that holds whether the comparison controls for total evidence or for evidence
inside the scored strip. The satisfaction diagnostic rises 16-18% in both studies while ink does not
follow. The avenue is not refuted below ~10%, but two pre-registered attempts with different controls
both fail to find a benefit, and the geometry signal that would make it look successful is circular.
