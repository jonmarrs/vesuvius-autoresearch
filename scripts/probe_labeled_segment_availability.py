#!/usr/bin/env python3
"""Which Scroll-1 segments can supply registered ground truth?

Motivation (2026-08-15): the GT fine-tune was left "void, needs retraining" after the
2026-08-07 misregistration correction. Retraining needs training GT that is (a) hand
labelled, (b) re-flattened in the open data, and (c) correctly placed. This probe measures
how many segments satisfy all three, because the answer turned out to be one -- and that
one is already spent as the held-out evaluation target.

Method: intersect three sources.
  * labels, from villa/ink-detection/train_scrolls/<seg>/<seg>_inklabels.png (local);
  * geometry, from s3://vesuvius-challenge-open-data/PHercParis4/segments/ (network);
  * placement, from this repo's committed *_validation.json gate blocks (local).

What this probe deliberately does NOT do:
  * it does not judge placement for segments it has no committed measurement for -- those
    report `null`, meaning unmeasured, never "fine";
  * it does not treat a network failure as an empty bucket. A probe that silently reports
    "0 segments present" would manufacture the very finding it exists to check, so an
    unreachable bucket is a hard error.

Interpretation: `exhausted: true` means fewer than two labelled segments have a measured
placement inside the gate, so no training/held-out split exists. This is point-in-time --
the open data changes, which is why this is a probe and not a constant.

Reading `exhausted` alone is not enough, and the probe says so in `status`. Placement is
read from committed measurements made in this repo, so a newly published segment arrives
unmeasured and cannot lift `exhausted` by itself -- upstream publication is necessary, not
sufficient. `status` separates the two states that matters: `exhausted_no_candidate` (no
labelled segment is even waiting to be measured) from `exhausted_pending_measurement` (one
is, and the next move is ours). `unmeasured` names them, and `present`/`absent` move the
moment upstream publishes, so a re-run after publication visibly changes state.

Usage:
    uv run python scripts/probe_labeled_segment_availability.py
    uv run python scripts/probe_labeled_segment_availability.py --offline
"""

import argparse
import datetime
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN_SCROLLS = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
REPORTS_DIR = REPO_ROOT / "reports" / "detector"
OUT_JSON = REPORTS_DIR / "labeled_segment_availability.json"
# When the exhaustion finding was established, for the report's historical record only. The
# JSON stamps the actual run date instead: a frozen stamp on freshly-listed bucket contents
# is the "measured once, never re-checked" failure this probe exists to prevent.
FINDING_DATE = "2026-08-15"
GATE_PX = 48.0

# A Scroll-1 segment id is a 14-digit scan timestamp. train_scrolls/ also holds
# PHercParis2Fr47 and PHercParis2Fr143, fragments of a different object kept for the
# GP-winner reproduction; counting them would inflate this survey from 6 to 8.
SEGMENT_ID = re.compile(r"^\d{14}$")

# Segments that clear the placement gate and are still unusable. Imported, never redefined:
# `gt_prep_fragment` gates training on the same list, and a second copy of a constant is the
# shape of the bug that started all of this. See the module for the reasoning.
sys.path.insert(0, str(REPO_ROOT))
from repro.sota_data.retirement import RETIRED_NON_SCORING  # noqa: E402


def labeled_segments(train_scrolls_root):
    """Scroll-1 segments carrying a 2023 hand ink label, sorted."""
    root = pathlib.Path(train_scrolls_root)
    return sorted(
        p.name
        for p in root.iterdir()
        if SEGMENT_ID.match(p.name) and (p / f"{p.name}_inklabels.png").is_file()
    )


def placements_on_disk(reports_dir):
    """Committed placement offsets, keyed by segment.

    Reads two shapes, because the measurements live in two shapes.

    ⚠ FIXED 2026-08-27. This used to read only `*_validation.json` gate blocks,
    and so reported `20231005123336` as "present but unmeasured (ours to
    measure)" -- an unblock path a reader would reasonably chase. It is measured,
    and has been since 2026-08-15: 57.5 px against a 48 px gate, recorded in
    `gt_finetune_prep.json` under `regions[].placement_offset_level2_px` and
    written up in `gt_training_data_exhaustion_2026-08-15.md`. A probe whose job
    is to say what is left to try must not invent work that is already done; that
    error points the same way as wishful thinking, which is why it is worth
    naming rather than quietly patching.

    Region ids carry a `_y####_x####` suffix, so the segment is the leading field.
    Where a segment has several regions the WORST (largest) offset is kept: a
    segment is only usable if its regions are usable, and taking the best would
    let one good region hide a bad one.
    """
    out = {}
    for path in sorted(pathlib.Path(reports_dir).glob("*_validation.json")):
        try:
            d = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        seg = d.get("segment")
        offset = (
            d.get("registration", {}).get("gate", {}).get("placement_offset_level2_px")
        )
        if seg and offset is not None:
            out[seg] = float(offset)

    prep = pathlib.Path(reports_dir) / "gt_finetune_prep.json"
    if prep.exists():
        try:
            d = json.loads(prep.read_text())
        except json.JSONDecodeError:
            d = {}
        for region in d.get("regions", []):
            frag = region.get("frag_id") or ""
            offset = region.get("placement_offset_level2_px")
            if not frag or offset is None:
                continue
            seg = frag.split("_y")[0]
            out[seg] = max(out.get(seg, float("-inf")), float(offset))
    return out


def classify(
    labeled,
    bucket_segments,
    placements,
    retired=(),
    gate_px=GATE_PX,
    surveyed=None,
    mode="live",
):
    """Partition labelled segments by data availability and measured placement."""
    labeled, bucket = sorted(set(labeled)), set(bucket_segments)
    retired = set(retired)
    present = sorted(s for s in labeled if s in bucket)
    era_2023 = sorted(s for s in bucket if s.startswith("2023"))
    in_gate = sorted(
        s for s in present if placements.get(s) is not None and placements[s] <= gate_px
    )
    # Clearing the gate is necessary, not sufficient: a retired segment is excluded even
    # though it passes. Keeping the two sets separate means the JSON shows the difference
    # rather than hiding an exclusion inside a single number.
    usable = sorted(s for s in in_gate if s not in retired)
    # A segment upstream publishes tomorrow arrives here with no committed placement, so it
    # can never lift `exhausted` on its own -- publication is necessary, not sufficient, and
    # the remaining step is ours. Naming those segments keeps `exhausted: true` from reading
    # as "nothing changed upstream" when something did.
    unmeasured = sorted(
        s for s in present if s not in retired and placements.get(s) is None
    )
    exhausted = len(usable) < 2
    if not exhausted:
        status = "not_exhausted"
    elif unmeasured:
        status = "exhausted_pending_measurement"
    else:
        status = "exhausted_no_candidate"
    return {
        "surveyed": surveyed or datetime.date.today().isoformat(),
        "survey_mode": mode,
        "gate_px": gate_px,
        "labeled": labeled,
        "present": present,
        "absent": sorted(s for s in labeled if s not in bucket),
        "era_2023": era_2023,
        "unlabeled_2023": sorted(s for s in era_2023 if s not in set(labeled)),
        "in_gate": in_gate,
        "retired": sorted(retired),
        "measured_passing": usable,
        "unmeasured": unmeasured,
        # One usable segment is required as the held-out eval target, so a training split
        # needs at least two. Fewer means the experiment has no training set at all.
        "exhausted": exhausted,
        "status": status,
    }


def bucket_segments(fs):
    """Segment names under PHercParis4/segments. Raises if the bucket is unreachable."""
    sys.path.insert(0, str(REPO_ROOT))
    from repro.sota_data.distill_run import BUCKET, SCROLLS

    prefix = f"{BUCKET}/{SCROLLS['scroll1']}/segments"
    return sorted(x.rstrip("/").split("/")[-1] for x in fs.ls(prefix, detail=False))


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument(
        "--offline",
        action="store_true",
        help="skip the bucket query and reuse the previous run's segment list",
    )
    args = ap.parse_args()

    labeled = labeled_segments(TRAIN_SCROLLS)
    placements = placements_on_disk(REPORTS_DIR)

    if args.offline:
        if not OUT_JSON.exists():
            raise SystemExit(f"--offline needs a previous run at {OUT_JSON}")
        previous = json.loads(OUT_JSON.read_text())
        bucket = previous["era_2023"]
        mode = "offline"
    else:
        import s3fs

        bucket = bucket_segments(s3fs.S3FileSystem(anon=True))
        mode = "live"

    out = classify(labeled, bucket, placements, retired=RETIRED_NON_SCORING, mode=mode)
    if args.offline:
        # An offline run stamps today but its bucket half is as old as whatever it reused.
        # Without this the two are indistinguishable, and a stale availability claim would
        # wear a fresh date -- the exact failure this probe is here to prevent.
        out["bucket_listed"] = previous.get("bucket_listed", previous.get("surveyed"))
    else:
        out["bucket_listed"] = out["surveyed"]
    OUT_JSON.write_text(json.dumps(out, indent=2) + "\n")

    print(
        f"survey {out['surveyed']} ({out['survey_mode']}, bucket listing "
        f"{out['bucket_listed']})  gate {out['gate_px']:.0f} px"
    )
    print(f"{'segment':<20} {'label':<6} {'in data':<8} placement")
    for seg in out["labeled"]:
        p = placements.get(seg)
        print(
            f"{seg:<20} {'yes':<6} {'yes' if seg in out['present'] else 'NO':<8} "
            f"{'unmeasured' if p is None else f'{p:.1f} px'}"
        )
    print(
        f"\nlabelled: {len(out['labeled'])}  present: {len(out['present'])}  "
        f"absent: {len(out['absent'])}"
    )
    print(f"re-flattened 2023-era without a label: {len(out['unlabeled_2023'])}")
    print(f"inside the gate: {out['in_gate']}")
    print(f"retired despite passing: {out['retired']}")
    print(f"present but unmeasured (ours to measure): {out['unmeasured']}")
    print(f"usable: {out['measured_passing']}")
    print(f"EXHAUSTED: {out['exhausted']}  (needs >= 2 for a train/held-out split)")
    print(f"status: {out['status']}")
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
