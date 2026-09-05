# Refitting the spiral on its own well-satisfied patches: FAILURE

**2026-09-05.** Six fits, three per arm, run over ~28 hours and analysed by
`scripts/analyse_patch_bootstrap.py` exactly as committed on 2026-09-03 before any arm existed.
Registration: `docs/preregistration/2026-09-03_patch_bootstrap.md`.

Answers an avenue villa names in `37_2026_open_problems.md`: *"identifying methods to automatically
crop 'good' regions of the spiral fit, and using these as surface patch inputs to a subsequent run"*.

## Result

| endpoint | RANDOM | BOOTSTRAP | relative | p |
|---|---:|---:|---:|---:|
| `satisfied_area_fraction` | 0.8328 | 0.9799 | **+17.66%** | 0.0000 |
| `total_fg_pixels` | 1,642,359 | 1,628,729 | **-0.83%** | 0.8915 |

Per fit:

| arm | geometry | total_fg |
|---|---:|---:|
| boot090s1 | 0.9798 | 1,488,420 |
| boot090s2 | 0.9795 | 1,768,292 |
| boot090s3 | 0.9804 | 1,629,476 |
| rand090s1 | 0.8308 | 1,564,627 |
| rand090s2 | 0.8340 | 1,644,149 |
| rand090s3 | 0.8336 | 1,718,300 |

**VERDICT: FAILURE**, by the rule registered before the data existed: geometry improved and ink did
not follow. Recorded as a failure of the method, **not a partial success**. My registered prediction
("ink null, geometry up") was **met** -- worth stating plainly, since I have been wrong on three of
five prior registered predictions and this is not evidence that the reasoning behind it was right.

## Why the geometry number is not good news

`satisfied_area` rose 17.66% because the arm was **selected for patches the reference fit already
satisfied at >= 0.90**, then scored on how well the new fit satisfies them. That is close to
circular, and it is exactly the circularity the registration named in advance as the reason a
geometry-only gain would be recorded as failure rather than promise.

This is the **second measured instance** of the two metrics moving independently, and it is starker
than the first:

| case | `satisfied_area` | `total_fg_pixels` |
|---|---|---|
| gap-expander config (`gap_fix_costs_ink_established.md`, n=12) | +1.03% | **-10.35%** |
| patch bootstrap (this study, n=6) | **+17.66%** | -0.83% (null) |

A 17.66% move in the geometry diagnostic bought nothing measurable in recovered ink. Any pipeline
using `satisfied_area` as its guard for an ink objective should treat that as a live hazard.

## What the null does and does not say

**No ink effect larger than about 10%.** Not "no effect". At three per arm and the measured outer
CV of 0.0421, 80% power reaches only ~9.6%, which was computed and recorded before the fits ran. The
arms are not separated on ink at all (no separation; per-fit ranges overlap heavily), so this is a
genuine null rather than a near miss.

Context, carrying no claim by registration because it confounds evidence quality with quantity:
BOOTSTRAP -5.29% (p=0.3820) and RANDOM -4.49% (p=0.2306) against the six full-data baselines. Both
filtered arms sit slightly below baseline and indistinguishably from each other.

## The result that makes the follow-up worth running

`patch_bootstrap_outer_evidence_deficit.md` established, before any endpoint was read, that
BOOTSTRAP carries **~11% less relative area inside the scored strip** than RANDOM, because
satisfaction falls with radius (r = -0.21).

**BOOTSTRAP nonetheless reached ink parity on that thinner evidence.** That is not a win -- the
comparison is null and a null is a null -- but it is consistent with a modest positive selection
effect being masked by an evidence deficit, and this study cannot distinguish that from nothing
happening at all.

`docs/preregistration/2026-09-04_stripmatch_followup.md`, written while these endpoints were still
unread, fixed the trigger in advance: **run STRIPMATCH on a FAILURE verdict.** That condition is now
met. The design equalises in-strip area between the arms so that any remaining difference is
selection quality alone; feasibility was demonstrated at registration time (29,661 patches matching
BOOTSTRAP's total area to 100.00% and its in-strip share to 0.4120, gap 0.0000). Cost ~16 hours.
My blind prediction there is that STRIPMATCH also shows no ink advantage.

## Validity

Every check below ran before the endpoints were read, and each is in a tested script:

* arms are subsets of the reference fit; threshold did not leak (BOOTSTRAP min fraction exactly
  0.9000); area matched 76.36% vs 76.37% (`check_patch_selection.py`);
* the six `fit_*.sh` are byte-identical apart from dataset, tag and seed; seeds 1/2/3 in each arm;
* fits pinned to villa-spiral `6847063f`, renders to `5479453a`, both enforced by
  `tests/test_villa_spiral_refs_pinned.py`;
* all six arms passed the registered non-blank control (47.5-48.6% nonzero, tightly consistent), so
  the ink comparison is not explained by one arm rendering more strip than another;
* all six produced 240 mesh entries with all ten outer windings present;
* RANDOM tracks the full population in quality (0.7986 vs 0.8003) and spatially (largest radial band
  gap 0.26 points), so the single-draw limitation is discharged on both dimensions.

The analysis refuses a partial sample and was invoked through
`scripts/run_patch_bootstrap_verdict.py`, which resolves each arm's twelve input paths and errors
rather than guessing if a tag matches more than one fit directory.

## For villa

Cropping a spiral fit's well-satisfied regions and refitting on them **raises the satisfaction
diagnostic by 17.66% and does not measurably improve recovered ink** on this ROI at this budget. The
avenue is not refuted at effects below ~10%, and one refinement remains registered and untested
(equalising coverage in the scored strip). But as stated, it does not deliver reading.
