# Design and architecture review: label-edit proposals

Reviewed main `b71946a1` in an isolated CPU checkout on October 31, 2026 (Pacific
time). Scope: the label-editing commands and the boundary between heuristic edits
and preferred training targets.

## Findings and fixes

1. **Wrong semantic tool.** `preprocess_labels.py` applied Villa functions for
   cylindrical spiral-label volumes to PNG ink strokes. The real pinned
   `detect_inner_region` added **588 background pixels** to four 2×2 marks
   containing only **16 positives** on a 64×64 image. This is a semantic fixture,
   not a quality measurement. The earlier
   [cross-scroll specification](superpowers/specs/2026-06-12-multi-scroll-cross-scroll-experiment-design.md)
   separately documents 89–97% overfilled masks being set aside.
2. **False success.** The wrapper ignored `cv2.imwrite`'s return value. Running its
   original `main` body with the pinned detector and a missing output parent
   printed `Success!` with no file. Outputs are now staged and decoded for readback.
3. **Unreviewed preferred targets.** The bulk EDT/Frangi prototype wrote
   `inklabels_refined.png` beside training and validation data. Its other output
   mode flattened fragment basenames, could overwrite earlier files, materialized
   unbounded volumes and selected an unproven fallback backend silently. Its CLI
   and Python helpers are retired; the path delegates to the new bounded 2D
   proposal workflow. Legacy options fail with migration guidance.
4. **Missing review and provenance contract.** A shared module publishes
   `PROPOSAL_ONLY` bundles with original/proposed/addition images, an overlay,
   component counts and boxes, source/code captures, settings, versions and hashes.
   Size, total-addition and component-count limits bound the proposal. Optional
   eligibility masks must cover whole holes. Approval, training readiness,
   annotation quality and CT-alignment flags remain false. No auto-preferred
   filename is written, and outputs must be outside source folders.
5. **Fragile help and imports.** Both commands resolve this checkout explicitly
   and parse help before scientific imports. Neither needs Villa or training
   packages. A dry run computes actual counts without creating output artifacts.

The pinned Villa source was fetched by commit through the GitHub connector:
`ccb431818fa68059138f2c964ae299fc474ff116`,
`vesuvius/src/vesuvius/scripts/fill_inner_outer_labels.py`, Git blob
`daee6a9eb0ca03af80429cb3f1b03f08edfe4ac1`. Reproduction executed its unchanged
detector AST and the unchanged local `main` AST; no substitute detector or live
research data was used.

## Architecture and verification

Thin CLI adapters share `scripts/label_edit_proposals.py`, reusing bounded binary
PNG captures, source rechecks and the existing new-directory publisher. Changes
are deterministic array proposals under explicit background-connectivity and
size settings. Small holes are not evidence of missing ink; letter counters can
be legitimate reasons to reject them. Live CT, study measurements, training
targets and checkpoints were not read or changed. Existing label preference
remains; altering it changes the validation protocol and needs separate work.

Final validation: **322 passed in 52.35 seconds, no skips**, using Python 3.10.21,
Torch 2.9.1 CPU and OpenCV 4.13, with CUDA hidden and numerical-library threads
limited to one. The seven modules were `test_label_edit_proposals`,
`test_data_catalogue_contracts`, `test_pseudo_handoff_contracts`,
`test_pseudo_label_quality`, `test_label_curation_contracts`,
`test_validation_suite_covers_the_loop` and `test_validation_runner` under `tests/`.
All 56 new proposal cases passed. Ruff check/format, Mypy over all five changed
Python files, local documentation links and whitespace checks passed.

The required smoke command reported **8/11 passed, 3 skipped, 0 failed in 10.2s**.
The skips were two absent local training datasets and the unavailable BGv2
augmentation entry point. Smoke loaded the tracked checkpoint in the isolated
checkout; other data/checkpoint exercises used synthetic fixtures. No live
research checkout was used. Direct executable `--help` was also checked.

The isolated checkout's upstream curator and patch-sampler files were captured
from the Villa pin and verified against their Git blob IDs; no replacement
implementations were used. A synthetic CLI bundle and its preview were inspected:
exactly four pixels were proposed while the large counter and open shape stayed
unchanged. The full repository suite and real-label quality were not measured.

The final author PR review is recorded in the pull request. Coverage includes
the semantic reproduction, component and change
budgets, binary encodings, unknown regions, image/path validation, source/output
mutation, staged completion order, write failure, no-output dry runs and fresh
interpreters that reject training/Villa imports.

See [usage and migration](LABEL_EDIT_PROPOSALS.md) for limits and retired
interfaces. No GPU, improved ink quality or large-image performance is claimed.
