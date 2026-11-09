# Fiber dataset acquisition: design and architecture review

Reviewed the benchmark's public dataset downloader on main
`bcd8077266ba6da904ab89eff0d7a0e39f3bec5c`. This follows the scoring-input and
probability-cache reviews; it does not regenerate study data or benchmark results.

## Findings and repairs

- **Annotation selection depended on HTML link order (P2).** With versions 1, 2
  and 10 listed, the old downloader saved version 1, then skipped the others
  because its unversioned local filename was nonempty. The initial regression
  failed before repair. A separate `FetchPlan` now groups recognized sources by
  cube and chooses the highest numeric version. Duplicate links are deduplicated;
  different filenames tied for the selected version are refused as ambiguous.
  HTML parsing supports single/double quotes, case-insensitive tags/attributes
  and comments. Multi-digit scroll identities now match the request validator.
- **Destination checks happened too late or not at all (P2).** An existing
  nonempty semantic-label symlink was silently accepted, after earlier files
  had already been downloaded. This also failed before repair. The complete
  selected batch now reserves all NML/image/semantic destinations using the
  shared path checker, before any transfer. Symlinks, directories, special files
  and aliases are refused. The plan is rechecked before transfers, after opening
  responses and before publication. A bad later cube cannot trigger earlier
  dataset writes during initial preflight.
- **A truncated listing could masquerade as a complete selection (P2).** Review
  reproduced a short listing containing one valid cube link under a larger
  declared Content-Length; the old path downloaded it and returned success.
  Listing reads are now capped at 2 MiB and checked against a supplied byte count
  before planning. Empty/unrecognized listings also fail explicitly.
- **Reuse and recovery were opaque.** Existing nonempty regular files remain
  reusable by default, now with a source/content-unverified message. `--refresh`
  deliberately replaces each selected cube's NML, CT and semantic labels.
  `--dry-run` lists remote sources, local destinations and DOWNLOAD/REUSE/REPLACE
  actions while requesting only the directory listing and creating no data
  directory. It can be combined with refresh to preview replacements.

## Architecture and behavior

`dataset_fetch.py` separates HTML/source selection and whole-batch path planning
from CLI network I/O. Only recognized flat annotation names become remote
sources; arbitrary absolute/parent links are ignored. The existing dataset `s1a`
to `s1` convention and local filenames are retained. Plans are deterministic and
side-effect free. No new dependencies or changes to the shared path/atomic-write
helpers were needed.

Transfers retain 60-second socket timeouts, empty/byte-count checks, sibling
temporary files and existing destination permissions. An interrupted or invalid
transfer preserves its previous destination and cleans up its temporary file.
Publication is per file: completed earlier files remain updated if a later file
fails. Directory/path checks are not locks; serialize writers and keep paths
stable. Annotation version numbers do not prove annotation quality or CT/label
alignment. Without remote checksums or a complete historical manifest, fetch
cannot attest existing bytes or pin a remote dataset snapshot. It does not decode
TIFF/NML contents. See [fiber tracing](FIBER_TRACING.md) for CLI details.

## Verification

Python 3.10.21, Torch 2.9.1+cpu, NumPy 2.2.6, with Villa pinned at
`ccb431818fa68059138f2c964ae299fc474ff116`.

- Initial regressions: **2 failed in 1.02s** before the repairs. The additional
  short-listing regression failed during review (**1 failed in 1.16s**) before
  its byte-count guard was added.
- Final affected curated selection: **297 passed in 30.65s**, across 8/192
  modules. It includes 23 fetch cases plus benchmark/cache/NML/file-mode and
  suite-registration contracts. Tests cover numeric version order, aliases and
  duplicate/ambiguous links, single-quoted HTML, full-batch destination checks,
  dry-run/reuse/refresh behavior, preserved permissions, incomplete/invalid
  transfers/listings and a destination replaced during transfer. Network payloads
  in the tests are synthetic; atomic file and path behavior is real.
- A live read-only CLI preview on 2026-11-09 recognized **11 cubes and 33
  DOWNLOAD actions**, with no data directory created. The public listing then
  held one annotation per cube (six version 0, four version 1, one version 3);
  competing versions are covered by fixtures, not claimed as a live-server issue.
- Required smoke: **8/11 passed, 3 skipped, 0 failed in 14.3s**. Local training
  data and an optional batchgenerators transform were unavailable. Available
  import/model/augmentation paths passed, including 288/288 checkpoint tensors.
- Ruff lint/format and scoped Mypy passed all four changed Python files. Exact
  commands and captured output are in the PR.

No full curated suite, full live NML/TIFF payload download, CUDA/RTX 4090 workload,
new scientific measurement or prize-filing update was performed. Existing study
files, historical reports, inference/scoring recipes and research claims were
not changed.
