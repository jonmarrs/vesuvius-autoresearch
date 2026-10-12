# Design and architecture review — cross-cutting contracts

Date: 2026-10-12. Baseline: `3ea6c7bd4fa9847b0a97e6dde4bb33c02973264c`.
Villa pin: `9afddaf0fdc12efe088bab7b82534c4f9a79e536`. Reviewer: Claude (Anthropic),
at the owner's request; changes are authored as such in the commit history.
Scope: code merged after the fiber-diagnostic review's baseline (`060585b6`), in
particular the re-vendored ScrollGT 0.7.0 scorer, plus contracts that cross
subsystem boundaries and that no single-subsystem review owns: how the package
imports pinned villa source, and which loop process state is under version control.

## What changed

Reject duplicated skeleton edges before fiber scoring. Stop tracking the loop's
lock file and shift-log pointer, and ignore them. Load the two pinned villa
modules the package imports at runtime from their absolute file paths instead of
putting villa directories at the front of `sys.path`.

## Why

A duplicated edge silently cut a perfect trace's ERL by half or more with no other
signal. A tracked lock let ordinary git commands admit a second concurrent loop.
Villa's TTA resolved to whichever `vesuvius` package was imported first, and the
lasagna warp was silently skipped outside the repository root.

## Findings and fixes

| Priority | Finding | Fix |
| --- | --- | --- |
| P2 | The path-order edge walk crosses a duplicated edge out and back, ending a stretch at every edge. A perfect trace of a 40-voxel fiber scored ERL 2.00 with every edge doubled (either orientation) and 20.61 with one edge doubled, instead of 40.00, at coverage 1.0 with zero splits and merges. `score_tracing` promises to reject input "that would otherwise be scored silently" but accepted it. | `_validate_fiber`, our wrapper outside the vendored core, rejects a node pair joined by more than one edge. Branches, loops and zero-length self-edges still score; a self-edge leaves the score unchanged. |
| P2 | `autoresearch.lock` was tracked (since `319b462b`, 2026-04-29). Loop ownership is an `fcntl` lock on the file's inode; a running loop leaves the file modified, and `git checkout -- .`, `git stash` or `git restore .` replace it. The first loop keeps its lock on the orphaned inode, a second loop acquires the new file, and `stop.sh` can no longer find the first. Reproduced with `scripts/loop_control.acquire_lock`. | Untrack and ignore it, with the shift-log pointer, which is the same kind of per-run state. A guard test requires all six loop runtime files to be untracked and ignored. |
| P2 | `villa_inference._load_villa_tta` prepended `villa/vesuvius/src` and imported `vesuvius.models.run.tta`. After an earlier `import vesuvius` it returned the older installed snapshot; before one, it bootstrapped the pinned package and replaced `vesuvius` for every later import in the process. This is the mixing `scripts/pinned_vesuvius.py` exists to prevent. `VillaTTAWrapper` has no current caller, so the defect was latent. | New `core/villa_modules.load_villa_leaf` executes a leaf module (one importing nothing from its directory or from `vesuvius`) from its absolute path under a private module name, once per process, without touching `sys.path` or `sys.modules["vesuvius"]`; it refuses a non-leaf module. TTA loads through it. |
| P3 | The lasagna uint8 warp inserted the relative path `"villa/lasagna"` at `sys.path[0]`. It resolved only from the repository root; elsewhere the import failed inside the method's `try`, and the `except` returned the unwarped patch, so flattening was silently skipped while the run recorded `use_lasagna: true`. The entry also shadowed ~90 generic top-level names (`model`, `common`, `optimizer`, `fit`) for the rest of the process. All 19 configs in `recent_configs.json` enable lasagna; the loop is unaffected only because `start.sh` changes into the checkout. | `grid_sample_3d_u8` (stdlib and torch imports only) loads through `load_villa_leaf`. A guard test fails if package code puts a string-literal path on `sys.path`. |

## Architecture and compatibility decisions

**Scorer.** The equivalence boundary is unchanged: `_validate_fiber` and
`score_tracing` are this repository's wrapper, not vendored ScrollGT source, so
`tests/test_fiber_scoring_matches_scrollgt.py` still compares the same eleven
definitions plus the scoring core. Validation is not scoring: on input that
passes, scores are byte-for-byte what they were. Every fiber of the 21 ScrollGT
v0.7.0 cubes passes (8,491 fibers, 458,949 edges, unpacked with ScrollGT's own
`_unpack_skeleton`), so no published or filed number changes and
`SCORING_VERSION` stays 5. ScrollGT itself validates nothing, so its entrants are
exposed to the same silent score; the guard should go upstream, which will need
a re-vendor because ScrollGT's `score_tracing` is the vendored core.

**Leaf loading versus `scripts/pinned_vesuvius.py`.** The two solve different
problems and both remain. `pinned_vesuvius_modules` registers pinned source under
its real `vesuvius.*` names for the duration of a block, for code that imports it
by name. `load_villa_leaf` is for a single self-contained file the package calls
into; it lives in the package because package code must not import from
`scripts/`. The leaf check is a static AST scan: relative imports, absolute
`vesuvius` imports and imports of a sibling module name are refused, including
imports nested in functions. A dynamic `importlib.import_module` would not be
caught; neither pinned file uses one. The cache key is a hash of the resolved
path, so a test tree and the real checkout never alias. A failed execution is
not cached.

`tests/test_villa_modules.py` checks that both files the package loads are still
leaves at the recorded pin, so a villa bump that adds a sibling import fails on
CPU rather than inside a GPU run. The lasagna CUDA extension is still compiled by
villa's own module-level `load(...)` call; it now runs once per process under the
private module name instead of under `grid_sample_3d_u8`.

**Deliberately unchanged.** `vesuvius_loader` still appends `villa/vesuvius/src`
and the fibers-dataset directory to the *end* of `sys.path` at import time.
`scripts/training/train.py` and 13 other scripts import `vesuvius.*` and can
resolve through that fallback when the installed package lacks a module; appending
cannot shadow an installed package, so it does not have the defect fixed here.
Replacing it is a separate change with its own migration.

**Loop state.** Configuration and promotion state the loop auto-commits
(`config.json`, `autoresearch_history.json`, `best_model.pt`) stays tracked by
design. Only process state is removed. The archival logs at the repository root
(`run.log.old`, `night_shift_2026-05-28_20-20-55.out`) were committed deliberately
in April–May and are left alone.

### Migration for the loop host

Applying the lock commit deletes `autoresearch.lock` from the working tree. Once
any loop has run, the file holds a PID, so `git am` / `git pull` refuses it as a
local modification, and the obvious remedy, `git checkout -- autoresearch.lock`,
is exactly the hazardous operation if a loop is running. Therefore:

```sh
./stop.sh
python3 scripts/loop_control.py status   # must report no running loop
git checkout -- autoresearch.lock .current_day_shift_log
git am 000*.patch                        # or git pull
./start.sh                               # acquire_lock recreates the lock file
```

Losing the pointer only means the first shift after the update starts a new
sprint log instead of resuming that day's.

## Remaining architecture observations (not changed)

- The installed package is not self-contained: `core/model_wrappers.py` imports
  the root-level `vesuvius_model.py`, and `detector/cli.py` appends
  `repro/gp_winner` to `sys.path` (file-anchored, so editable installs only).
  Both work from a source checkout, which is how the project is run.
- `git clean -x` deletes ignored files, including a held lock. That command is
  destructive by intent; the untracking removes the routine path to the defect,
  not every possible one. A holder-side check that the path still names the
  locked inode would close the rest.
- `scripts/dev/check_villa_patch_finder.py` still prepends `villa/vesuvius/src`.
  It imports a non-leaf module and is a manual developer probe, not a workflow.

## Verification

Environment: CPython 3.10.20 venv with NumPy 2.2.6, SciPy 1.15.3, pytest, Ruff
0.9.10 and mypy, plus the package installed editable without dependencies. No
GPU and no PyTorch: torch 2.9.1's CUDA dependencies did not fit the review
sandbox. Villa was a sparse checkout at the pin (`vesuvius/src/vesuvius`,
`lasagna`, `foundation/datasets/fibers-dataset`) linked at `villa/`; ScrollGT
v0.7.0 (`6d05d64`) was checked out beside the repository. `$PY` below is that
interpreter.

### Reproductions on the baseline

Duplicated edges, unvalidated core (`_score_tracing_scrollgt`), 40-voxel fiber,
oracle prediction, `tolerance=0`:

```text
clean                erl=40.00 gt_len=40.0 cov=1.0 splits=0 merges=0
all doubled          erl=2.00 gt_len=80.0 cov=1.0 splits=0 merges=0
all reversed-doubled erl=2.00 gt_len=80.0 cov=1.0 splits=0 merges=0
one dup              erl=20.61 gt_len=41.0 cov=1.0 splits=0 merges=0
```

Lock: process A holds `acquire_lock` in a clone of the baseline; process B then
tries to acquire it.

```text
before: git status ->
 M autoresearch.lock
loop B correctly refused (lock held)
operator discards local changes: git checkout -- autoresearch.lock
loop B ALSO acquired the lock  <-- two loops running
```

TTA import order, with a fake installed `vesuvius`, a fake pinned tree and a stub
`torch` module (the real call needs no tensor work):

```text
installed-first  TTA used -> INSTALLED (old snapshot) | later `import vesuvius` -> INSTALLED
tta-first        TTA used -> PINNED | later `import vesuvius` -> PINNED
```

Lasagna resolution, run from `/tmp`:

```text
OLD from /tmp: ModuleNotFoundError - No module named 'grid_sample_3d_u8'
```

### Failing-first regression tests

Each new test was run against the unfixed code:

```sh
$PY -m pytest tests/test_fiber_eval_trace.py -q --no-header
$PY -m pytest tests/test_loop_lifecycle.py -q --no-header -k runtime_state
$PY -m pytest tests/test_villa_modules.py -q --no-header -k relative_path
```

```text
3 failed, 14 passed in 0.73s
E       assert not ['autoresearch.lock', '.current_day_shift_log']
1 failed, 9 deselected in 0.18s
E       assert not ['src/vesuvius_autoresearch/core/vesuvius_loader.py:455']
1 failed, 14 deselected in 0.16s
```

Interpretation: the three duplicate-edge cases, the two tracked runtime files and
the relative `sys.path` entry are each detected on the baseline.

### After the fixes

```sh
OMP_NUM_THREADS=1 $PY -m pytest tests/test_villa_modules.py tests/test_fiber_eval_trace.py tests/test_fiber_scoring_matches_scrollgt.py tests/test_loop_lifecycle.py tests/test_pinned_vesuvius.py -q --no-header -rs
```

```text
SKIPPED [1] tests/test_villa_modules.py:140: could not import 'torch': No module named 'torch'
SKIPPED [1] tests/test_villa_modules.py:157: could not import 'torch': No module named 'torch'
56 passed, 2 skipped in 3.63s
```

Interpretation: scorer validation, all 13 ScrollGT v0.7.0 equivalence checks, loop
lifecycle and runtime-state guards, leaf loading (import state, caching, refusal,
failure, missing file), the pin's leaf status for both real files and the
`sys.path` guard pass. The two call-site tests need PyTorch and skip here.

Real data, every fiber of the 21 shipped cubes through the new `_validate_fiber`:

```text
8491 fibers / 458949 edges in 21 cubes pass the new validation
```

Lock reproduction rerun on a clone of the branch:

```text
loop A holds lock, pid 338
git status shows: []
after git checkout -- .  -> loop B correctly refused (lock held)
after git stash          -> loop B correctly refused (lock held)
after git restore .      -> loop B correctly refused (lock held)
```

TTA import order and lasagna resolution on the branch:

```text
installed-first  TTA used -> PINNED | later `import vesuvius` -> INSTALLED
tta-first        TTA used -> PINNED | later `import vesuvius` -> INSTALLED
NEW from /tmp: ModuleNotFoundError - No module named 'torch' | raised inside /home/claude/villa/lasagna/grid_sample_3d_u8.py line 5
```

Interpretation: from outside the repository the pinned file is now found and
executed; it stops at its own `import torch` only because this environment has
none. The TTA call-site test also passed under the stub (`1 passed`).

### Standard validation, baseline versus branch

`scripts/run_validation_tests.py`'s list was run with
`--continue-on-collection-errors` on a worktree of the baseline and on the branch:

```text
baseline: 39 failed, 884 passed, 2 skipped, 32 errors in 40.58s
branch:   39 failed, 902 passed, 4 skipped, 32 errors in 34.20s
failing ids: baseline=71 branch=71
only failing on branch:
only failing on baseline:
```

Interpretation: the 71 failing or erroring IDs are identical and come from
packages absent in this environment (`torch` 33, `cv2` 18, `sklearn` 5, and
`fpdf`, `yaml`, `tensorstore`, `pytorch_lightning`). The 18 extra passes and 2
extra skips are the new tests. This is not a substitute for the full suite.

### Patch application

The series was applied with `git am` to a fresh clone of the baseline whose lock
held a PID:

```text
error: autoresearch.lock: does not match index
Patch failed at 0002 loop: stop tracking the process lock and shift-log pointer
```

After discarding the stale lock content with no loop running, all three patches
applied, `git status` was clean and the lock file was absent until the next start.

### Documentation reference audit

```sh
$PY -m pytest tests/test_audit_doc_references.py -q --no-header
```

```text
1 failed, 8 passed in 23.51s
```

Interpretation: `test_live_documents_stay_clean` fails identically on the
baseline worktree. All twelve reported paths are villa directories outside the
three this review's sparse checkout contained (for example `villa/ink-detection`,
`villa/volume-cartographer`); none comes from this change. It needs a full villa
checkout to be meaningful.

### Lint, formatting, whitespace and typing

```sh
ruff check <7 changed Python files>
ruff format --check <7 changed Python files>
git diff --check
mypy src/vesuvius_autoresearch/core/villa_modules.py src/vesuvius_autoresearch/fibers/eval_trace.py tests/test_villa_modules.py
mypy src/vesuvius_autoresearch/core/villa_inference.py src/vesuvius_autoresearch/core/vesuvius_loader.py
```

```text
All checks passed!
7 files already formatted
Success: no issues found in 3 source files
Success: no issues found in 2 source files
```

Interpretation: both pre-existing test files were formatted at baseline, so the
formatter touched only new lines. The whole-repository mypy run was not repeated.

## Edge cases considered

- Duplicates in the same and reversed orientation, a single duplicate mid-fiber,
  branches, closed loops and zero-length self-edges; real data with no duplicates.
- The lock replaced by `checkout`, `stash` and `restore` while held; runtime files
  that were already ignored; applying the untracking commit over a lock with a PID.
- `vesuvius` imported before and after the TTA load; a run from outside the
  repository root; a leaf loaded twice; relative, `vesuvius`, sibling and nested
  imports; a module that raises during execution; a missing pinned file; several
  trees with the same relative file names loaded in one process.

## What was NOT tested

- The lasagna call-site test and the real TTA call: PyTorch could not be installed.
- `scripts/smoke_test.py`, the complete validation suite with all dependencies, a
  whole-repository mypy run, GPU execution and the CUDA extension build.
- A real autoresearch shift, training or any scientific measurement.
- ScrollGT itself; no upstream change was made.

## Reviewer focus

Check that duplicate rejection cannot alter a score on valid input and that the
vendored-core boundary is intact. Confirm the leaf definition is strict enough for
the two pinned files, and that the private-name, once-per-process loading suits
the lasagna CUDA extension in DataLoader workers. Run the two torch-gated tests
and the smoke test on the GPU host, and follow the migration steps on that host.
