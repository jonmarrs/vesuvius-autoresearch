# Design and architecture review — the contributor-facing documents and the citation

Date: 2026-10-21. Baseline: `05840c62` (main after #167).
Reviewer: Claude (Anthropic), at the owner's request.

Scope: the documents a contributor reads first, which the doc-reference audit did not read:
- the top-level `*.md`;
- `.github/README_SKELETON.md`, whose technical sections call themselves verified and copyable;
- `CITATION.cff`, which no review had read.

Main has not moved since #167, and no owner PR is open.

## What changed

- **The README skeleton's "verified" commands no longer worked.** It says its install, run and layout sections can
  be copied verbatim, but since May:
  - `uv run python train.py --config config.json` names a file that moved to `scripts/training/train.py`;
  - "a row in `results.tsv`": a direct run writes `history.tsv`, `last_model.pt` and `run_result.json`, and the
    promotion files only if it promotes (`docs/program.md`);
  - "the loop auto-commits and pushes any cycle that improves val_bpb". `commit_promotion` commits
    `config.json`, `best_model.pt` and `autoresearch_history.json` locally and never pushes. It promotes on `val_f1`
    beating the incumbent's by more than 0.01 (`F1_NOISE_TOLERANCE`), with an AP-prevalence lift above 1.02
    (`LIFT_MARGIN`);
  - "To stop: `pkill -INT -f ...`": `./stop.sh` stops the loop's runs and pauses the watchdog;
  - the project layout gave `train.py`, `vesuvius_loader.py`, `model_wrappers.py` and `predict.py` at the top
    level.

  Each is now as the code and `CONTRIBUTING.md` give it. The layout is `CONTRIBUTING.md`'s, every path of which
  exists. A dated note at the top says what changed. The `USER` notes keep their May numbers, as the owner's
  drafts.
- **`CITATION.cff`'s abstract described May's loop.** It said the loop "samples a configuration space
  (architectures, losses, augmentations)" and "evaluates them with topological metrics against a fixed
  cross-fragment baseline".
  - The architecture has been pinned to `resenc_unet` since 2026-06-09.
  - Promotion has been on threshold-swept F1 gated by AP-prevalence lift since 2026-07-11, with topology reported
    only (`METHOD.md`).
  - The abstract now says so. The file still parses as YAML with the same keys.
- **The doc-reference audit read only `reports/` and `docs/`.**
  - The documents a contributor reads first were never checked: README, CONTRIBUTING, METHOD, REPRODUCE,
    SUBMISSION, FINDINGS, CREDITS and `.github/`.
  - `audit_doc_references.documents()` now lists them too.
  - Checked against villa's pinned tree, not this container's sparse checkout, they cite three paths that are not
    there:
    - `FINDINGS.md` cited the Grand-Prize pipeline at `villa/ink-detection/inference_timesformer.py`. At the
      current pin it is `villa/deprecated/ink-detection/inference_timesformer.py`; the record now cites that, and
      says it was at `villa/ink-detection/` then;
    - `METHOD.md`'s `villa/ink-detection/models/` is what `resnet3d` and `i3d` import from, and the document says
      villa moved it;
    - `REPRODUCE.md`'s `villa/ink-detection/train_scrolls` is the detector's default `data_root`, which the
      reproduce step's conversion creates.

    The last two are named exemptions in the test, as the audit's existing ones are.
- **Test** (`tests/test_audit_doc_references.py`): the audit reads the README, CONTRIBUTING, METHOD, REPRODUCE and
  the README skeleton, as well as `reports/` and `docs/`.

## Verified, no change needed

- **`CONTRIBUTING.md`**: its commands, layout, shift hours and stop command are current. Its PR sections match
  `.github/PULL_REQUEST_TEMPLATE.md`.
- **The doc-reference audit's standing failure is environmental.** This container's `villa/` is a sparse checkout
  of the pinned commit (`ccb43181`), holding four directories. The pinned tree has `ink-detection/`,
  `deprecated/` and `volume-cartographer/`, so the villa paths the audit flags here exist on a full checkout.
  Against the pinned tree, the only live stale paths are:
  - the four named exemptions;
  - `models/detector/detector_epoch=7.ckpt`, an ignored local checkpoint.
- **Bare file names** (`train.py`, `results.tsv`) in the top-level documents are mostly shorthand for the file
  under its directory, or for a run's output. An audit of them would mostly report noise, so it is left out.

## Observations for the owner (not changed)

- **`reports/doc_reference_audit.txt`** is the audit's last committed run, from 2026-09-02 (119 documents). The
  audit now reads 388: the 7 top-level documents and 3 in `.github/` added here, and the reports and docs written
  since. Regenerating it in this container would report villa's absent directories as stale, so it is left for a
  machine with a full villa checkout.
- **The skeleton's `USER` notes** still quote May's best `val_bpb` and promotion count. They are the owner's drafts
  for a README that has since been written, so they are unchanged.

## Verification

- `pytest tests/test_audit_doc_references.py`: 9 passed. `test_live_documents_stay_clean` fails here as on main,
  on villa paths absent from this sparse checkout and on the ignored checkpoint, with no new path.
- `pytest tests/test_shift_budgets.py`, which reads the skeleton: 17 passed.
- Ruff and mypy are clean on the changed Python files. The audit script was already ruff-formatted. The test file
  was not, so it keeps its own formatting.
- The standard suite, the smoke test and the independent review are recorded below once run.
