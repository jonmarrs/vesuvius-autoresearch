# Held-out ground-truth registration (`20231210121321`) — registration SUCCEEDED, scoring DEFERRED

**Status:** registration validated on **teacher-free** evidence; the enrichment gate
false-negatived because the canon teacher reads this held-out segment poorly. Scoring against
the students is **deferred pending a gate-override decision** (see options at end). No numbers
are scored against this label yet — the "no scoring against a misaligned label" discipline is
held.

## What happened

The bridge (region 3D → nearest `original.obj` vertex → 2023-label texture coord → sample the
hand label) landed cleanly: **3D correspondence residual median 7.85 old-scan voxels**, versus
the independently-validated slice-5 `orig` registration's **7.92** — the same pipeline at the
same geometric quality. The overlay (`registered_gt_heldout_overlay.png`) shows the registered
hand label as **crisp, legible Greek letterforms in clean horizontal text lines**.

But the **alignment gate failed**: teacher-enrichment 1.68 (< 3.0 threshold), with no vt
convention separating (1.24 / 1.68 / 1.52 / 1.52). Inspecting the overlay shows why — the
**canon teacher on this held-out segment is scattered noise that does not form letterforms**,
while the registered human label (red) is clean text. Enrichment is a *teacher-dependent*
metric (registered-ink-inside-teacher ÷ outside); when the teacher itself is poor, enrichment ≈ 1
even under perfect registration. So the gate cannot distinguish "misaligned label" from "weak
teacher" — and here it is the latter.

## Teacher-free alignment evidence (registration is sound)

| criterion (teacher-free) | slice-5 `orig` (VALIDATED) | this `heldout` |
| --- | --- | --- |
| 3D correspondence residual (median, old-scan voxels) | 7.92 | **7.85** |
| registered-label text-line periodicity (row autocorr. peak) | 0.900 | **0.871** |
| vt convention | `rowHv_colu` | `rowHv_colu` (export-pipeline constant) |
| visual: coherent letterforms in text lines | yes | yes |

All teacher-free signals match the validated `orig` registration. The vt convention is a
property of the segment's OBJ export, which slice 5 established decisively (`rowHv_colu`,
enrichment 5.05) on the same scroll/scan/tooling — so it is not in doubt here despite the weak
enrichment margin.

## Finding (independent of scoring)

**The canon `new_canon_autoresearch_recipe` prediction reads this held-out Scroll-1 segment
poorly** — scattered, non-letterform output where human ground truth shows clean text. This is
the first direct observation of the released teacher failing on a specific segment, and it
matters: it means agreement-with-teacher would *reward* a student for reproducing this segment's
noise. A held-out ground-truth score here would measure real reading ability, not teacher
mimicry.

## Decision required (why scoring is deferred)

The enrichment gate is teacher-dependent and gave a false negative. Proceeding to score requires
either (a) validating on the teacher-free criteria above (residual + periodicity + visual +
convention prior), or (b) codifying a teacher-free gate criterion in code and re-validating.
Both were surfaced to the user; scoring is held until that call is made, to preserve the gate
discipline that underwrites every ground-truth number in this project.
