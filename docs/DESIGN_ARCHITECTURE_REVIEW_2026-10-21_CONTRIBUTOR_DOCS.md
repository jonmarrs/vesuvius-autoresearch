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
    (`1 + LIFT_MARGIN`), on the same validation protocol and inputs;
  - "To stop: `pkill -INT -f ...`": `./stop.sh` stops the loop's runs and pauses the watchdog;
  - the project layout gave `train.py`, `vesuvius_loader.py`, `model_wrappers.py` and `predict.py` at the top
    level;
  - the install steps left out `git submodule update --init villa`, which README and CONTRIBUTING run. Without
    it, villa's metrics and augmentations are skipped, not failed;
  - the shift section left out scoring the incumbent before the first start (`reevaluate_best_model.py
    --update-stored`), without which the loop refuses to start. `make reeval` leaves the stored scores as they are;
  - the shift hours said PT; the loop reads the machine's local time.

  Each is now as the code, README and `CONTRIBUTING.md` give it. The layout follows `CONTRIBUTING.md`'s, and every
  path in it exists. A dated note at the top says what changed. The `USER` notes keep their May numbers, as the
  owner's drafts.
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
  - `audit_doc_references.documents()` now lists them too, less any file git ignores: a launcher's `CLAUDE.md` at
    the top level is no reader's document, and would make the audit differ between machines.
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
- **Tests** (`tests/test_audit_doc_references.py`):
  - `documents()` lists the README, CONTRIBUTING, METHOD, REPRODUCE and the README skeleton, as well as `reports/`
    and `docs/`;
  - `audit()` reads every document `documents()` lists;
  - a document git ignores is left out.

  Each of these mutants fails them: `audit()` reading only `reports/` and `docs/`, the ignored files kept, and the
  top level or `.github/` dropped.

## Verified, no change needed

- **`CONTRIBUTING.md`**: its commands, layout, shift hours and stop command are current. Its PR sections match
  `.github/PULL_REQUEST_TEMPLATE.md`.
- **The doc-reference audit's standing failure is environmental.** This container's `villa/` is a sparse checkout
  of the pinned commit (`ccb43181`), holding four directories. Every villa path the audit flags here exists in the
  pinned tree, which has, among others, `ink-detection/`, `deprecated/`, `volume-cartographer/`,
  `scrollprize.org/` and `spiral-fitting/`. Against the pinned tree, the only live stale paths are:
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

- `pytest tests/test_audit_doc_references.py`: 11 passed. `test_live_documents_stay_clean` fails here as on main,
  on villa paths absent from this sparse checkout and on the ignored checkpoint. It has one entry more: FINDINGS'
  corrected path, which is in the pinned tree but not in this sparse checkout.
- `pytest tests/test_shift_budgets.py`, which reads the skeleton: 17 passed.
- Ruff and mypy are clean on the changed Python files. The audit script was already ruff-formatted. The test file
  was not, so it keeps its own formatting.
- **The standard suite** on the first commit (`c8e585d5`) ran as on main: 2690 passed, with the same 42 failures and
  2 errors, all environmental. The smoke test gave 9 of 11 passed and 2 skipped, as on main.
- **Independent review** of the first commit found nothing blocking. It confirmed:
  - each command and path in the skeleton;
  - the promotion constants, and that the loop never pushes;
  - the citation's dates;
  - the two exemptions, and the FINDINGS path at the pin;
  - the audit's remaining stale paths.

  It checked villa paths against a tree-only copy of the pinned commit, which it fetched from villa's repository
  into the scratch area. This review's rules do not fetch villa, so that copy was deleted, and the paths were also
  checked against the local checkout's own record of the pinned tree.

  Its should-fix findings:
  - the doc's "no new path";
  - the skeleton's missing submodule step;
  - its missing first-start re-score;
  - no test that `audit()` reads what `documents()` lists.

  Its nits:
  - `LIFT_MARGIN`'s wording;
  - PT for local time;
  - the promotion rule's "same protocol";
  - "is CONTRIBUTING's" layout;
  - the reasoning's directories;
  - FINDINGS' wording;
  - a redundant conditional;
  - ignored top-level files;
  - this placeholder;
  - a docstring line.

  All are addressed above. Its last nit is not: that `CITATION.cff`'s 64x64 window does not cover
  `repro/ink_segformer`'s 224 tiles. The abstract's subject is the loop.
