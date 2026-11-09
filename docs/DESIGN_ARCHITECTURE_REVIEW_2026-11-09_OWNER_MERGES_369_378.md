# Design and architecture review — the owner's #369, #371, #372 and #378

Date: 2026-11-09. Baseline: `31e050e5` (main after #378).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the firings from 20:12 UTC on 2026-11-08 to 00:12 UTC on 2026-11-09. It reviews four merges.

- **#371** corrects the confidence-weighted ink loss for pseudo-labels.
- **#369** registers and reports finding 106, the fiber generator's block seams, and drafts a villa change.
- **#372** corrects the scan-quality statistics and reports incomplete analyses.
- **#378** binds the fiber benchmark's reports to the bytes they scored and keeps its outputs off its inputs.

## What changed

### #369: what ran, and two join counts (`docs/VILLA_DRAFT_afv_generator_seam_trim.md`, `docs/RESEARCH_STRATEGY.md`)

- **The villa draft misstated what code ran.**
  - It said "the generator's own modules at villa main", naming `splines.extract_splines` and the `cleanup` functions.
  - The script imports the #1934 head's package. Its docstring says the head's spline module differs from main's.
  - Its `identity()` gate compares only `predict.py` and five `extend` modules with main. `splines` and `cleanup` were
    never compared.
  - The draft now names the head's modules, says which were checked byte-identical to main and says that `cleanup`
    and `splines` were not. This is the text meant for villa.
- **"176 crossings are chained only with the trim."** The diagnosis evidence gives 182: 176 of the crossings better
  with the trim and 6 of those worse. The draft now says "of the 178 crossings better with the trim, 176 are chained
  only with it", the report's framing.
- **The strategy entry's "gains a join at 176 crossings and loses one at 63".** The evidence gives 182 and 64; one
  better crossing was chained only in main. It now says "176 of the 178 crossings the trim improves gain a join, and
  63 of the 198 it worsens lose one".
- **Tests.**
  - Each sentence's test fails on the old text.
  - New tests reach:
    - the decision rule at its registered bounds;
    - the verdict's held-out filter and its write-once guard;
    - the crossing kinds at 95%, 80%, 2 voxels and 40 voxels;
    - the diagnosis summary's counts and its refusal of another trim's records (a new module);
    - the amendment's quoted row;
    - the draft's bent-end figures, against the registration.
  - The committed diagnosis script's bytes are pinned. The evidence says it has the run's syntax tree.
- **Mutants.**
  - Of 48 mutants of the three scripts, #369's tests killed 8 and now kill 43. Of the five survivors:
    - two are equivalent: `>= 0.10` against `> 0.10`, which no integer pair in range reaches; and the linked-pair
      filter, since a linked pair shares a chain;
    - two sit in `run()`, which needs villa and torch;
    - one moves the crossing window by half a voxel.
  - Of 37 changes to the documents' figures, the tests now catch 36. The survivor is the villa PR numbers and date,
    which no record holds.

### #372: two inputs still lost the whole report (`scripts/measure_scan_quality.py`)

#372's usage document promises that a failed input gives an overall FAILED, exit 1 and a per-cube reason, and that
the other cubes are still measured and the report still written. Two inputs broke that promise.

- **A malformed NRRD crashed the run.**
  - pynrrd raises `StopIteration` for an empty file, `zlib.error` for a corrupt gzip payload and `KeyError` for an
    unknown `type:`. The per-cube `except` caught none of them.
  - With four good cubes and one empty or corrupt volume, the command exited 1 with a traceback. It printed nothing
    and wrote no `--out` file.
  - A small wrapper now turns exactly those three into the cube's `ValueError`. The run reports 5 requested, 4
    measured and 1 failed, and publishes the report.
- **A dangling cube link was skipped.**
  - Cubes were selected with `is_dir()`, which is false for a link whose target is missing. `main` deliberately
    accepts external cube links, so an unmounted external cube vanished from the report.
  - Four good cubes and one dangling link gave MEASURED, 4 requested and exit 0. The link is now a failed cube
    ("missing regular NRRD input"), and `docs/SCAN_QUALITY.md` says so.
- **A stale figure.** `scripts/characterise_label_cubes.py`'s docstring still said the CT outcome "is saturated at
  ~0.999 in every cube". #372's correction note marks that result as superseded. The docstring now says so.
- **Tests.** `tests/test_scan_quality.py` gains 16 cases (36 → 52). Five fail on the merged code, and they are the
  three defects' tests. The other 11 reach guards no test reached (below).

### #378: eight guards no test reached (`tests/test_fiber_benchmark_*.py`)

I made 26 mutants of #378's planning, capture and CLI. Its tests killed 18. Each of the eight survivors now has a test
that passes as merged and fails with its guard removed.

- **The capture refuses another cube's shape.** Before #378, `score` refused a shape mismatch. Removing the shape
  comparison from `read_instances` failed no test.
- **The instance digest comes from the captured bytes.** The new test replaces the file as soon as it is captured. A
  digest read again from the path would describe bytes that were never parsed. #378's own test replaced the file only
  after scoring, when the digest already existed.
- **The header prefix reaches NumPy's cap.**
  - `np.load` accepts padded headers up to 10,000 bytes, not just the 128-byte headers NumPy writes. A version 2 header
    of exactly 10,000 bytes needs all 10,012 bytes of the prefix.
  - The test reads 10,000-byte version 1 and version 2 headers and refuses 10,001-byte ones, as `np.load` does. A
    prefix of 10,011 bytes fails it.
- **`score --with-floors` plans its probability cache as an output.** Dropping `with_floors` from the plan left a
  symlinked cache unrefused until after the instances were read. Without floors, score never writes the cache.
- **A report path that is a symlink or a directory is refused before data work.** Neither aliases an input, so only
  the regular-file check catches them.
- **The rechecks after long work.** Three of #378's rechecks had no test:
  - the cache check after inference;
  - the all-cube report check after every cube;
  - the trace report check after saving instances.

  Atomic replacement never follows a symlink at the final path, so a planted link alone would be replaced, not
  followed. The harm is a directory swap. The tests replace the report's directory with a link to the model directory
  during the work. Without the recheck, the report replaces the model's `plans.json`.

## Verified, no change needed

- **#369 follows its registration.**
  - The registration was committed at 15:59 on 2026-11-06 (Pacific), the amendment at 19:13 the same day, and the
    result at 01:14 on 2026-11-08.
  - The amendment quotes the one row its first held-out cube had written. The registration has no amendment rule.
    The amendment changes which patch would be proposed, not the arms, metrics or decision rule.
  - `verdict()` on the record gives SUPPORTED: P1 8 of 8, P2 0.1282, P3 439 → 386 merges, P4 0.0705.
  - Every table row and summary figure in the report recomputes from the record. The diagnosis evidence reproduces
    the record's crossing counts for every cube, arm and variant.
  - Both patches' hunk headers count their bodies. The two trim functions agree when the zone is the whole volume.
- **#371's figures and counts.**
  - Run against the pre-#371 loss, each figure in its review and PR recomputes:
    - an ignored PNG-128 patch gives BCE 1.123006 and Dice 0.997490;
    - the four-pixel oracle gives 0.407404, where the old loss gives 0.777772;
    - an unscored sample halves the loss, 0.333333 → 0.166667.
  - The focused selection gives 114 passed and the ten curated modules give 202 passed, as the PR says.
- **#371's guards.** All 18 mutants fail its tests. They cover:
  - the PNG-128 sentinel and its exact tolerance;
  - the Dice weighting, union, scored-sample count and mean;
  - precision promotion before reductions, and the weight computed before it;
  - the BCE denominator and its clamp;
  - the shape and channel checks, and the unweighted Dice;
  - the checkpoint recipe, the trainer's branch and the handoff's ignore scope.
- **#378's move and counts.**
  - `capture_bytes` and `_nonblocking_open` are identical in `core/file_capture.py` and in `scripts/text_snapshot.py`
    before #378.
  - The two new modules collect 50 tests: the review's 49 plus the row-name regression it added afterwards.
  - With the workflow contracts they collect 135, as the PR says.
  - The PR's twelve curated modules give 372 at the merge, all passing in the checkout. The PR's 370 came before at
    least the row-name regression.
- **#372's statistics.**
  - The AUC with average ranks equals an all-pairs count with ties as half (n = 1,500).
  - The fold, the seed-0 balanced capped sampling and the 1,000-voxel gate hold at their boundaries.
  - The scaling (/255, /65535, big-endian) is right.
  - The gradient statistics are of nonzero magnitudes, and the tensor feature matches a whole-volume eigen-solve at
    high and 10⁻⁴ contrast.
  - Correlations pair only complete cases. MEASURED needs every cube and all four correlations.
- **#372's mutants.** Of 28, its tests killed 11. The new tests kill 16 more:
  - the population gate's bound and comparison;
  - the sample cap;
  - the gradient median and percentile;
  - the tensor's sigma, boundary and cross term, and its flat-voxel threshold;
  - Spearman versus Pearson;
  - pairing, the overall status, the AUC summary and the voxel bound.

  The survivor is the intensity standard deviation's `ddof` (observations).
- **#372's before/after numbers** reproduce against the code before it:
  - constant CT: 1.0 → 0.5;
  - the quantized fixture: 0.664275 → 0.502392;
  - the tensor feature, axis-aligned and diagonal: 1.0 / 0.333 → 1.0 / 1.0;
  - Spearman by double argsort: 1.0, against 0.894 tie-aware.

  "36 passed" matches what pytest collects. "146 passed across 4 modules" is 147 at the merge; none of those test
  files differ between the PR head and the merge, so the count predates a final test.

## Observations for the owner (not changed)

- **#369's registered script and chain.** The script is registered, so these are recorded, not changed.
  - **The model-revision gate fails open.** It checks `provenance.get("revision", REVISION) != REVISION`, which
    passes when the key is missing. The record's `settings.revision` is the constant, not what ran. So the record
    cannot show which model revision ran, and the test of that field cannot fail.
  - **The patch gate is weaker than the registration reads.** `identity()` drops everything between `FAMILIES` and
    the `CUT_END` line and the whole `trim_cut_ends` body before comparing. Code added there, any `CUT_END` value or a
    `trim_cut_ends` returning nothing would pass. What ties the run to the registered patch is the record's
    `cut_end` (16.0) and its `stitch.py` digest.
  - **The chain.**
    - `|| echo FAILED` keeps going past a failed cube. The verdict then writes NO_VERDICT once, which fails closed, but
      that record must be deleted by hand before a rerun.
    - A failing `$(...)` in its `for` list does not stop `set -e`.
    - It takes `VILLA` and `PATCHED` from the environment and checks nothing out; `identity()` is the only check.
  - **Overwrites.** `run()` replaces an existing `result.json`, and the summary script replaces its output.
  - **The diagnosis script** names the author's worktree path, and its usage line names `diag_lost.py`.
- **#369's report.**
  - "60" counts crossings where every other-block copy is a short chain. The test is also true when no copy from
    another block covers 20% of the window, since `all()` of nothing is true. The per-cube diagnosis files are not
    committed, so I could not split them.
  - The per-cube "11 gain one" counts only the better crossings. Counting the worse ones that also gained a join
    gives 14.
  - Written length takes each fiber's last half-voxel sample, so each fiber can be up to half a voxel short.
  - The report's ScrollGT commit is not in the record.
- **#369's villa patches.** Neither patch's villa tests ran here, and the amended patch's test helper could not be
  checked against villa's.
- **#372: the direction of the old tie bias.** The old ranking put sheet samples first and broke ties by position, so
  it deflated the AUC when sheets were the brighter class and inflated it when they were dimmer. On the same fixture, sheet brighter: old 0.686, new 0.739; sheet dimmer: old
  0.782, new 0.729. If the papyrus is brighter in the 12 cubes, the historical 0.9946–0.9997 are lower bounds, and
  "saturated" might survive the rerun. "Not validated" stays fair; the dated record is unchanged.
- **#372: the intensity standard deviation's `ddof`** is not stated or tested. At 256³ the difference is about
  3 × 10⁻⁸ relative. The recipe could say "population (ddof = 0)".
- **#372: a MEASURED cube can have undefined features.** A flat CT cube scores AUC 0.5 with null gradient statistics,
  so a correlation's `n` can be smaller than the measured count. This is documented; a new test pins that the overall
  status stays INDETERMINATE.
- **#372: axis kinds.** The axis-kind check refuses NRRD's `none` and `???` kinds. If the real cubes declare them,
  they would be reported FAILED. I did not check the dataset.
- **#378: the rechecks are snapshots.** They narrow the window but are not locks, as #378's review says. A swap
  between the last recheck and the rename would still land.

## Verification

- **The touched modules pass.**
  - #378's two modules give 62 passed: 50 of #378's and 12 new.
  - The scan-quality module gives 52 passed.
  - #369's five modules and the November draft's give 50 passed, with villa present.
  - Each new defect test fails on the merged code: 5 for #372 and 3 for #369. Each new #378 test fails with its guard
    removed.
- **Ruff and mypy.** Ruff 0.9.10 `check` and `format` are clean on the 10 changed Python files. Mypy is clean over the
  whole repository: MYPY_FILES files.
- **The standard suite.**
  - At the start of the round, with only new tests on top of `31e050e5`, it gave round #153's 70 failing ids.
  - On the finished branch, all 186 modules give the same 70 ids.
- **The test modules outside the suite.** On this branch the 252 modules give 2,410 passed, 82 skipped, 13 failed and
  21 errors. The failing ids are round #153's 34. The pass count is round #153's 2,400 plus the 10 tests this round adds
  to #369's modules: 3, 1 and 2 in its existing modules, and 4 in the new summary module.
- **The doc audit**, run alone, AUDIT_RESULT

## A note on this round's work

- **The reviews of #369 and #372 paused for about three and a half hours.** Both helper agents stopped at the
  account's usage limit at about 20:40 UTC and resumed after it reset at 00:10. The firings from 21:12 to 00:12
  queued, and the session's worker restarted several times. Afterwards, I checked every worktree against its commit;
  none held a mutant.
- **#378's selection in a sparse worktree** failed two tests that scan the whole checkout, because `v3_training/` is
  not checked out there. In the main checkout all 384 pass, with this round's tests.
- **My first suite run on the branch failed the suite guard.** A new #369 test held the string `"predict.py"`. The
  guard reads a bare script name as a file under `scripts/`, so it took the draft's test for a test of the loop's
  `scripts/inference/predict.py`. The test now names the module without the suffix, and the suite was rerun.
- **I added tests in the main checkout while the first suite ran there.** pytest had already collected its modules,
  and that run gave the 70 ids.
