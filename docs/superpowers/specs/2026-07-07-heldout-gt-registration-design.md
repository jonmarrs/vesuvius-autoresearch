# Held-Out Ground-Truth Registration (`20231210121321`) — Design

**Status:** Approved design (brainstorming). Sixth slice of the SOTA-rebase pivot, following the
first ground-truth registration (`2026-07-05-label-registration-design.md`).

## Context & motivation

The first ground-truth calibration (segment `20230702185753`) established the clean facts — the
canon teacher scores ROC-AUC 0.703 / AP 0.257 / F1 0.437 vs human labels, the legacy detector is
chance — but the *students'* rows carried a train-region confound: that region was in all three
students' training sets, so their strong numbers were fit-quality, not generalization. This slice
removes that confound with a **held-out** ground-truth region.

## Feasibility (verified in the bucket + on disk)

Requirements to register a segment: a human hand label (old flattening), an `original.obj`
(vertex texture coords = 2023 label pixels), and a canon teacher tif (for the enrichment gate +
the teacher row). Inventory of Scroll-1 (PHercParis4) hand-labeled segments:

| segment | hand label | original.obj | canon teacher | arm status |
| --- | --- | --- | --- | --- |
| 20230702185753 | ✓ | ✓ | ✓ | TRAIN (all) — done in slice 5 |
| 20231005123336 | ✓ | ✓ | ✓ | TRAIN (all) |
| **20231210121321** | **✓** | **✓** | **✓** | **held-out (arm-A validated; B/C untouched)** |
| 20230826170124 | ✓ | ✗ | ✗ | (no bridge inputs) |
| 20230903193206 | ✓ | ✗ | ✗ | (no bridge inputs) |
| 20231221180251 | ✗ | ✓ | ✓ | (no hand label) |

So `20231210121321` is the **only** segment with all three inputs that no arm trained on. It was
arm A's best-epoch *selection* segment (agreement-with-teacher), so:
- **arms B and C**: fully clean held-out (they selected on PHerc 1667) — carry the held-out claim.
- **arm A**: mildly selection-optimistic (selected on this segment's teacher, not trained) —
  disclosed as such.
- **teacher, legacy**: clean (as slice 5).

## Target & scope

One segment `20231210121321`, region `(y0,x0)=(4000,2500)` size 4096 at level 2 — the region arm
A validated on and where the SOTA fragment already exists on disk
(`local_data/sota_distill/20231210121321_y4000_x2500`). No training.

## Method (identical validated pipeline, new target)

Reuse the merged registration pipeline verbatim, pointed at the new segment:
1. **probe** — fetch `20231210121321`'s `original.obj` + `on-<oldscan>` tifxyz; confirm formats.
2. **warp_obj** — region 3D → nearest `original.obj` vertex → its vt (2023 label px) → sample the
   hand label; vt orientation picked among 4 candidates by teacher-enrichment (disclosed).
3. **validate (gate)** — letterform overlay + teacher-enrichment + 3D residual; `score` refuses
   without the `VALIDATED` marker. Same "no scoring against a misaligned label" discipline.
4. **score** — teacher + arm A/B/C + legacy vs the **held-out** registered ground truth; report
   leads with F1 for the teacher comparison (teacher is binary — the slice-5 lesson), tags arm A
   as selection-caveated, tags arms B/C as clean held-out.

## Architecture & components

`register.py` unchanged. `register_run.py` is **parameterized** to run either target without
duplication:
- Replace the module-level `SEG`/`FRAG_ID`/`REGION_L2`/report-path/`OLD_ROOT` constants with a
  `TARGETS` dict keyed by a short name (`orig` → the slice-5 segment, `heldout` → `20231210121321`),
  each carrying `seg`, `region`, `frag_id`, `frag_root`, and the report/marker/stats paths.
- Every subcommand takes the target key as its first positional arg
  (`python -m repro.sota_data.register_run warp_obj heldout`), defaulting to `orig` for backward
  compatibility with the committed slice-5 invocations.
- The `20231210121321` fragment already exists under `local_data/sota_distill/` with `frag_id`
  `20231210121321_y4000_x2500` (Phase-2 naming via `frag_id`, not `xfrag_id`); the target config
  points `frag_root`/`frag_id` there so `_measure` and the teacher read the right files. If a
  needed layer/label is missing, a prep helper regenerates the fragment (loud guard).
- A small unit test covers the `TARGETS` config + arg dispatch (both keys resolve to distinct
  seg/region/paths; unknown key ⇒ `ValueError`); the geometry is already tested.

## Success criteria

1. A held-out registered label passing the alignment gate (or an honest documented negative).
2. If validated: the scoring table (teacher + 3 students + legacy) vs **held-out** ground truth,
   committed with the arm-A selection caveat and the binary-teacher caveat stated inline.
3. A stated read: do arms B/C hold up vs held-out human labels (distillation learned to read) or
   drop (overfit the teacher)? Either is decisive and honestly reported.

## Non-goals

- No training; one segment, one region.
- No cross-scroll domain-ceiling claim — that needs human 1667 labels, which are **not released**
  (verified: 1667 ships only the canon prediction). This slice is same-scroll held-out GT.
- No re-selection of arm A's epoch (the caveat is disclosed, not engineered away; arms B/C carry
  the clean claim).

## Global constraints

Isolation (`repro/sota_data/` + `tests/` + `reports/detector/` + git-ignored `local_data/`);
anonymous S3; no detector-code changes; slice-5 backward-compatible; loop paused only for GPU
inference in `score`; no AI-authorship markers.

## Follow-ups (out of scope)

- Cross-scroll domain-ceiling: blocked until human 1667 (or other non-training-scroll) labels are
  released; re-check the bucket periodically.
- Registered held-out labels as *fine-tuning* data (ground-truth training on SOTA surfaces).
- July filing refresh with the held-out GT row (deadline 2026-07-31).
