# Design and architecture review — the owner's #292–#295 (patch lineage, detector predictions, NML import, fiber streaming)

Date: 2026-10-30. Baseline: `7362a1ad` (main after #295).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 21:13–00:14 UTC firings. Three read-only reviews ran beside mine: #292, #293, and #294 with
#295. I checked each of their findings before acting on it.
- **#292** binds patch-bootstrap arms to their selection manifests and refuses aliased or duplicated arms.
- **#293** publishes detector predictions atomically, refuses outputs that alias inputs, and reports coverage.
- **#294** parses NML ground truth as XML and can refuse partial graphs (`--strict-nml`).
- **#295** streams the fiber filter CLI through halo blocks and protects published artifacts.

## What changed

- **A copy of the bootstrap arm's links passed as the control** (#292, `scripts/patch_check_inputs.py`).
  - #292 refuses the same patch container given as both arms, including aliases. A copied link folder is a
    different container, so it passed. With its manifest removed it passed both checks: the selection check gave
    PASS with 2 of 2 patches overlapping and an area gap of 0.00, and the spatial check gave MEASURED.
  - Two arms that select exactly the same patches are now refused in both checkers.
  - The test fails on #292's checkers.
- **The spatial check refused a FULL dataset that the builders accept** (#292 regression,
  `scripts/check_patch_spatial_balance.py`).
  - #292 made `read_arm` refuse two patch IDs resolving to one directory. The spatial check reads `--full` through
    `read_arm`, so the rule covered every FULL entry. The builders apply it to scored patches only.
  - A FULL dataset with two unscored IDs aliasing one directory then failed ("u1 and u2 resolve to the same
    directory"); the parent measured it. The guide says unscored FULL patches stay outside the comparison.
  - With `--full`, the check now covers the scored patches, both when reading and when rechecking before the
    report. The test fails on #292's checker.
- **`bootstrap_ids`** (`scripts/patch_dataset_artifacts.py`) lost its last caller in #292 and is removed.
- **`floors --all-cubes --strict-nml` ran inference before refusing** (#294, `src/vesuvius_autoresearch/fibers/bench_cli.py`).
  - The guide says strict mode refuses partial graphs "before inference". The all-cubes loop loaded each cube's
    graph just before that cube's inference, so a dangling edge in a later cube was found after the earlier cubes'
    inference had run. The report was kept; the GPU time was spent.
  - Strict mode now checks every cube's graph before the loop. The test counts inference calls and fails on #294's
    code (one call).
- **#295's non-finite test did not reach its check** (`tests/test_fiber_streaming_cli.py`).
  - `test_nonfinite_late_block_never_replaces_previous_output` gave the CT a NaN. The input check refuses that
    before any block, so the per-block output check the test is named for never ran, and the test passed on the
    parent.
  - A second case now runs a finite CT whose last block's filter response is NaN. That case fails with the output
    check removed.
- **#290 broke a test outside the standard suite** (`tests/test_fiber_chain_loop_guard.py`).
  - #290's seed-heading launcher refuses a missing status helper before its loop guard. The guard test runs every
    chain against a stub checkout with no scripts, so the seed-heading cases stopped at the helper check: 4
    failures, and its loop guard was no longer exercised.
  - The stub checkout now has the helper, and all 29 cases pass. The #290 review did not run tests outside the
    standard suite, which is how it missed this.
- **The patch selection guide** (`docs/PATCH_DATASET_SELECTION.md`) says that identical arms are refused, that
  unscored FULL patches are outside the distinct-directory check, and that a RANDOM arm is refused as BOOTSTRAP
  while its record is present.

## Verified, no change needed

- **#292** (the #292 review).
  - Present manifests are now read by both checkers and the STRIPMATCH builder. A bootstrap built from changed
    reference bytes fails, and a RANDOM arm passed as `--bootstrap` fails on its recorded mode.
  - The same container, root and container aliases, and two IDs resolving to one directory are refused.
  - A two-patch arm's p25 is now undefined. From three values up, the exclusive method interpolates between data.
  - Datasets built before #292, including a STRIPMATCH without a recorded bootstrap manifest, pass the new
    checkers under `--require-manifests`. Exit codes are unchanged.
- **#293** (the #293 review).
  - Its main fix holds: on the parent, `--output fx/model.ckpt` overwrote the checkpoint; the merge refuses and
    leaves it byte-identical. A failed save keeps the previous file and removes its temporary file.
  - Coverage matches a brute-force per-pixel computation through the real loader in 35 random cases. The real CLI
    round trip gives 6144/6400 (96.00%), as the guide's example.
  - Existing callers of `infer` still get a float32 array by default.
- **#294** (the #294/#295 review).
  - The one real NML in the checkout (Villa's `fibers_s5_06500z_02000y_04000x_500_v03.nml`) loads identically
    under the old and new parsers: 456 trees, 20,572 nodes, 20,116 edges, the same IDs, coordinates and scale.
  - Cycles, disconnected components, duplicate edges and IDs, and empty trees give the parent's graph.
    Downstream consumers round and bounds-check the now-fractional coordinates. `source_sha256` hashes the parsed
    bytes.
- **#295** (the #294/#295 review).
  - In 39 CLI cases (five dtypes, both filters, uneven shapes and blocks), streaming output is byte-identical to
    the old tiled and dense outputs. So is a 192³ volume, with peak memory 171 MB against 205 MB.
  - Staging files are renamed into place in the destination directory. Previous artifacts survive compute and
    serialization failures. Paths and the input's identity are rechecked before publishing.
- **The checks** (mine). Ruff 0.9.10 `check` and `format` and whole-repository mypy (841 files) are clean on the
  four merges and on this round's changes.

## Observations for the owner (not changed)

- **#292:**
  - **The area gates still disagree.** STRIPMATCH accepts a 1% relative area gap; the selection check fails above
    0.5 points of total area. A build the checker then rejects was reproduced. #292's record keeps them on purpose,
    and the checker gates.
  - **Without `--require-manifests`, a deleted manifest skips manifest checks.** Documented as legacy behaviour.
  - **Other links at an arm's root are not bound.** Only patch targets are recorded and rechecked; whether training
    reads the other root entries was not determined.
  - **Untested guards.** Several of the manifest guards have no test: the threshold selection, the recorded
    threshold, the `--full` binding, the STRIPMATCH bootstrap path and the builder's pre-publication recheck. Each
    works when tried by hand.
  - **Float equality.** `selected_area` is compared exactly. That holds on Python 3.10, which the project requires.
- **#293:**
  - **A write-protected output is now replaced.** The replacement keeps its 0444 mode. This matches the repository's
    other rename publishers, but the guide does not say so.
  - **A writable output in a non-writable directory now fails after inference.** The rename needs the directory,
    and the check before inference does not test it. The previous file is kept.
  - **Smaller points:**
    - an output name of 246 bytes or more fails after inference (the temporary name exceeds 255);
    - the recheck after serialization has no test;
    - a killed process leaves its hidden temporary file;
    - `--output x.npz` without `--output-format npz` writes NPY bytes.
- **#294:**
  - **Mixed namespace prefixes give an empty graph without an error.** Children unprefixed under a prefixed root
    are not found. WEBKNOSSOS does not write namespaced NML.
  - **Stricter reading.** A single non-UTF-8 byte now rejects the file, and Python number syntax (`4_0`) is
    accepted. Two guards (several `<scale>` elements, a non-bool `strict_edges`) have no test.
  - **Baseline count.** #294's record gives its first baseline run's count, "35 failures and 1 pass". The merged
    test file gives 46 and 1 on the parent.
- **#295:**
  - **The minimum halo is one voxel short at a volume face whose tile core is one voxel wide.** The minimum is
    `int(4σ + 0.5) + 2`, but the one-sided second derivative at a face reaches three voxels in.
    - This happens on an axis one longer than a multiple of the block size. At halo 10 (σ = 2), tiled and dense
      differ by up to 0.00032; halo 11 matches.
    - The rule predates #295 (it is in `detection.py`'s tiled API too). The default halo of 16, and the 16 the
      bench uses, are unaffected. Several of the owner's tests run at the minimum, so tightening it is the owner's
      call.
  - **`--preview` always writes PNG at the exact path.** The parent chose the format from the suffix. This follows
    #295's exact-path design, which the owner's test pins with a non-PNG name, but #295's record does not mention
    the change.
  - **The input mapping is closed explicitly while views of it may exist.** The CLI never reads such a view after
    the close; a future caller doing so would segfault rather than raise.
  - **Untested guard, baseline count.** The free-space check has no test. #295's record gives its initial
    baseline run's count, "12 failures and 7 passes"; the merged test file gives 31 and 8 on the parent.

## Verification

- **The changed areas' tests:**
  - patch tooling: 165 passed;
  - NML import and streaming CLI: 88 passed;
  - fiber modules with the bench and file-mode tests: 483 passed, 25 skipped, apart from the chain guard fixed
    above;
  - chain guard: 29 passed.
- **Each new or changed test fails on the code before its fix.** For the streaming test, that means without the
  output check.
- **The standard suite** gives the same 43 failures as before, from `s3fs`, `numba`, `jsonschema` and Villa files
  absent here. The same 2 modules cannot be collected (`tensorstore`, `s3fs`).
- **The 229 test modules outside the standard suite** give 2,092 passed, 80 skipped, 13 failed and 21 collection
  errors.
  - Apart from the chain guard fixed above, each failure is environment-only or standing:
    - the `probe_*` modules need Villa's spiral modules;
    - five new failures and two collection errors need `s3fs`;
    - the rest also failed on 10-24.
  - `test_live_documents_stay_clean` lists the same 20 Villa and model paths.
- **The doc audit** finds no new unresolved reference.
