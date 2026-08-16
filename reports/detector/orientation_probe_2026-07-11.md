> **⚠ PARTIALLY RETRACTED — 2026-08-15.** This probe's premise for `20231005123336` was our
> own bug, so its conclusions about that segment are void. What it says about
> `20230702185753` stands.
>
> **Void: "the canon teacher is chance-quality on `20231005123336`".** The enrichment
> collapse there (≈1 across all four candidates) was a *second* hardcoded `LEVEL0_SHAPE`, in
> `gt_register.py`, found 2026-08-14 — a month after this probe ran. That segment's true
> level-0 is 34880×97280 against the assumed 50600×36400, a 167% x-scale error that
> scattered the label, and a scattered label enriches at ≈1 against **any** teacher,
> including a good one. Re-registered with the fix, teacher-enrichment is **4.88** and the
> orientation is decisively determined. The teacher was never chance-quality there; the
> registration was broken.
>
> **Therefore void, in the Consequences below:**
> * Consequence 2's claim that half the GT fine-tune's training labels may have been
>   "geometric noise". The labels were fine. That negative was retracted outright on other
>   grounds, and the experiment is now known to be **not testable** at all — see
>   [`gt_training_data_exhaustion_2026-08-15.md`](gt_training_data_exhaustion_2026-08-15.md).
> * Consequence 3's distillation narrative, which rests on students imitating a
>   chance-quality teacher on this segment.
> * Consequence 1's *reason* for withholding `20231005123336_y4000_x2500`. It stays
>   withheld, but on placement (57.5 level-2 px, ±1 px, against a 48 px gate), not on
>   unverifiable orientation. ScrollGT was corrected 2026-08-15.
>
> **What survives.** The method is sound, and `20230702185753` was never affected: the
> hardcoded constant was its own geometry, so its direct probe result (enrichment 3.13
> against ≤1.50 for the alternatives) is unchanged and still validates that orientation.
>
> The lesson is the one this project keeps relearning: a diagnostic that reads "chance" is
> evidence about the *measurement* as much as the subject, and the favourable reading is not
> the one to trust. Nothing below is deleted.

# 4-candidate orientation probe (2026-07-11)

**Question:** the GT registrations produced by `repro/sota_data/gt_register.py` carry the
`rowHv_colu` UV convention as a fixed export-pipeline prior. Is that orientation actually
correct per region — especially on segment `20231005123336`, where the canon teacher
scored exact chance against the registered GT (ROC 0.493, AP-lift 0.989)?

**Method:** the NN bridge (region 3D point → nearest `original.obj` vertex) is
convention-independent, so one KDTree query per region supports all four candidate UV
conventions. For each candidate, warp the 2023 hand label into the region and compute
teacher-enrichment = P(teacher-positive | registered-ink) / P(teacher-positive).
Script: session scratchpad `orientation_probe.py` (uses `gt_register.parse_obj_vt`,
`register.warp_via_field`, `register.label_line_periodicity`).

## Results

**CONTROL `20230702185753_y7000_x4000`** (same segment as the enrichment-validated
slice-5 region; residual 8.07):

| convention | enrichment | periodicity |
|---|---|---|
| rowv_colu | 0.809 | 0.950 |
| **rowHv_colu** | **3.134** | 0.856 |
| rowv_colWu | 1.496 | 0.851 |
| rowHv_colWu | 1.103 | 0.619 |

→ `rowHv_colu` clearly dominant: probe machinery validated, and this region's
orientation is now DIRECTLY validated (upgraded from prior-carried). Shipped as a
ScrollGT target with a canon-teacher baseline (val_f1 0.4627 / lift 2.2425 / roc 0.7259).

**SUSPECT `20231005123336_y4000_x2500`** (residual 8.03, teacher_rate 0.153):

| convention | enrichment | periodicity |
|---|---|---|
| rowv_colu | 0.815 | 0.910 |
| rowHv_colu | 0.921 | 0.932 |
| rowv_colWu | 0.792 | 0.911 |
| rowHv_colWu | 1.020 | 0.930 |

→ ALL candidates ≈ 1: the canon teacher is chance-quality on this segment, so
enrichment cannot discriminate orientation; text-line periodicity is flip-invariant
(0.91–0.93 for every candidate) so it cannot either. **The region's 2D orientation is
unverifiable with current tools.**

## Consequences

1. **ScrollGT:** `20230702185753_y7000_x4000` shipped (v0.1.1); `20231005123336_y4000_x2500`
   WITHHELD with the reason documented in the benchmark's BASELINES.md.
2. **GT fine-tune negative (additional confound, disclosed):** segment `20231005123336`
   supplied 2 of the 4 GT fine-tune training regions. Their labels pass residual+periodicity
   but their orientation cannot be verified, and the teacher there is chance-quality. If the
   orientation prior is wrong on that segment, half the fine-tune training labels were
   geometric noise — consistent with (and possibly contributing to) the observed
   collapse-to-trivial. Addendum added to `gt_finetune_heldout.md`.
3. **Distillation narrative sharpened:** `20231005123336` was also a distillation TRAINING
   segment — students were partly trained to imitate a teacher that is chance-quality vs
   human GT there (with the same orientation caveat attached). Either reading reinforces
   the held-out finding: agreement-with-teacher ≠ reading.
4. **Tooling note:** any future `gt_register.py` use should run this 4-candidate probe
   per segment instead of trusting the fixed convention; segments with uninformative
   teachers need an independent orientation check before their labels are used for
   anything.

## Addendum (2026-07-12): the three new registrable segments — all blocked

The v0.2 inventory (44 GP-winner 2023 labels × 81 bucket Scroll-1 segments) yields 6
fully-registrable segments; the 3 unused ones were probed
(`orientation_probe_new_segments.json`):

| segment | probe result | verdict |
|---|---|---|
| 20230929220926 | all candidates ≤ 1 (0.20–0.99) | teacher uninformative → orientation unverifiable → WITHHELD |
| 20231106155351 | flat (0.82–1.04) | teacher uninformative → orientation unverifiable → WITHHELD |
| 20231022170901 | probe crashed: its 2023 label exceeds cv2.remap's 32767-px limit | UNRESOLVED (tooling; fixable by tiling the warp) |

**Pattern (now 5 of 7 probed segments):** the released canon prediction is too weak
off its showcase segments for teacher-enrichment to validate registration orientation.
ScrollGT expansion is therefore blocked on an **independent orientation check** (candidate:
warp the old segment's surface texture through the same field per convention and NCC
against the SOTA surface — convention-sensitive and teacher-free), not on data
availability. Also fixed en route: `distill_run.extract_region`'s "2.4um sorts first"
zarr-selection assumption (false for segments with 1.129um scans).

## Addendum 2 (2026-07-12): independent surface-NCC orientation check — built, segment-conditional

Method (`repro/sota_data/probe_orientation_ncc.py`): warp the OLD segment's depth-averaged
surface intensity through the same correspondence field per UV convention and compare
against the SOTA region's depth-averaged surface (global NCC + median of per-512px-tile
NCC). Teacher-free and convention-sensitive. Results (`surface_ncc_probe.json`):

| case | winner | winner NCC (raw / tile-med) | others |
|---|---|---|---|
| CONTROL-A 20230702185753_y7000_x4000 (known rowHv_colu) | **rowHv_colu** ✓ | **0.280 / 0.231** | ≤ 0.016 |
| CONTROL-B 20231210121321_y4000_x2500 (known rowHv_colu) | none — FLAT | ±0.016 | — |
| SUSPECT 20231005123336_y4000_x2500 | none — FLAT | ≤ 0.021 | — |

**Operating envelope:** the check is decisive where it fires (Control-A: ~15× over
runner-up) but can be silent on a correctly-registered segment (Control-B) — so a flat
profile is NON-EVIDENCE, never refutation. Gate policy: a target ships only when at least
one independent check fires (teacher-enrichment OR surface-NCC); flat-everywhere targets
stay withheld. Consequences: `20230702185753_y7000_x4000` is now DOUBLE-validated
(enrichment 3.13 + NCC 0.28); the withheld `20231005123336` target remains withheld (no
check fires); applying NCC to the two teacher-uninformative new segments requires their
SOTA region layers (S3 extraction) — feasible follow-up.

> **⚠ See the retraction banner.** "No check fires" on `20231005123336` is void: the checks
> were being run against a label scattered by the second hardcoded `LEVEL0_SHAPE`.
> Re-registered, teacher-enrichment fires decisively at 4.88. The target does remain
> withheld, but on placement (57.5 ±1 level-2 px vs a 48 px gate), not for want of a check.
> The gate policy stated here — ship only when an independent check fires — is unaffected
> and still correct.

## Addendum 3 (2026-07-12): third segment probed via crop-offset warp — also flat; the pattern is complete

`20231022170901` (label 6656×35840 — warped via a crop-offset wrapper around
`warp_via_field` to clear cv2.remap's 32767px limit): residual 7.83, but enrichment flat
(rowHv_colu 1.02 vs 0.41–0.81) — teacher uninformative, orientation unverifiable,
NOT shipped (`orientation_probe_170901.json`).

**Final tally across all 6 registrable Scroll-1 segments:** the teacher-enrichment
check FIRES on exactly one segment (20230702185753: 5.05 and 3.13 on its two regions);
it is flat on 20231005123336, 20230929220926, 20231106155351, and 20231022170901, and
only weakly corroborative (1.68) on the held-out 20231210121321. Combined with the GT
calibrations (ROC 0.49–0.73 segment-dependent), the released canon prediction is
enrichment-informative on ~1 of 6 registrable segments — it reads its showcase segment
family and little else. ScrollGT expansion now requires the surface-NCC check, which
needs the segments' 2023-era layers (dl.ash2txt.org, credentialed) — or a future
independent orientation method.
