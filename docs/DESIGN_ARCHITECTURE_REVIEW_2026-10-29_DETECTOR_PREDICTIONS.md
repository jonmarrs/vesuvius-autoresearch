# Design and architecture review: detector predictions, 2026-10-29

Reviewed baseline `47c262f5`, concentrating on the fragment detector's inference
and export boundary. This is a CPU-only review in an isolated worktree.

## Findings and changes

| Priority | Finding | Repair |
|---|---|---|
| P1 | The inference CLI could overwrite its checkpoint, config, layers or fragment mask, including through symlink and hard-link aliases. | Reuse the shared artifact collision checker before inference and publication. Protect the input tree and individual files; reject symlink and nonregular outputs. |
| P1 | Opening the destination directly truncated a previous prediction before serialization completed. | Serialize into a sibling temporary file and rename only after success. Clean up on serialization or rename failure and preserve destination permissions. |
| P2 | Unvisited pixels were indistinguishable from a model's zero probability. The original 64×100 full-mask example silently leaves 256 valid pixels uncovered. | Warn on partial coverage, report counts in the CLI, add optional strict coverage refusal, and offer an NPZ bundle with probability, coverage and the original fragment mask. |

The first regression run on the baseline produced 24 failures: 15 existing
export-safety failures and nine checks for the new coverage API and
format. A separate execution of the baseline inference body confirmed the
64×100 example returned 256 zero-filled fragment pixels with no warning.

## Architecture and operator behavior

`detector/prediction.py` holds the result object and the single-file publication
boundary. It reuses the core path-collision and permission helpers. Inference
keeps the existing tiling, full-window mask rule, normalization, model dispatch,
TTA, blending, and zero fill. Existing Python callers still receive a float32
probability array; `return_details=True` adds coverage information.

The default CLI output remains NPY. Optional NPZ schema 1 stores numeric arrays
only: `schema_version`, `probability`, `coverage`, and `fragment_mask`. Keeping
the maps in one file avoids a stale coverage sidecar after a probability map is
replaced. The output path is exact, with no automatic suffix. Strict coverage
checks the completed prediction and refuses publication if valid fragment pixels
are uncovered; it does not change the grid to fill them.

Evaluation and measurement emit the inference warning but retain their existing
metric definitions, report schema, and full fragment-mask denominator, including
uncovered zeros. Historical measurements and preregistrations are unchanged.
See [the workflow guide](DETECTOR_WORKFLOW.md) for usage and bundle fields.

## Verification

Commands below ran with `MPLCONFIGDIR=/tmp/vesuvius-detector-mpl`,
`XDG_CACHE_HOME=/tmp/vesuvius-detector-cache`, `OMP_NUM_THREADS=1`,
`OPENBLAS_NUM_THREADS=1`, `MKL_NUM_THREADS=1`, and `CUDA_VISIBLE_DEVICES=''`.

```sh
/tmp/vesuvius-chain-env/bin/python -m pytest -q -rs tests/test_detector_prediction_artifacts.py tests/test_detector_cli.py tests/test_validation_suite_covers_the_loop.py
```

**44 passed in 33.05s.** Includes a real small ResEnc checkpoint round trip on an
unlabeled synthetic fragment, strict failure preserving the previous bundle,
stride and mask-hole coverage, predicted zeros versus unvisited pixels,
input aliases, nonregular outputs, serialization and rename failures, exact
filenames, permission bits, and validation-suite registration. An earlier
overlapping run of the new cases, CLI, detector contracts and registry guard
passed 93 tests before the final additional publication cases were added.

```sh
/tmp/vesuvius-chain-env/bin/python scripts/smoke_test.py
```

**8/11 passed, 3 skipped, 0 failed in 21.5s.** The skips are two absent training
URI/inklabel fixtures and the unavailable batchgeneratorsv2 transform.

Ruff check and format-check pass for all six changed Python files. Targeted
Mypy with `--follow-imports=silent --explicit-package-bases --namespace-packages`
reports no issues in those six files. `git diff --check` passes.

A broader run including `tests/test_audit_doc_references.py` returned **55 passed,
1 failed**. The repository-wide live-document path guard fails on absent Villa
submodule paths and the unavailable detector checkpoint in this checkout.
Comparing cited paths with the baseline blobs found the same **38** missing
paths, including four existing historical exceptions; no new missing live paths
were introduced. This is not a passing repository-wide documentation gate.

## Limits

No GPU jobs, real-scroll quality/throughput experiment, full real-fragment
inference, native Villa integration, live-study inspection, research-host
deployment or prize submission was performed. The bundle has no input hashes
or training-lineage attestation. Export uses atomic replacement, not input
locking, concurrent-writer coordination, or a power-loss durability protocol.
Callers must use stable inputs and serialize writes. The implementation still
holds dense fragment arrays in RAM.
