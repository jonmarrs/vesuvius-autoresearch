# Design and architecture review — the retry probe's exit codes, and the downloader #203 fixed

Date: 2026-10-23. Baseline: `5ea69a9b` (main after #199). Main, now `aaf38e94` after the owner's
#202 and #203, is merged in.
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 13:20 UTC firing. #199 recorded two reachable defects in the owner's #196 and
#197 harnesses: the downloader's silent skips, with a proposed fix, and the probe's shared exit 1.
This round fixes the probe and finds the owner fixed the downloader.

## What changed

- **The fiber downloader dropped listed files without counting them.**
  - `repro/fibers/fetch_reference_annotations.py` skipped any `.json` link containing `/`, `\`, `:`
    or `%`, so a name an autoindex percent-encodes was neither downloaded nor counted. It still
    printed "Downloaded all N listed JSON files".
  - **This round's first commit fixed it.** It decoded names and recorded skipped links in a
    `skipped_hrefs` field, with three tests.
  - **The owner fixed the same defect in #203**, merged while this round ran.
    - #203 decodes names strictly, and also skips and records links with a query, a fragment, a bad
      percent escape or a control character.
    - It quotes each name again to fetch it, never overwrites a saved file, and records each skipped
      link with its reason in `skipped_json_links`.
    - When anything is skipped, it no longer prints "Downloaded all".
    - It is tested in `tests/test_reference_annotation_downloads.py`.
  - **The merge takes #203's downloader whole and drops this round's version and its three tests.**
    #203's code handles everything they tested, but its tests leave out three of the cases: an
    absolute-path href, a name with a colon, and a non-anchor `<link>`. Two links that decode to one
    name are merged into one file by #203, where this round refused them. The next round, which
    reviews #202 and #203, takes these up.
  - **The report** keeps this round's dated head note, now naming #203 and its field. Whether the
    published snapshots skipped any file cannot be checked from here: the captured listings are not
    in the repository.
  - **The snapshot record** still names the downloader version that ran. #199's binding accepts any
    committed version, so neither fix needs a new snapshot. The binding test passes after the merge.
- **The retry probe exited 1 both for a timeout and for every refusal.**
  - `repro/ink_native/check_retry_cycle.py` raised on a bad mesh hash, used bare `assert`s for the
    corner and pre-checks, and failed late on an existing record. Each of these exited 1, as the
    baseline timeout does. Only the record, which a refusal never wrote, told them apart. The report
    told readers to check the status, and `python -O` would have removed the two `assert`s.
  - **Refusals are now explicit and exit 2 with `refused: <why>` and no traceback.**
    - These are refused before anything runs:
      - an output path that exists, a dangling symlink included;
      - an output path whose directory does not exist;
      - a mesh file that is missing or is not the published one;
      - surface in either corner;
      - a patch villa does not reject, either one;
      - a missing POSIX timer.
    - A voxel touch before the geometry rejection is refused whenever it happens, including during
      the retry itself.
    - **Late failures before this.** An output in a missing directory, or a dangling symlink, failed
      only after the run (two seconds for the baseline cycle) and exited 1. A missing mesh file
      exited 1 with a traceback.
    - argparse's own usage errors also exit 2, without `refused:`; the docstring says so.
  - **The voxel sentinel** now also refuses attribute access. villa's first touch of a volume it reads
    is `.shape`, in `_read_flat_surface`. Before rejecting a patch, villa's `_native_sample` opens the
    handles but touches none of them, so the recorded runs are unaffected.
  - Exit 0 and 1 keep their meaning. An uncaught error, villa missing from `PYTHONPATH` among them,
    is still a traceback and 1. The docstring and a dated report note say so.
  - `tests/test_check_retry_cycle.py` now requires exit 2, the refusal's message and no traceback
    for every refusal.
    - It adds a `.shape` touch, a voxel read during the retry, a stand-in that admits only one of the
      two patches, a missing mesh file, a platform without the timer, a missing output directory and
      a dangling symlink.
    - It checks that output-path refusals happen before the dataset is built.
  - **54 of 55 mutants** of the revised probe fail a test. They include:
    - a `Refused` derived from `RuntimeError`, which the retry's `except` would have caught;
    - a pre-check of either patch alone.

    The survivor opens the record with `"w"` instead of `"x"`. That differs only if another process
    creates the record during a run, since any existing path is refused up front.

## Verified, no change needed

- **The recorded runs.** Neither record hashes the probe, and both came from the old probe. Its
  behaviour on the published mesh, two rejected corners, is unchanged.
- **Ruff.** The probe keeps main's findings (import order, one `dict()` call), no more.

## Observations for the owner (not changed)

- **Retaking the fiber snapshots** with #203's downloader would settle whether any file was skipped.
  `dl.ash2txt.org` is not reachable from this container.
- **The two older temporary packs** in `villa/.git/objects/pack` (`tmp_pack_SMpTdR` and
  `tmp_pack_fWNLrg`, from 13 October, about 400 MB) are from a failed git operation. Removing them is
  safe, but this round did not, since they predate it.

## Verification

- **The touched and new tests**, with the downloader, prize-readiness and filing tests main brought in:
  147 passed and 4 skipped. The probe's tests alone give 30 passed.
  - All 11 refusal tests in the first commit fail against `5ea69a9b`'s probe, as the independent
    review checked.
- **Mutants:** 54 of 55 of the probe fail a test, as above.
- **Ruff** 0.9.10 `check` and `format` are clean on the probe's tests. The probe keeps main's two
  findings.
- **The ledger and the suite coverage guard** pass.
- **Doc guards.** The 11 files that read a changed doc or glob the docs give 378 passed and 2 skipped on
  main `aaf38e94` and on the branch.
- **Doc audit:** the branch gains no entries.
- **The standard suite** with the locked-package overlay, on the merged tree: 2813 passed, 22 skipped
  and 1 xfailed, as on main. The ten failures are main's ten environmental ones: nine need villa
  files, one is `gp_winner`.
- **Independent review** of the probe and the notes found nothing blocking. It confirmed:
  - villa's `_native_sample` touches no volume handle before the rejection, so the new
    `__getattr__` cannot fire on the recorded runs;
  - the copy it read has the before record's hash, and the patch leaves `_native_sample` alone.

  Its should-fix items:
  - the timer refusal was untested;
  - three input errors still exited 1 late;
  - this doc overstated #203's tests.

  Its nits: two pre-check gaps, `Refused` unpinned from `RuntimeError`, argparse's exit 2, and this
  doc's baseline and opening. All are fixed in the third commit.
