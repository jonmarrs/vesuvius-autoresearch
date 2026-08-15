# Registered-GT Training Data Exhaustion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish the finding that registered-GT training data is exhausted on Scroll-1, make the survey behind it re-runnable, and correct the two places that currently imply otherwise.

**Architecture:** One new probe script separates a pure classification function (offline, unit-testable) from its network-dependent data collection, so the claim can be pinned by tests without depending on the S3 bucket. A report cites the probe. Two record-cleanup edits in this repo and two disclosure edits in the published ScrollGT repo remove the now-false implications.

**Tech Stack:** Python 3.10, `s3fs` (anonymous S3), `pytest`, `uv` for the project interpreter.

## Global Constraints

- **Interpreter:** always `uv run python ...`. A system `pytest` may lack GPU/CT deps. Tests: `uv run python -m pytest -q <paths>`.
- **Probe path discipline:** probes MUST anchor paths to `REPO_ROOT` derived from `__file__`. Never `os.path.abspath(".")`, never bare `"local_data/..."` or `"../scrollgt/..."` string literals. Enforced by `tests/test_probe_paths.py`.
- **Commit trailer:** every commit ends with `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`. No `Claude-Session:` line.
- **No AI-authorship markers** in any outward-facing text (ScrollGT README/BASELINES prose, PR bodies).
- **Prose style:** in `../scrollgt` match the surrounding file, which uses em-dashes. The no-dash house style applies only to Discord and prize-filing drafts, which this plan does not touch.
- **Branch:** all work in this repo continues on `spec/gt-training-data-exhaustion`. ScrollGT work is a separate repo at `../scrollgt` on its own `main`.
- **Date stamp:** the availability finding is point-in-time. Every artifact stating it must carry `2026-08-15`.
- **Measured values that must appear consistently** (source: `reports/detector/registration_offset_2026-08-07.md:282-285`, and the 2026-08-15 survey):
  - 6 Scroll-1 segments carry a 2023 hand ink label.
  - 3 of them are in the open data: `20230702185753`, `20231005123336`, `20231210121321`.
  - 3 are absent: `20230820203112`, `20230826170124`, `20230903193206`.
  - 81 segments under `PHercParis4/segments`, 11 of them 2023-era.
  - 8 re-flattened 2023-era segments carry no label: `20230929220926`, `20231007101619`, `20231012184424`, `20231016151002`, `20231022170901`, `20231031143852`, `20231106155351`, `20231221180251`.
  - Placement: `20230702185753` y4000_x2500 = 46.6 px, y7000_x4000 = 53.3 px, `20231005123336` y4000_x2500 = 55.1 px, y7000_x4000 drops at prep, `20231210121321` = 32.0 px. Gate = 48 px.
  - **Clearing the gate is necessary but not sufficient.** `20230702185753` clears it by 1.4 px and is still retired non-scoring (2026-08-14, worst tile ~1.9x the 512 um analysis window). Usable segments = exactly **1** (`20231210121321`), which is why the experiment is exhausted.
  - `villa/ink-detection/train_scrolls/` contains **8** labelled directories, of which **6** are Scroll-1 segments. `PHercParis2Fr47` and `PHercParis2Fr143` are fragments of a different object, retained for the GP-winner reproduction, and must never be counted in this survey or deleted from the checkout.

---

### Task 1: Availability probe with an offline-testable core

**Files:**
- Create: `scripts/probe_labeled_segment_availability.py`
- Create: `tests/test_probe_labeled_segment_availability.py`
- Modify: `tests/test_probe_paths.py:18` (add the new probe to `PROBES`)

**Interfaces:**
- Produces:
  - `REPO_ROOT: pathlib.Path`
  - `labeled_segments(train_scrolls_root: pathlib.Path) -> list[str]`
  - `placements_on_disk(reports_dir: pathlib.Path) -> dict[str, float]`
  - `RETIRED_NON_SCORING: tuple[str, ...]` — segments excluded even when they clear the gate.
  - `classify(labeled: Iterable[str], bucket_segments: Iterable[str], placements: Mapping[str, float], retired: Iterable[str] = (), gate_px: float = 48.0) -> dict`
    returning keys `surveyed`, `gate_px`, `labeled`, `present`, `absent`, `era_2023`, `unlabeled_2023`, `in_gate`, `retired`, `measured_passing`, `exhausted`.
    Note `in_gate` (cleared the placement gate) and `measured_passing` (cleared it *and* not retired) are deliberately separate, so the JSON shows the exclusion instead of hiding it in one number.
  - `bucket_segments(fs) -> list[str]` (network)
- Task 2 consumes the probe's JSON output at `reports/detector/labeled_segment_availability.json`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_probe_labeled_segment_availability.py`:

```python
"""The exhaustion claim must be re-checkable, not measured once.

The 2026-08-14 claim-vs-test audit found that this project's failures were never in
metric code -- they were properties measured once and never re-checked. The finding that
registered-GT training data is exhausted on Scroll-1 gates a published benchmark, so its
classification logic is pinned here and its live half is re-run by the probe.
"""

import json
import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from probe_labeled_segment_availability import (  # noqa: E402
    RETIRED_NON_SCORING,
    classify,
    labeled_segments,
    placements_on_disk,
)

# The 2026-08-15 survey, recorded so a regression is visible as a diff.
LABELED = [
    "20230702185753",
    "20230820203112",
    "20230826170124",
    "20230903193206",
    "20231005123336",
    "20231210121321",
]
PRESENT = ["20230702185753", "20231005123336", "20231210121321"]
ABSENT = ["20230820203112", "20230826170124", "20230903193206"]
UNLABELED_2023 = [
    "20230929220926",
    "20231007101619",
    "20231012184424",
    "20231016151002",
    "20231022170901",
    "20231031143852",
    "20231106155351",
    "20231221180251",
]
BUCKET_2023 = sorted(PRESENT + UNLABELED_2023)


def test_classify_partitions_labelled_segments_by_availability():
    out = classify(LABELED, BUCKET_2023, {}, gate_px=48.0)
    assert out["present"] == PRESENT
    assert out["absent"] == ABSENT
    assert out["unlabeled_2023"] == UNLABELED_2023


def test_clearing_the_gate_is_necessary_but_not_sufficient():
    """20230702185753 clears the gate by 1.4px and is still unusable.

    It was retired as non-scoring on 2026-08-14 because its worst tile reaches ~1.9x the
    512um analysis window. A probe that counted it would report exhausted=False and
    contradict the report it exists to support.
    """
    placements = {
        "20230702185753": 46.6,
        "20231005123336": 55.1,
        "20231210121321": 32.0,
    }
    out = classify(
        LABELED, BUCKET_2023, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["in_gate"] == ["20230702185753", "20231210121321"]
    assert out["measured_passing"] == ["20231210121321"]
    assert out["exhausted"] is True


def test_a_second_well_placed_segment_would_lift_exhaustion():
    """Guard against the claim silently outliving the condition that produced it."""
    bucket = BUCKET_2023 + ["20230820203112"]
    placements = {"20231210121321": 32.0, "20230820203112": 30.0}
    out = classify(
        LABELED, bucket, placements, retired=RETIRED_NON_SCORING, gate_px=48.0
    )
    assert out["measured_passing"] == ["20230820203112", "20231210121321"]
    assert out["exhausted"] is False


def test_fragments_of_other_objects_are_not_counted_as_scroll1_segments():
    """train_scrolls/ also holds PHercParis2Fr47 and PHercParis2Fr143.

    Those are fragments of a different object, retained for the GP-winner reproduction.
    Counting them would inflate the Scroll-1 survey from 6 to 8.
    """
    root = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
    if not root.is_dir():
        pytest.skip("villa/ink-detection/train_scrolls not present")
    got = labeled_segments(root)
    assert not [s for s in got if not s.isdigit()]
    assert "PHercParis2Fr47" not in got and "PHercParis2Fr143" not in got


def test_placements_are_read_from_committed_validation_json():
    got = placements_on_disk(REPO_ROOT / "reports" / "detector")
    assert got["20231210121321"] == pytest.approx(32.0, abs=0.1)
    assert got["20230702185753"] == pytest.approx(46.6, abs=0.1)


def test_labeled_segments_matches_the_recorded_survey():
    root = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
    if not root.is_dir():
        pytest.skip("villa/ink-detection/train_scrolls not present")
    assert labeled_segments(root) == LABELED


def test_probe_json_if_present_agrees_with_the_recorded_survey():
    out = REPO_ROOT / "reports" / "detector" / "labeled_segment_availability.json"
    if not out.exists():
        pytest.skip("probe has not been run yet")
    d = json.loads(out.read_text())
    assert d["absent"] == ABSENT
    assert d["surveyed"] == "2026-08-15"
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `uv run python -m pytest -q tests/test_probe_labeled_segment_availability.py`
Expected: FAIL at collection with `ModuleNotFoundError: No module named 'probe_labeled_segment_availability'`

- [ ] **Step 3: Write the probe**

Create `scripts/probe_labeled_segment_availability.py`:

```python
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

Usage:
    uv run python scripts/probe_labeled_segment_availability.py
    uv run python scripts/probe_labeled_segment_availability.py --offline
"""

import argparse
import json
import pathlib
import re
import sys

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
TRAIN_SCROLLS = REPO_ROOT / "villa" / "ink-detection" / "train_scrolls"
REPORTS_DIR = REPO_ROOT / "reports" / "detector"
OUT_JSON = REPORTS_DIR / "labeled_segment_availability.json"
SURVEY_DATE = "2026-08-15"
GATE_PX = 48.0

# A Scroll-1 segment id is a 14-digit scan timestamp. train_scrolls/ also holds
# PHercParis2Fr47 and PHercParis2Fr143, fragments of a different object kept for the
# GP-winner reproduction; counting them would inflate this survey from 6 to 8.
SEGMENT_ID = re.compile(r"^\d{14}$")

# Segments that clear the placement gate and are still unusable. 20230702185753 passes by
# 1.4 px globally while its worst 768px tile reaches ~1.9x the 512um analysis window, so a
# score there can land on a different part of the sheet; retired non-scoring 2026-08-14.
# Kept as data, not a special case in the logic, so the reason travels with the exclusion.
RETIRED_NON_SCORING = ("20230702185753",)


def labeled_segments(train_scrolls_root):
    """Scroll-1 segments carrying a 2023 hand ink label, sorted."""
    root = pathlib.Path(train_scrolls_root)
    return sorted(
        p.name
        for p in root.iterdir()
        if SEGMENT_ID.match(p.name) and (p / f"{p.name}_inklabels.png").is_file()
    )


def placements_on_disk(reports_dir):
    """Committed placement offsets, keyed by segment, from *_validation.json gate blocks."""
    out = {}
    for path in sorted(pathlib.Path(reports_dir).glob("*_validation.json")):
        try:
            d = json.loads(path.read_text())
        except json.JSONDecodeError:
            continue
        seg = d.get("segment")
        offset = d.get("registration", {}).get("gate", {}).get(
            "placement_offset_level2_px"
        )
        if seg and offset is not None:
            out[seg] = float(offset)
    return out


def classify(labeled, bucket_segments, placements, retired=(), gate_px=GATE_PX):
    """Partition labelled segments by data availability and measured placement."""
    labeled, bucket = sorted(set(labeled)), set(bucket_segments)
    retired = set(retired)
    present = sorted(s for s in labeled if s in bucket)
    era_2023 = sorted(s for s in bucket if s.startswith("2023"))
    in_gate = sorted(
        s
        for s in present
        if placements.get(s) is not None and placements[s] <= gate_px
    )
    # Clearing the gate is necessary, not sufficient: a retired segment is excluded even
    # though it passes. Keeping the two sets separate means the JSON shows the difference
    # rather than hiding an exclusion inside a single number.
    usable = sorted(s for s in in_gate if s not in retired)
    return {
        "surveyed": SURVEY_DATE,
        "gate_px": gate_px,
        "labeled": labeled,
        "present": present,
        "absent": sorted(s for s in labeled if s not in bucket),
        "era_2023": era_2023,
        "unlabeled_2023": sorted(s for s in era_2023 if s not in set(labeled)),
        "in_gate": in_gate,
        "retired": sorted(retired),
        "measured_passing": usable,
        # One usable segment is required as the held-out eval target, so a training split
        # needs at least two. Fewer means the experiment has no training set at all.
        "exhausted": len(usable) < 2,
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
        bucket = json.loads(OUT_JSON.read_text())["era_2023"]
    else:
        import s3fs

        bucket = bucket_segments(s3fs.S3FileSystem(anon=True))

    out = classify(labeled, bucket, placements, retired=RETIRED_NON_SCORING)
    OUT_JSON.write_text(json.dumps(out, indent=2) + "\n")

    print(f"survey {out['surveyed']}  gate {out['gate_px']:.0f} px")
    print(f"{'segment':<20} {'label':<6} {'in data':<8} placement")
    for seg in out["labeled"]:
        p = placements.get(seg)
        print(
            f"{seg:<20} {'yes':<6} {'yes' if seg in out['present'] else 'NO':<8} "
            f"{'unmeasured' if p is None else f'{p:.1f} px'}"
        )
    print(f"\nlabelled: {len(out['labeled'])}  present: {len(out['present'])}  "
          f"absent: {len(out['absent'])}")
    print(f"re-flattened 2023-era without a label: {len(out['unlabeled_2023'])}")
    print(f"inside the gate: {out['in_gate']}")
    print(f"retired despite passing: {out['retired']}")
    print(f"usable: {out['measured_passing']}")
    print(f"EXHAUSTED: {out['exhausted']}  (needs >= 2 for a train/held-out split)")
    print(f"\nwrote {OUT_JSON}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run python -m pytest -q tests/test_probe_labeled_segment_availability.py`
Expected: PASS (the probe-JSON test skips until Step 6)

- [ ] **Step 5: Register the probe with the path-discipline test**

In `tests/test_probe_paths.py:18`, change:

```python
PROBES = ["probe_placement_field.py", "probe_registration_offset.py"]
```

to:

```python
PROBES = [
    "probe_labeled_segment_availability.py",
    "probe_placement_field.py",
    "probe_registration_offset.py",
]
```

Run: `uv run python -m pytest -q tests/test_probe_paths.py`
Expected: PASS

- [ ] **Step 6: Run the probe against live data**

Run: `uv run python scripts/probe_labeled_segment_availability.py`
Expected: 6 labelled, 3 present, `absent` lists the three segments, `unlabeled_2023` has 8 entries, `in_gate` is `['20230702185753', '20231210121321']`, `retired` is `['20230702185753']`, `usable` is `['20231210121321']`, `EXHAUSTED: True`. Writes `reports/detector/labeled_segment_availability.json`.

If any count disagrees with Global Constraints, STOP and report — the finding has changed and the report in Task 2 must be rewritten, not adjusted.

- [ ] **Step 7: Re-run the full test file now that the JSON exists**

Run: `uv run python -m pytest -q tests/test_probe_labeled_segment_availability.py`
Expected: PASS, with no skips for `test_probe_json_if_present_agrees_with_the_recorded_survey`

- [ ] **Step 8: Commit**

```bash
git add scripts/probe_labeled_segment_availability.py \
        tests/test_probe_labeled_segment_availability.py \
        tests/test_probe_paths.py \
        reports/detector/labeled_segment_availability.json
git commit -m "$(cat <<'EOF'
probe: is there any registered-GT training data left on Scroll-1

Answers the question the 2026-08-07 correction left open. Retraining the GT
fine-tune needs labels that are hand-drawn, re-flattened in the open data, and
correctly placed; this intersects all three and finds exactly one segment,
which is already spent as the held-out evaluation target.

The classification is a pure function so the claim is pinned offline, and an
unreachable bucket is a hard error rather than an empty result -- a probe that
reported "0 present" on a network blip would manufacture its own finding.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: The report

**Files:**
- Create: `reports/detector/gt_training_data_exhaustion_2026-08-15.md`

**Interfaces:**
- Consumes: `reports/detector/labeled_segment_availability.json` from Task 1.
- Produces: a report path cited by Tasks 3 and 4.

- [ ] **Step 1: Write the report**

Create `reports/detector/gt_training_data_exhaustion_2026-08-15.md`. It must contain, in this order:

1. **Headline.** On Scroll-1 the intersection {2023 hand label} and {SOTA re-flattening} and {passes the 48 px placement gate} contains exactly one segment, and it is required as the held-out evaluation target. One segment cannot be both training set and held-out test.

2. **The availability table**, exactly as in the spec's "What was measured" section, all 8 rows.

3. **Both blockers, named separately.** Two segments fail on registration quality (cross-scan surface disagreement, closed as a floor on 2026-08-07 after two falsified fix attempts). Three fail on data availability (absent from the open data entirely: neither `ink-detection/` nor `surface-volumes/` resolves). State plainly that fixing registration would not unblock the experiment and neither would compute.

4. **Consequence 1: the GT fine-tune is unanswerable as posed.** Not "does not help" — that is the retracted 2026-07-11 claim and it was false. Not testable, for want of a training set. Add that the original premise is independently void: it cited arm C at ROC-AUC 0.558 as the bar to beat, and post-correction arm C reads that segment at ~0.746, so "unlock reading from chance" describes nothing real.

5. **Consequence 2: ScrollGT's pixel family is n=1 and unexpandable.** Note that n=1 is already disclosed at `README.md:126` but is qualified as "currently", which implies expandability the survey rules out.

6. **Two unblock paths**, stated as necessary but not sufficient: re-flatten one of the three absent labelled segments, or hand-label one of the eight re-flattened 2023-era segments. Measured base rate for a fresh segment passing the gate is 1 of 3.

7. **Limitations.** Point-in-time (cite the probe as the re-check mechanism, and the `2026-08-15` stamp). Placement verification is relative — `placement_peak` scores against the canon teacher crop, so it localises disagreement between two artifacts rather than establishing truth. State this as a general caveat on every placement figure, not as a caveat on any one segment.

   **Do not write that `20231005123336` has a chance-quality teacher.** That was true before 2026-08-07 and is now false: the enrichment collapse there was our own second hardcoded level-0 shape, and re-registered with the fix, teacher-enrichment is **4.88** with the orientation decisively determined (`../scrollgt/baselines/BASELINES.md:119-131`). Its 55.1 px placement is a properly measured failure. The same correction retires the 2026-07-11 orientation addendum's claim that half the fine-tune's training labels may have been geometric noise — the labels were fine, the registration was broken.

Every number must cite either `labeled_segment_availability.json` or `registration_offset_2026-08-07.md`. No number appears without one.

- [ ] **Step 2: Verify every cited number against its source**

Run:

```bash
uv run python -c "
import json,pathlib
d=json.loads(pathlib.Path('reports/detector/labeled_segment_availability.json').read_text())
print('labeled',len(d['labeled']),'present',len(d['present']),'absent',len(d['absent']))
print('unlabeled_2023',len(d['unlabeled_2023']),'exhausted',d['exhausted'])
"
grep -n "46.6\|53.3\|55.1\|32.0" reports/detector/registration_offset_2026-08-07.md | head
```

Expected: 6 / 3 / 3, 8, `True`; and all four placement figures present in the 08-07 report. Any mismatch means fix the report text, not the sources.

- [ ] **Step 3: Commit**

```bash
git add reports/detector/gt_training_data_exhaustion_2026-08-15.md
git commit -m "$(cat <<'EOF'
report: registered-GT training data is exhausted on Scroll-1

The GT fine-tune is not answerable as posed, and not for the reason the
2026-08-07 correction assumed. Two blockers bind independently: two segments
fail on registration quality, three more are absent from the open data
entirely. Neither compute nor a better registration would unblock it.

Replaces a retracted false negative ("GT fine-tuning worsens held-out
reading") with a true and checkable one ("not testable, and here is the
missing resource"). Ends on two concrete unblock paths rather than a dead end,
because both sides of the intersection were measured.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Record cleanup in vesuvius-autoresearch

**Files:**
- Modify: `reports/detector/gt_finetune_prep.json` (replace wholesale)
- Modify: `reports/detector/registration_offset_2026-08-07.md:401-403`
- Modify: `repro/sota_data/gt_finetune.py:73-79`
- Create: `tests/test_gt_finetune_prep_superseded.py`

**Interfaces:**
- Consumes: the report path from Task 2.

- [ ] **Step 1: Write the failing test**

Create `tests/test_gt_finetune_prep_superseded.py`:

```python
"""The committed prep artifact must not keep telling the retracted story.

gt_finetune_prep.json predates the 2026-08-14 placement gate. It recorded all four
training regions as passing, which is how the GT fine-tune came to train on displaced
labels. Three of those four fail the gate, so the file must not assert any pass.
"""

import json
import pathlib

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
PREP = REPO_ROOT / "reports" / "detector" / "gt_finetune_prep.json"


def test_prep_artifact_claims_no_passing_region():
    d = json.loads(PREP.read_text())
    assert d.get("kept") == [], "kept regions imply a usable training split; there is none"
    for r in d.get("regions", []):
        assert r.get("passed") is not True, f"{r.get('frag_id')} still recorded as passing"


def test_prep_artifact_says_why_and_points_at_the_report():
    d = json.loads(PREP.read_text())
    assert "superseded" in d
    assert "gt_training_data_exhaustion_2026-08-15" in json.dumps(d["superseded"])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run python -m pytest -q tests/test_gt_finetune_prep_superseded.py`
Expected: FAIL — `kept` currently lists four regions and each records `"passed": true`

- [ ] **Step 3: Replace the stale artifact**

Overwrite `reports/detector/gt_finetune_prep.json` with:

```json
{
  "superseded": {
    "date": "2026-08-15",
    "reason": "This file was written before the 2026-08-14 placement gate existed. It recorded all four regions as passing, which is exactly how the GT fine-tune came to train on displaced labels. Three of the four fail the gate and the fourth passes by 1.4 px on a gate whose own per-tile scatter is +/- 27 to 33 px. Its former numbers are void and have been removed rather than left readable.",
    "report": "reports/detector/gt_training_data_exhaustion_2026-08-15.md",
    "regenerate": "uv run python -m repro.sota_data.gt_finetune prep"
  },
  "regions": [],
  "kept": []
}
```

- [ ] **Step 4: Run the test to verify it passes**

Run: `uv run python -m pytest -q tests/test_gt_finetune_prep_superseded.py`
Expected: PASS

- [ ] **Step 5: Amend the 08-07 report's status line**

In `reports/detector/registration_offset_2026-08-07.md:401-403`, replace:

```markdown
- **Void, needs retraining:** `arm C + GT fine-tune`, which was fine-tuned on the displaced
  label. Removed from the leaderboard rather than re-scored — and it should not be
  retrained until the residual is fixed, or it will just bake in the smaller error.
```

with:

```markdown
- **Void, NOT retrainable:** `arm C + GT fine-tune`, which was fine-tuned on the displaced
  label. Removed from the leaderboard rather than re-scored. This entry previously made
  retraining conditional on fixing the residual; that condition was moot, because the
  residual is closed above as an irreducible floor. Overriding it on 2026-08-15 exposed the
  real blocker: there is no training set. Exactly one Scroll-1 segment is labelled,
  re-flattened and correctly placed, and it is spent as the held-out evaluation target. See
  [gt_training_data_exhaustion_2026-08-15.md](gt_training_data_exhaustion_2026-08-15.md).
```

- [ ] **Step 6: Amend the guard message**

In `repro/sota_data/gt_finetune.py:73-79`, replace the `raise ValueError(...)` body:

```python
            f"{PREP_JSON} kept only {len(kept)} region(s): {kept}. Fine-tuning needs at "
            "least 2 so validation can be disjoint from training. As of 2026-08-14 three "
            "of the four configured regions fail the placement gate, so this experiment "
            "needs new training GT rather than a smaller split -- see "
```

with:

```python
            f"{PREP_JSON} kept only {len(kept)} region(s): {kept}. Fine-tuning needs at "
            "least 2 so validation can be disjoint from training. Three of the four "
            "configured regions fail the 2026-08-14 placement gate, and as of 2026-08-15 "
            "no replacement exists: exactly one Scroll-1 segment is labelled, re-flattened "
            "and correctly placed, and it is spent as the held-out evaluation target. This "
            "is not fixable with a smaller split or more compute -- see "
```

Then update the trailing path on the following line to reference
`reports/detector/gt_training_data_exhaustion_2026-08-15.md` instead of
`reports/detector/registration_offset_2026-08-07.md`.

- [ ] **Step 7: Verify nothing else regressed**

Run: `uv run python -m pytest -q tests/test_gt_finetune_prep_superseded.py tests/test_probe_paths.py tests/test_probe_labeled_segment_availability.py`
Expected: PASS

Run: `uv run python -c "import ast,pathlib; ast.parse(pathlib.Path('repro/sota_data/gt_finetune.py').read_text()); print('parses')"`
Expected: `parses`

- [ ] **Step 8: Commit**

```bash
git add reports/detector/gt_finetune_prep.json \
        reports/detector/registration_offset_2026-08-07.md \
        repro/sota_data/gt_finetune.py \
        tests/test_gt_finetune_prep_superseded.py
git commit -m "$(cat <<'EOF'
correct: the GT fine-tune is not retrainable, and the artifacts said otherwise

Three records still implied the experiment was waiting on a fix. The prep JSON
predated the placement gate and recorded all four regions as passing, which is
the state that produced the retracted result; its numbers are removed rather
than left readable. The 08-07 status line made retraining conditional on
fixing the residual, a condition that was moot once the residual was closed as
a floor. The guard message said the experiment "needs new training GT" without
saying none exists.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: ScrollGT disclosure

**Files:**
- Modify: `../scrollgt/README.md:146-152`
- Modify: `../scrollgt/baselines/BASELINES.md:119-131`

**Interfaces:**
- Consumes: the report from Task 2 (cited by URL, since ScrollGT is a separate public repo).

**Note:** separate repo, separate remote, its own `main`. Do not push. Leave the commit local for review.

- [ ] **Step 1: Confirm the starting state**

Run: `sed -n '146,152p' ../scrollgt/README.md`
Expected: the paragraph ending `so 20231210121321 is currently the only pixel target we would stand behind.`

- [ ] **Step 2: Replace the "currently" paragraph**

In `../scrollgt/README.md`, replace:

```markdown
**The problem is segment-wide, not region-wide.** Both regions of `20230702185753` are
poorly placed (46.6 px and 53.3 px, local error to ~1 mm) while `20231210121321` is 3–4×
tighter. This is cross-scan disagreement between the 2023 and 2026 segmentations of that
sheet, not a correctable offset — so `20231210121321` is currently the only pixel target we
would stand behind.
```

with:

```markdown
**The problem is segment-wide, not region-wide.** Both regions of `20230702185753` are
poorly placed (46.6 px and 53.3 px, local error to ~1 mm) while `20231210121321` is 3–4×
tighter. This is cross-scan disagreement between the 2023 and 2026 segmentations of that
sheet, not a correctable offset — so `20231210121321` is the only pixel target we would
stand behind.

**And the pool is exhausted, not merely unprocessed.** Six Scroll-1 segments carry a 2023
hand ink label. Three of them (`20230820203112`, `20230826170124`, `20230903193206`) are
absent from the open data entirely — neither `ink-detection/` nor `surface-volumes/`
resolves — so there is no geometry to register a label onto. Of the three that remain, two
are the poorly placed ones above. Measured 2026-08-15; the open data changes, so this is a
[re-runnable probe][probe] rather than a claim.

**What this costs you as a user.** A single-target pixel family cannot separate model
quality from segment idiosyncrasy: a score here is a score on one sheet. Read the pixel
leaderboard accordingly, and prefer the column and fiber families when you need more than
one point of comparison. Expanding it needs new upstream data — either a re-flattening of
one of the three absent labelled segments, or a hand label on one of the eight 2023-era
segments that are re-flattened but unlabelled. Neither is sufficient on its own: a fresh
segment still has to pass the placement gate, and the measured base rate for that is 1 of 3.

[probe]: https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/gt_training_data_exhaustion_2026-08-15.md
```

- [ ] **Step 3: Add the same fact where the withheld region is discussed**

Run `sed -n '119,131p' ../scrollgt/baselines/BASELINES.md` to see the current text, then append this paragraph at the end of that withheld-region discussion:

```markdown
**This region cannot be replaced.** Withholding it leaves the pixel family at one scoreable
target, and as of 2026-08-15 there is no fourth candidate: of the six Scroll-1 segments
carrying a 2023 hand label, three are absent from the open data and two are the poorly
placed `20230702185753` regions. The family is capped by data availability, not by
processing effort. See the
[availability survey](https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/detector/gt_training_data_exhaustion_2026-08-15.md).
```

- [ ] **Step 4: Verify the claims in the edits match the sources**

Run:

```bash
grep -c "20230820203112\|20230826170124\|20230903193206" ../scrollgt/README.md
grep -n "1 of 3\|exhausted\|absent from the open data" ../scrollgt/README.md
```

Expected: the three absent segment IDs appear in the README, and the base-rate and exhaustion language is present.

Confirm no AI-authorship marker was introduced:

```bash
grep -rn "Generated with\|Claude Code\|🤖" ../scrollgt/README.md ../scrollgt/baselines/BASELINES.md
```

Expected: no output.

- [ ] **Step 5: Run ScrollGT's test suite**

Run: `cd ../scrollgt && uv run python -m pytest -q`
Expected: PASS, same count as before the edits. These are documentation-only changes; a failure means a test asserts on doc text and needs reading before anything is adjusted.

- [ ] **Step 6: Commit locally, do not push**

```bash
cd ../scrollgt
git add README.md baselines/BASELINES.md
git commit -m "$(cat <<'EOF'
docs: the pixel family is capped by data availability, not effort

The README already disclosed one scoreable pixel target but called it
"currently" the only one we would stand behind, which implies the family grows
with more processing. It does not. Six Scroll-1 segments carry a 2023 hand
label; three are absent from the open data entirely and two are the poorly
placed 20230702185753 regions, leaving one.

States what that costs a user -- a single-target family cannot separate model
quality from segment idiosyncrasy -- and what would actually expand it, with
the caveat that a fresh segment still has to pass the placement gate.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git log --oneline -1
```

- [ ] **Step 7: Report the ScrollGT commit for review**

Print the diff for the user and confirm it is unpushed:

```bash
cd ../scrollgt && git show --stat HEAD && git status -sb | head -2
```

Expected: `## main...origin/main [ahead 1]`

---

## Self-Review

**Spec coverage:**

| Spec deliverable | Task |
|---|---|
| D1 committed survey probe | Task 1 |
| D2 report | Task 2 |
| D3 ScrollGT disclosure (README + BASELINES) | Task 4 |
| D4 regenerate stale prep JSON | Task 3, Steps 1-4 |
| D4 amend 08-07 retraining precondition | Task 3, Step 5 |
| D4 amend `gt_finetune.py` guard message | Task 3, Step 6 |
| Verification: probe reproduces the table | Task 1, Step 6 |
| Verification: test pins claim, skips offline | Task 1, Steps 1-4 |
| Verification: ScrollGT suite passes | Task 4, Step 5 |
| Verification: no uncited numbers | Task 2, Step 2 |
| Non-goal: no retraining | No task runs training |
| Non-goal: fragment variant out of scope | No task touches `PHercParis2Fr*` |
| Non-goal: no outward announcement | Task 4 Step 6 commits locally, does not push |

**Placeholder scan:** no TBD/TODO. Every code step carries literal content. Task 2's report is specified as seven required elements with sources rather than pasted prose, because it is a prose deliverable whose numbers must be re-verified at write time (Step 2) rather than copied from a plan that could drift.

**Type consistency:** `classify` returns the same eleven keys used by the tests, the probe's `main`, and Task 2's verification snippet, including the `in_gate`/`measured_passing` pair and `RETIRED_NON_SCORING`. `labeled_segments` and `placements_on_disk` take a path and return `list[str]` / `dict[str, float]` consistently in the probe and the test import. `REPO_ROOT` is derived from `__file__` in both files, satisfying `test_probe_paths.py`.

**One risk carried deliberately:** Task 1 Step 6 can invalidate Task 2 before it is written, if the bucket has changed since 2026-08-15. The step says STOP and report rather than adjust, because a changed survey means a different finding, not a different sentence.
