# Design and architecture review — the owner's #214 and #215

Date: 2026-10-24. Baseline: `34cb015f` (main after the owner's #214 and #215).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 05:12, 06:13, 07:12, 08:13 and 09:12 UTC firings. The 04:12 firing found main
unmoved after #217.
- **#214** bumps 19 non-ML transitive dependencies in `uv.lock`, among them urllib3, requests, idna,
  anyio, tornado and GitPython.
- **#215** replaces the data server's basic-auth credentials in five June plan and spec documents with
  `$ASH2TXT_USER` and `$ASH2TXT_PASS`.

No problems were found, so nothing is changed. This document records what was checked, and what the
lock still carries.

## Verified, no change needed

- **#215 removed every copy of the credentials.** The old pair appears nowhere on main. The remaining
  references are the two environment variables, and no script, test or source file reads them.
  `repro/villa_preserved/ink_detection/download.sh` prompts for its credentials and held none. The
  history still holds the old pair, which are the Vesuvius Challenge's shared registration credentials.
- **#214's lock is PyPI's.**
  - The 75 sdists and wheels of the 19 bumped packages match PyPI's sha256 and sizes, and none is yanked.
  - `uv lock --check` passes.
- **The bumps clear what they were for.** PyPI's advisory data lists advisories against every old
  version, and none against any new one. GitPython 3.1.47 had 48, mistune 3.2.0 had 30, tornado 6.5.5
  had 14, urllib3 2.6.3 had 10. #213's certifi 2026.2.25 carried PYSEC-2026-4320; 2026.10.23 carries
  none. s3fs moves only to follow fsspec.
- **The lock's format moved from revision 3 to 5.** The same re-lock dropped the
  `sys_platform != 'win32'` marker from 67 dependency edges, which matters only on Windows.
  Nothing pins an old uv: the Dockerfile, README and Makefile install the latest. uv 0.11.32 here reads
  the new lock.
- **No test changes under the new versions.**
  - Seven of the bumped packages are in this container's environment: anyio, fsspec, idna, multidict,
    s3fs, setuptools and urllib3. requests and Pygments were already at #214's versions.
  - All of `tests/` was run with those seven at #214's versions, on main `34cb015f`: 4,701 passed, 100
    skipped and 1 xfailed.
  - The 18 failures and 19 collection errors are main's environmental set. Under the old versions the
    same 37 fail the same way. They need villa's spiral modules, villa files, a villa submodule
    checkout, model checkpoints, or `gp_winner`.

## Observations for the owner (not changed)

- **Nine locked packages still have PyPI-listed advisories after #213 and #214:**

  | package | locked | advisories | what holds it |
  |---|---|---|---|
  | aiohttp | 3.10.11 | 74 | webknossos 2.5.0's `~=3.10.5` |
  | python-dotenv | 1.0.1 | 2 | webknossos 2.5.0's `~=1.0.1` |
  | zipp | 3.5.1 | 2 | webknossos 2.5.0's `~=3.5.0` |
  | cryptography | 45.0.7 | 13 | nothing found: google-auth needs `>=38.0.3` |
  | filelock | 3.24.3 | 3 | nothing found: huggingface-hub needs `>=3.10.0` |
  | virtualenv | 20.33.1 | 21 | nothing found: pre-commit needs `>=20.10.0` |
  | pillow | 12.1.1 | 72 | ML side |
  | accelerate | 1.13.0 | 2 | ML side |
  | pytorch-lightning | 2.6.1 | 1 | ML side |

  - The first three are at the newest versions webknossos 2.5.0 allows. Moving them means moving or
    dropping that webknossos.
  - cryptography, filelock and virtualenv are non-ML and look free to bump, but #214 did not bump them.
  - torch, from the PyTorch index, was not checked.
  - Re-locking cannot run here: it needs `download.pytorch.org`, which this container cannot reach.
- **Ten of the bumped packages are not in this container's environment**, so the test run did not
  exercise them: bleach, GitPython, httplib2, mistune, msgpack, nbconvert, pyasn1, soupsieve, tornado
  and werkzeug. They are notebook, Google-client and W&B dependencies.

## Verification

- **Hashes:** 75 locked files of #214's bumps against PyPI's JSON API, all equal.
- **Advisories:** PyPI's `vulnerabilities` field for every package in the lock, before and after.
- **Tests:** all of `tests/`, run in chunks of 30 files with each chunk's temporary directory removed.
  The first, single-session run filled this container's disk with test temporaries and was abandoned.
- **Doc audit:** main gains no entries over #217's baseline.
- **No independent review this round.** Nothing is changed.
