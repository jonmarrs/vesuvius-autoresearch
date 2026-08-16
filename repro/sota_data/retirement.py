"""Segments that clear the placement gate and are still unusable.

Clearing the gate is necessary, not sufficient. `20230702185753` passes the 48 level-2 px
threshold by 1.4 px globally, but its per-768px-tile placement has sd 26.8 (dy) / 33.0 (dx)
with individual tiles reaching ~102 px (~0.96 mm) -- roughly 1.9x the 512 um prize analysis
window. Within a single window a model can therefore be scored against ground truth from a
different part of the sheet, so the segment was retired non-scoring on 2026-08-14.

This lives in its own stdlib-only module for two reasons.

**One definition.** The concept first existed only in
`scripts/probe_labeled_segment_availability.py` while `gt_prep_fragment` -- the function that
actually decides what enters training -- knew nothing about it, so the retired segment came
back `passed: True` and `gt_finetune_prep.json` had to ship a "do not run this" warning in
place of a working regenerate command. A constant duplicated across two files is also the
exact shape of the bug that started all of this: a second hardcoded `LEVEL0_SHAPE` in
`gt_register.py` kept displacing training labels for a week after the first copy was fixed.

**No heavy imports.** The natural home would be `register_run.py`, next to
`MAX_PLACEMENT_OFFSET_L2PX` -- the threshold this qualifies. But that module pulls cv2,
tifffile, PIL and `distill_run` (zarr, s3fs), and the probe's whole value is that its
classification is importable and testable with no such dependency and no network. Hence a
leaf module both sides can import. `gt_register.py` already defers its
`MAX_PLACEMENT_OFFSET_L2PX` import into the function body for the same reason.

Retirement is deliberately **segment-level**, not region-level: the measured problem is
segment-wide (both regions of `20230702185753` are poorly placed, at 46.6 px and 53.3 px,
while `20231210121321` is 3-4x tighter), so retiring one region and keeping its sibling would
misrepresent it.

Do not confuse retirement with failing the gate. `20231005123336` is excluded because it
measures 57.5 px against a 48 px threshold -- an ordinary gate failure. Retirement is for
segments the gate lets through and we still will not use.

See `reports/detector/registration_offset_2026-08-07.md` and
`reports/detector/gt_training_data_exhaustion_2026-08-15.md`.
"""

RETIREMENT_DATE = "2026-08-14"

RETIRED_NON_SCORING = ("20230702185753",)

RETIREMENT_REASON = (
    f"segment retired non-scoring {RETIREMENT_DATE}: it clears the 48 level-2 px placement "
    "gate by 1.4 px globally, but per-tile local error reaches ~1.9x the 512 um analysis "
    "window, so a score can be against a different part of the sheet"
)


def is_retired(seg):
    """True if `seg` is retired non-scoring, regardless of what the placement gate says."""
    return seg in RETIRED_NON_SCORING
