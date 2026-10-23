# Design and architecture review — the fiber downloader's silent skips, the retry probe's exit codes

Date: 2026-10-23. Baseline: `5ea69a9b` (main after #199).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 13:20 UTC firing. Main has not moved since #199, and there are no open pull
requests. #199 recorded two reachable defects in the owner's #196 and #197 harnesses and proposed
fixes; this round makes them.

## What changed

- **The fiber downloader dropped listed files without counting them.**
  - `repro/fibers/fetch_reference_annotations.py` skipped any `.json` link containing `/`, `\`, `:`
    or `%`. An autoindex lists a name with a space as `%20`, so such a file was neither downloaded
    nor counted. The downloader still printed "Downloaded all N listed JSON files".
  - Names are now percent-decoded before they are checked. A decoded name containing `/`, `\`, `:`
    or a NUL would leave the folder, or be unsafe as a file name.
    - Such a link is still not fetched, but the manifest lists it under `skipped_hrefs` and the
      downloader prints it. So "all listed" can be checked against the manifest.
    - Every other `.json` link is fetched by its listed href and saved under its decoded name.
  - Two links that would save under one name are refused before anything is downloaded.
  - **Tests.** Three new tests in `tests/test_audit_fiber_reference_provenance.py` cover a
    percent-encoded name, six kinds of link that leave the folder, and a name collision. All three
    fail on the old downloader.
    - A non-anchor `<link>` in the listing is ignored.
    - The owner's own tests pass unchanged, including the `../outside.json` link they expect to be
      skipped.
  - **11 of 11 mutants** of the change fail a test. The first run left one alive, a dropped
    anchor-tag check; the non-anchor `<link>` case now kills it.
  - **The report** gains a dated head note: whether its snapshots skipped any file cannot be checked
    from here, because the captured listings are not in the repository.
  - **The snapshot record** still names the downloader version that ran. #199's binding accepts any
    committed version, so it needs no new snapshot.
- **The retry probe exited 1 both for a timeout and for every refusal.**
  - `repro/ink_native/check_retry_cycle.py` raised on a bad mesh hash, used bare `assert`s for the
    corner and pre-checks, and failed late on an existing record. Each of these exited 1, as the
    baseline timeout does. Only the record, which a refusal never wrote, told them apart. The report
    told readers to check the status, and `python -O` would have removed the two `assert`s.
  - **Refusals are now explicit and exit 2 with `refused: <why>` and no traceback.** They cover:
    - a missing POSIX timer;
    - an existing record, checked before anything runs;
    - a mesh file that is not the published one;
    - surface in either corner;
    - a patch villa does not reject;
    - a voxel touch before the rejection.
  - **The voxel sentinel** now also refuses attribute access. villa's first touch of a volume it reads
    is `.shape`, in `_read_flat_surface`. Before rejecting a patch, villa's `_native_sample` opens the
    handles but touches none of them, so the recorded runs are unaffected.
  - Exit 0 and 1 keep their meaning. An uncaught error, villa missing from `PYTHONPATH` among them,
    is still a traceback and 1. The docstring and a dated report note say so.
  - `tests/test_check_retry_cycle.py` now requires exit 2, the refusal's message and no traceback
    for every refusal. It adds a `.shape` touch, and checks that an existing record is refused
    before the dataset is built.
  - **48 of 49 mutants** of the revised probe fail a test. The survivor opens the record with `"w"`
    instead of `"x"`. That differs only if another process writes the record during a run, since the
    up-front check refuses an existing one first.

## Verified, no change needed

- **The recorded runs.** Neither record hashes the probe, and both came from the old probe. Its
  behaviour on the published mesh, two rejected corners, is unchanged.
- **Ruff.** The three owner files keep main's findings (import order, one `dict()` call), no more.

## Observations for the owner (not changed)

- **Retaking the fiber snapshots** with the fixed downloader would settle whether any file was
  skipped. `dl.ash2txt.org` is not reachable from this container.
- **The two older temporary packs** in `villa/.git/objects/pack` (`tmp_pack_SMpTdR` and
  `tmp_pack_fWNLrg`, from 13 October, about 400 MB) are from a failed git operation. Removing them is
  safe, but this round did not, since they predate it.

## Verification

- Pending.
