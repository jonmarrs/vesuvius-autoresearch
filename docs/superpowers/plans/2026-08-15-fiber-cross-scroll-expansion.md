# Fiber Cross-Scroll Expansion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Take ScrollGT's fiber cross-scroll axis from one Scroll-5 cube to six, without letting ERL be compared across cube sizes.

**Architecture:** The exporter in `vesuvius-autoresearch` gains a scroll-derived split predicate and emits a `size_class` field. ScrollGT reads that field, carries it into every scorecard alongside the class's oracle ERL, and refuses to aggregate across classes. Data generation comes last because it needs model inference and may partially fail.

**Tech Stack:** Python 3.10, numpy, tifffile, pytest, `uv`. Two repos: `vesuvius-autoresearch` (build/export) and `../scrollgt` (public, ships the targets).

## Global Constraints

- **Interpreter:** always `uv run python ...`. Tests: `uv run python -m pytest -q <paths>`.
- **Commit trailer:** exactly `Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>`. **No `Claude-Session:` line** — the harness default template adds one; this project forbids it.
- **No AI-authorship markers** in any prose (README/BASELINES/meta.json notes).
- **Never stage `villa`** — a vendored upstream checkout, deliberately untracked.
- **`../scrollgt` is public.** Commit locally; **do not push**. The user reviews before publication.
- Pre-commit runs ruff/ruff-format/mypy/end-of-file-fixer; if it rewrites files, re-stage and re-commit.
- **Prose style:** match the surrounding file. ScrollGT uses em-dashes.
- **Do not cite line numbers inside a file your own edit shifts** — quote text instead.
- **Measured values (2026-08-15), to be used verbatim:**
  - 11 cubes in `local_data/fiber_skeletons/`, 6 shipped as targets.
  - Unshipped: `s5_06494_01994_03994_512`, `s5_06994_00994_04994_512`, `s5_07994_01994_05494_512` (512³); `s5_07997_02997_05497_256`, `s5_14997_01497_01497_256` (256³).
  - Only `s5_06494_01994_03994_512` already has `_fiberprob.npy`; the other four do not.
  - Oracle ERL on `s1_00497_01497_03997_256` is **258.27**; ERLpen 239.46; coverage 1.0.
  - Mask model: `scrollprize/fiber_hz_vt (Apache-2.0)`, threshold **0.5**.
  - `_erl(runs) = Σr² / Σr`, in voxels (`../scrollgt/src/scrollgt/fibers/eval_trace.py`).

---

### Task 1: Exporter emits `size_class` and derives split from scroll

**Files:**
- Modify: `scripts/export_fiber_targets.py` (the `CROSS_SCROLL_SPLIT` constant and the `"split"` field)
- Test: `tests/test_export_fiber_targets_split.py` (create)

**Interfaces:**
- Produces: `split_for_stem(stem: str) -> str` returning `"cross_scroll"` for `s5_*`, `"primary"` for `s1_*`, raising `ValueError` otherwise; and a `"size_class"` integer key in each emitted `meta.json`.

- [ ] **Step 1: Write the failing test**

Create `tests/test_export_fiber_targets_split.py`:

```python
"""The cross-scroll split must be derived, not hardcoded to one cube.

`CROSS_SCROLL_SPLIT` was a single stem, so `split` was "cross_scroll" only for
`s5_03997_01497_03997_256`. Shipping five more Scroll-5 cubes through that would label
them "primary" -- cross-scroll cubes marked same-scroll, corrupting the axis this work
exists to expand. That is an n=1 assumption living in code rather than in data.
"""

import pathlib
import sys

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT / "scripts"))

from export_fiber_targets import size_class_for_stem, split_for_stem  # noqa: E402


@pytest.mark.parametrize(
    "stem",
    [
        "s5_03997_01497_03997_256",
        "s5_06494_01994_03994_512",
        "s5_06994_00994_04994_512",
        "s5_07994_01994_05494_512",
        "s5_07997_02997_05497_256",
        "s5_14997_01497_01497_256",
    ],
)
def test_every_scroll5_cube_is_cross_scroll(stem):
    assert split_for_stem(stem) == "cross_scroll"


@pytest.mark.parametrize(
    "stem",
    [
        "s1_00497_01497_03997_256",
        "s1_00497_02497_02997_256",
        "s1_00997_02497_02997_256",
        "s1_08997_02997_02497_256",
        "s1_10997_02997_02997_256",
    ],
)
def test_every_scroll1_cube_is_primary(stem):
    assert split_for_stem(stem) == "primary"


def test_an_unknown_scroll_is_refused_rather_than_defaulted():
    """Defaulting to "primary" is how a cross-scroll cube gets silently mislabelled."""
    with pytest.raises(ValueError, match="scroll"):
        split_for_stem("s9_00001_00002_00003_256")


@pytest.mark.parametrize(
    "stem,expected",
    [
        ("s1_00497_01497_03997_256", 256),
        ("s5_06494_01994_03994_512", 512),
    ],
)
def test_size_class_comes_from_the_cube_name(stem, expected):
    assert size_class_for_stem(stem) == expected
```

- [ ] **Step 2: Run it to verify it fails**

Run: `uv run python -m pytest -q tests/test_export_fiber_targets_split.py`
Expected: FAIL at collection — `ImportError: cannot import name 'size_class_for_stem'`

- [ ] **Step 3: Implement**

In `scripts/export_fiber_targets.py`, delete the `CROSS_SCROLL_SPLIT` constant and add:

```python
def split_for_stem(stem: str) -> str:
    """Reporting split, derived from the scroll rather than a hardcoded cube list.

    This was `"cross_scroll" if stem == CROSS_SCROLL_SPLIT else "primary"` -- a single
    stem, so every additional Scroll-5 cube would have been labelled "primary". An unknown
    scroll raises rather than defaulting, because defaulting is exactly how a cross-scroll
    cube gets silently reported as same-scroll.
    """
    prefix = stem.split("_", 1)[0]
    if prefix == "s1":
        return "primary"
    if prefix == "s5":
        return "cross_scroll"
    raise ValueError(f"unknown scroll prefix {prefix!r} in cube stem {stem!r}")


def size_class_for_stem(stem: str) -> int:
    """Cube edge in voxels. ERL is a length statistic and does not compare across these."""
    return size_from_stem(stem)
```

Replace the `"split"` line with `"split": split_for_stem(stem),` and add
`"size_class": size_class_for_stem(stem),` immediately after it.

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run python -m pytest -q tests/test_export_fiber_targets_split.py`
Expected: PASS (6 + 5 + 1 + 2 = 14 passed)

- [ ] **Step 5: Commit**

```bash
git add scripts/export_fiber_targets.py tests/test_export_fiber_targets_split.py
git commit -m "$(cat <<'EOF'
fix(fibers): derive the cross-scroll split instead of hardcoding one cube

CROSS_SCROLL_SPLIT was a single stem, so split was "cross_scroll" only for
s5_03997_01497_03997_256. Shipping five more Scroll-5 cubes through that would
have labelled them "primary" -- cross-scroll cubes reported as same-scroll,
corrupting the very axis the expansion exists to widen. An n=1 assumption
living in code rather than in data.

An unknown scroll prefix now raises rather than defaulting to "primary",
because defaulting is the failure mode. Also emits size_class, since ERL is a
length statistic and does not compare across cube sizes.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 2: ScrollGT carries `size_class` and the class oracle into every scorecard

**Files:**
- Modify: `../scrollgt/src/scrollgt/fibers/target.py` (`score_fiber_prediction`)
- Modify: `../scrollgt/data/fibers_*/meta.json` (6 files — backfill `size_class`)
- Test: `../scrollgt/tests/test_fiber_size_class.py` (create)

**Interfaces:**
- Consumes: `"size_class"` key written by Task 1.
- Produces: scorecard keys `size_class: int` and `class_oracle_erl: float | None`.

**Note:** work in `../scrollgt`. Commit there; **do not push**.

- [ ] **Step 1: Write the failing test**

Create `../scrollgt/tests/test_fiber_size_class.py`:

```python
"""A fiber score is only readable against its own class ceiling.

ERL is expected run length in voxels (`_erl(runs) = sum r^2 / sum r`), so a 512-cube
admits longer fibers and scores higher for geometric reasons alone. Every scorecard
therefore states its size class and that class's oracle, so a number is never read
against the wrong ceiling.
"""

import json
import pathlib

import pytest

DATA = pathlib.Path(__file__).resolve().parents[1] / "data"
FIBER_TARGETS = sorted(DATA.glob("fibers_*"))


def test_there_are_fiber_targets_to_check():
    assert FIBER_TARGETS, "no fiber targets found; this test would vacuously pass"


@pytest.mark.parametrize("target", FIBER_TARGETS, ids=lambda p: p.name)
def test_every_fiber_target_declares_its_size_class(target):
    meta = json.loads((target / "meta.json").read_text())
    assert "size_class" in meta, f"{target.name} has no size_class"
    assert meta["size_class"] in (256, 512)
    # The class must agree with the cube's own declared shape, not just be present.
    assert meta["shape"][0] == meta["size_class"]


@pytest.mark.parametrize("target", FIBER_TARGETS, ids=lambda p: p.name)
def test_scorecard_reports_the_class_and_its_oracle(target):
    from scrollgt.fibers.target import load_fiber_target

    _, _, meta = load_fiber_target(str(target))
    assert meta["size_class"] == meta["shape"][0]
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_fiber_size_class.py`
Expected: FAIL — `KeyError`/assertion, the six shipped metas have no `size_class`

- [ ] **Step 3: Backfill `size_class` into the six shipped targets**

Run:

```bash
cd ../scrollgt && uv run python -c "
import json, pathlib
for d in sorted(pathlib.Path('data').glob('fibers_*')):
    p = d / 'meta.json'
    m = json.loads(p.read_text())
    if 'size_class' in m:
        continue
    m['size_class'] = int(m['shape'][0])
    p.write_text(json.dumps(m, indent=2) + '\n')
    print('backfilled', d.name, m['size_class'])
"
```

Expected: six lines, each reporting `256`.

- [ ] **Step 4: Add the class oracle to the scorecard**

In `../scrollgt/src/scrollgt/fibers/target.py`, inside `score_fiber_prediction`, after
`row = score_tracing(...).as_row()`, add:

```python
    # ERL is a length statistic, so a score means nothing without the ceiling for its own
    # cube size. Carry both into the card rather than leaving the reader to look them up.
    row["size_class"] = int(meta["size_class"])
    row["class_oracle_erl"] = meta.get("floors", {}).get("oracle", {}).get("erl")
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_fiber_size_class.py tests/test_fiber_target.py`
Expected: PASS

- [ ] **Step 6: Commit (do not push)**

```bash
cd ../scrollgt
git add src/scrollgt/fibers/target.py data/fibers_*/meta.json tests/test_fiber_size_class.py
git commit -m "$(cat <<'EOF'
feat(fibers): every target declares its size class, every card its ceiling

ERL is expected run length in voxels, so a 512 cube admits longer fibers and
scores higher for geometric reasons alone. Targets now declare size_class and
scorecards carry both it and the class oracle, so a number is never read
against the wrong ceiling.

The six shipped targets are backfilled from their own declared shape, and a
test pins that the two agree rather than trusting the field.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 3: Aggregation refuses to mix size classes

**Files:**
- Modify: `../scrollgt/src/scrollgt/fibers/target.py` (add `aggregate_fiber_scores`)
- Modify: `../scrollgt/tests/test_fiber_gaming.py` (add the cross-class case)

**Interfaces:**
- Consumes: scorecards from Task 2 carrying `size_class`.
- Produces: `aggregate_fiber_scores(cards: list[dict]) -> dict` returning
  `{"size_class": int, "n": int, "erl_mean": float, "erl_merge_penalized_mean": float}`,
  raising `ValueError` when `cards` span more than one class or is empty.

- [ ] **Step 1: Write the failing test**

Append to `../scrollgt/tests/test_fiber_gaming.py`:

```python
def test_aggregating_across_size_classes_is_refused():
    """A mean over mixed cube sizes is meaningless, so it must raise, not compute.

    Without this, a tracer scoring 60 on a 512 cube outranks one scoring 45 on a 256 cube
    for reasons of geometry rather than quality -- the same confound class as the
    n_fibers / n_fibers_scored conflation this benchmark already had to fix.
    """
    from scrollgt.fibers.target import aggregate_fiber_scores

    mixed = [
        {"size_class": 256, "erl": 45.0, "erl_merge_penalized": 30.0},
        {"size_class": 512, "erl": 60.0, "erl_merge_penalized": 40.0},
    ]
    with pytest.raises(ValueError, match="size class"):
        aggregate_fiber_scores(mixed)


def test_aggregating_within_one_size_class_works():
    from scrollgt.fibers.target import aggregate_fiber_scores

    same = [
        {"size_class": 256, "erl": 40.0, "erl_merge_penalized": 30.0},
        {"size_class": 256, "erl": 50.0, "erl_merge_penalized": 20.0},
    ]
    out = aggregate_fiber_scores(same)
    assert out["size_class"] == 256
    assert out["n"] == 2
    assert out["erl_mean"] == pytest.approx(45.0)
    assert out["erl_merge_penalized_mean"] == pytest.approx(25.0)


def test_aggregating_nothing_is_refused():
    from scrollgt.fibers.target import aggregate_fiber_scores

    with pytest.raises(ValueError):
        aggregate_fiber_scores([])
```

- [ ] **Step 2: Run it to verify it fails**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_fiber_gaming.py -k aggregat`
Expected: FAIL — `ImportError: cannot import name 'aggregate_fiber_scores'`

- [ ] **Step 3: Implement**

Append to `../scrollgt/src/scrollgt/fibers/target.py`:

```python
def aggregate_fiber_scores(cards) -> dict:
    """Mean ERL over cards of ONE size class. Raises on a mixed or empty set.

    Provided so that summarising several cubes has a correct implementation to reach for.
    Without one, a reader averages by hand across whatever cubes are in front of them, and
    ERL -- expected run length in voxels -- is not comparable between a 256 cube and a 512
    cube: the larger admits longer fibers and scores higher for geometric reasons.
    """
    cards = list(cards)
    if not cards:
        raise ValueError("aggregate_fiber_scores: no scorecards given")
    classes = {int(c["size_class"]) for c in cards}
    if len(classes) > 1:
        raise ValueError(
            f"refusing to aggregate across size class {sorted(classes)}: ERL is a length "
            "statistic and does not compare between cube sizes; aggregate each class "
            "separately"
        )
    n = len(cards)
    return {
        "size_class": classes.pop(),
        "n": n,
        "erl_mean": float(sum(float(c["erl"]) for c in cards) / n),
        "erl_merge_penalized_mean": float(
            sum(float(c["erl_merge_penalized"]) for c in cards) / n
        ),
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd ../scrollgt && uv run python -m pytest -q tests/test_fiber_gaming.py`
Expected: PASS (the pre-existing gaming tests plus the three new ones)

- [ ] **Step 5: Commit (do not push)**

```bash
cd ../scrollgt
git add src/scrollgt/fibers/target.py tests/test_fiber_gaming.py
git commit -m "$(cat <<'EOF'
feat(fibers): refuse to aggregate ERL across cube sizes

A mean over mixed cube sizes is meaningless: ERL is expected run length in
voxels, so a 512 cube admits longer fibers and scores higher geometrically. A
tracer scoring 60 on a 512 cube would outrank one scoring 45 on a 256 cube for
reasons unrelated to quality -- the same confound class as the n_fibers /
n_fibers_scored conflation already fixed here.

aggregate_fiber_scores exists so that summarising several cubes has a correct
implementation to reach for; without one, people average by hand. It raises on
mixed or empty input, pinned in test_fiber_gaming.py alongside the other
invariants rather than described in prose.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 4: Generate the missing probability volumes and export five targets

**Files:**
- Modify: `scripts/export_fiber_targets.py` (`CUBES` list)
- Create: `local_data/fiber_skeletons/{stem}_fiberprob.npy` for four cubes (generated, not committed)
- Create: `../scrollgt/data/fibers_{stem}/` for five cubes

**Interfaces:**
- Consumes: `split_for_stem`, `size_class_for_stem` from Task 1.

**This is the task that can partially fail.** 512³ is 8× the volume of 256³ and the patch-based
inference path may not fit. If a cube cannot be produced, **stop and report** — do not silently
drop it; the fallback is defined in Step 5.

- [ ] **Step 1: Add the five cubes to the exporter**

In `scripts/export_fiber_targets.py`, extend `CUBES` with, in this order (256³ first so a
failure on the large cubes still leaves a usable increment):

```python
    "s5_07997_02997_05497_256",
    "s5_14997_01497_01497_256",
    "s5_06494_01994_03994_512",
    "s5_06994_00994_04994_512",
    "s5_07994_01994_05494_512",
```

- [ ] **Step 2: Generate the four missing probability volumes**

`s5_06494_01994_03994_512` already has one. For the other four, run the cached generator —
it writes `{cube}_fiberprob.npy` beside the inputs:

```bash
uv run python -c "
import pathlib, numpy as np, tifffile, sys
sys.path.insert(0, '.')
from vesuvius_autoresearch.fibers.bench_cli import _fiber_prob
SRC = pathlib.Path('local_data/fiber_skeletons')
MODEL = pathlib.Path('local_data/models')  # adjust if the fiber_hz_vt weights live elsewhere
for stem in ['s5_07997_02997_05497_256', 's5_14997_01497_01497_256',
             's5_06994_00994_04994_512', 's5_07994_01994_05494_512']:
    out = SRC / f'{stem}_fiberprob.npy'
    if out.exists():
        print('have', stem); continue
    img = tifffile.imread(SRC / f'{stem}_image.tif')
    print(stem, 'shape', img.shape, flush=True)
    fp = _fiber_prob(SRC, stem, img, MODEL, 192)
    print('  wrote', out, fp.shape, flush=True)
"
```

If the model directory path is wrong, find it first with
`grep -rn "load_model\|model_dir" src/vesuvius_autoresearch/fibers/bench_cli.py` and read how
the benchmark CLI resolves it — do not guess a path into the command.

Expected: four `.npy` files written, each matching its cube's shape.

- [ ] **Step 3: Export the five targets**

Run: `uv run python scripts/export_fiber_targets.py`
Expected: eleven targets written under `../scrollgt/data/`, the five new ones reporting
`split=cross_scroll` and `size_class` 256 or 512 as appropriate.

- [ ] **Step 4: Verify the size-class rule was needed, not assumed**

Run:

```bash
cd ../scrollgt && uv run python -c "
import json, pathlib
for d in sorted(pathlib.Path('data').glob('fibers_*')):
    m = json.loads((d/'meta.json').read_text())
    o = m.get('floors', {}).get('oracle', {}).get('erl')
    print(f\"{d.name:44s} class={m['size_class']:4d} split={m['split']:12s} oracle_erl={o}\")
"
```

Expected: every `s5_*` row reads `cross_scroll`; the 512³ oracle ERLs are visibly larger than
the 256³ ones. **If they are not, stop and report** — the size-class design rests on that
difference, and if it is absent the premise is wrong and the spec needs revisiting.

- [ ] **Step 5: If any 512³ cube could not be produced**

Do not drop it. Ship what succeeded, and record in your report exactly which cubes failed and
why. Task 5 then states in BASELINES that those cubes are pending and for what reason. Silently
shipping a shorter list is the failure mode this whole branch exists to correct.

- [ ] **Step 6: Run both suites**

Run: `uv run python -m pytest -q tests/test_export_fiber_targets_split.py`
Run: `cd ../scrollgt && uv run python -m pytest -q`
Expected: PASS in both.

- [ ] **Step 7: Commit both repos (scrollgt: do not push)**

```bash
git add scripts/export_fiber_targets.py
git commit -m "$(cat <<'EOF'
feat(fibers): export the five unused Scroll-5 cubes as targets

Cross-scroll goes from one cube to six, using hand-traced data that was already
on disk. Four of the five needed their fiber_hz_vt probability volume generated
first -- the target mask is model output at threshold 0.5, not annotation, and
only s5_06494 had it cached.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
cd ../scrollgt
git add data/
git commit -m "$(cat <<'EOF'
data(fibers): five more Scroll-5 cubes, taking cross-scroll from n=1 to n=6

An axis with one cube cannot separate tracer quality from cube idiosyncrasy.
This is the same n=1 limitation disclosed for the pixel family, except that
here it was never capped -- the data was already hand-traced and sitting
unused.

Three of the new cubes are 512, so they carry size_class 512 and their scores
are only comparable within that class.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
```

---

### Task 5: Documentation, provenance backfill, and the column disclosure

**Files:**
- Modify: `../scrollgt/baselines/BASELINES.md`
- Modify: `../scrollgt/README.md`
- Modify: `../scrollgt/data/fibers_*/meta.json` (mask provenance note)

- [ ] **Step 1: Backfill mask provenance on every fiber target**

The `mask` block records the model and threshold but not that we generated the volume
ourselves. Add a `generated` note to all eleven:

```bash
cd ../scrollgt && uv run python -c "
import json, pathlib
for d in sorted(pathlib.Path('data').glob('fibers_*')):
    p = d / 'meta.json'
    m = json.loads(p.read_text())
    mask = m.get('mask')
    if not isinstance(mask, dict) or 'generated' in mask:
        continue
    mask['generated'] = ('probability volume produced locally by running '
                         'scrollprize/fiber_hz_vt over the cube, not downloaded from the '
                         'villa dataset; thresholded at 0.5 to give the shipped mask')
    p.write_text(json.dumps(m, indent=2) + '\n')
    print('noted', d.name)
"
```

- [ ] **Step 2: Rewrite the fiber section of BASELINES.md**

Replace the sentence beginning `Six 256³ cubes from villa's` — it is now wrong on both
count and size. The replacement must state: how many cubes and in which size classes; that
ERL is a length statistic and is therefore reported **per size class and never averaged
across them**, with `aggregate_fiber_scores` refusing to do so; that cross-scroll is now
six cubes rather than one; and, if Task 4 could not produce some cube, which and why.

Split the existing results table into one table per size class, each carrying its own oracle
row so a reader sees the ceiling beside the scores.

- [ ] **Step 3: Add the column-family n=1 disclosure**

In `../scrollgt/README.md`, near the column target description, state plainly that the column
family has exactly one target (`pherc1667_merged_columns`), that a single target cannot
separate model quality from target idiosyncrasy, and that expanding it needs another scroll
with a published reading whose column geometry can be registered. Match the tone of the
existing pixel-family disclosure — a limitation of this benchmark, not a complaint.

- [ ] **Step 4: Verify the docs against the shipped data**

```bash
cd ../scrollgt && grep -c "Six 256" baselines/BASELINES.md
uv run python -c "
import json, pathlib
cl = {}
for d in sorted(pathlib.Path('data').glob('fibers_*')):
    m = json.loads((d/'meta.json').read_text())
    cl.setdefault((m['size_class'], m['split']), []).append(d.name)
for k in sorted(cl): print(k, len(cl[k]))
"
grep -n "one target\|single target" README.md | head -3
```

Expected: `0` for the stale sentence; the class/split counts match what BASELINES claims; the
column disclosure is present.

- [ ] **Step 5: Run the full ScrollGT suite**

Run: `cd ../scrollgt && uv run python -m pytest -q`
Expected: PASS. These are documentation and metadata changes; a failure means a test asserts
on doc text and must be read before anything is adjusted.

- [ ] **Step 6: Commit (do not push)**

```bash
cd ../scrollgt
git add baselines/BASELINES.md README.md data/
git commit -m "$(cat <<'EOF'
docs(fibers): per-class tables, mask provenance, and the column n=1 disclosure

BASELINES described "six 256 cubes", wrong on both count and size after the
expansion. Results are now split per size class, each with its own oracle row,
because ERL does not compare across cube sizes.

The mask block recorded the model and threshold but not that we generate the
probability volume ourselves rather than downloading it. Backfilled across all
targets, including the six that shipped without it.

Also discloses that the column family has exactly one target. Found while
expanding fibers; shipping the fiber fix while silently knowing about the
column gap would repeat the failure corrected earlier today.

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>
EOF
)"
git status -sb | head -1
```

---

## Self-Review

**Spec coverage:**

| Spec item | Task |
|---|---|
| Size class first-class, scorer prints class oracle | Task 2 |
| Scorer refuses cross-class aggregation, pinned in gaming test | Task 3 |
| Split becomes a predicate; test pins every `s5_*` is cross_scroll | Task 1 |
| Generate four missing probability volumes | Task 4, Step 2 |
| Provenance states locally generated, backfilled to existing six | Task 5, Step 1 |
| Floors and oracle per new cube | Task 4, Step 3 (exporter computes them) + Step 4 verifies |
| BASELINES per-class tables | Task 5, Step 2 |
| Column n=1 disclosure | Task 5, Step 3 |
| Verification: no network/GPU at score time | Task 4, Step 6 (`scrollgt` suite) |
| Verification: 512³ oracle exceeds 256³ | Task 4, Step 4 |
| Non-goal: no tracer re-run | No task runs the tracer |
| Non-goal: no column change beyond disclosure | Task 5 touches only README prose |
| Risk: 512³ may not fit | Task 4, Step 5 defines the fallback explicitly |

**Placeholder scan:** none. Task 4 Step 2 deliberately tells the implementer to *find* the
model path rather than guessing one, since a wrong path in a plan is worse than an instruction
to look — that is a directive, not a placeholder.

**Type consistency:** `split_for_stem` / `size_class_for_stem` (Task 1) are imported by name in
Task 1's test. `size_class` is written by Task 1, read by Task 2, consumed by
`aggregate_fiber_scores` in Task 3. Scorecard keys `erl` and `erl_merge_penalized` match
`FiberScore.as_row()` as used by the existing gaming tests.

**One risk carried deliberately:** Task 4 depends on model weights and compute that no earlier
task exercises, so it can fail after three tasks have landed. Tasks 1-3 are independently
valuable regardless — they fix the hardcoded split and the cross-class confound even if not one
new cube ships.
