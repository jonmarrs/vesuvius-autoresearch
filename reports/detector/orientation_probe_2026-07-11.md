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
