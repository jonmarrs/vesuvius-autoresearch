# Villa engineering opportunities — 2026-10-23 UTC

**Further review:** an [audit of all 853 published fiber annotation files](fiber_reference_provenance_2026-10-23.md)
supports an eight-line documentation clarification about tracer-generated
references, related to [#2264](https://github.com/ScrollPrize/villa/issues/2264).
The patch and PR draft are prepared locally; publication is still blocked by
the previously observed GitHub integration permissions. The existing native
retry fix remains the first unpublished code contribution to pursue.

**Follow-up:** [#1482](https://github.com/ScrollPrize/villa/issues/1482) is a
live code candidate after its previous fix expired unmerged. A bounded retry
fix, nine new tests and a real-mesh rejection probe are now prepared;
see [the focused review](villa_native_retry_cycle_2026-10-23.md).
The TIFF resume bug in #1404 was also checked and is already fixed by merged
#1695; the Windows seed failure in #1594 is already fixed by merged #1595.

One new contribution is published as [Villa #2259](https://github.com/ScrollPrize/villa/pull/2259):
the headless AppImage CLI instructions for
[#2153](https://github.com/ScrollPrize/villa/issues/2153). It is a small
documentation correction with an independently reproduced startup failure.
The existing seeding and SQLite PRs remain the first upstream follow-ups.

## Verified queue

| Issue / PR | Current evidence | Action |
| --- | --- | --- |
| [#2141](https://github.com/ScrollPrize/villa/pull/2141), SQLite track reader | Open. Both maintainer findings addressed at `19575a45`; five local tests pass. | Upstream maintainer review and merge. |
| [#2258](https://github.com/ScrollPrize/villa/pull/2258), fractional fiber planes | Open. Twenty local tests pass; default-spacing arrays match on three real scroll masks. Python CI remains in progress when checked. | Finish upstream checks and maintainer merge. |
| [#2153](https://github.com/ScrollPrize/villa/issues/2153), headless AppImage | Open; no earlier matching PR found by issue number or AppRun/headless terms. The installation page claims all dependencies are bundled. | Published +29/-1-line documentation fix as [#2259](https://github.com/ScrollPrize/villa/pull/2259); awaiting checks and maintainer merge. |
| [#2027](https://github.com/ScrollPrize/villa/issues/2027), spiral angle precision | Already fixed in [#2028](https://github.com/ScrollPrize/villa/pull/2028), merged October 21; current source uses `float_hi`. | No duplicate PR. |
| [#2186](https://github.com/ScrollPrize/villa/issues/2186), recompression data loss | Active fix [#2199](https://github.com/ScrollPrize/villa/pull/2199). | No duplicate PR. |
| [#2195](https://github.com/ScrollPrize/villa/issues/2195), slow patch finding | Active fix [#2197](https://github.com/ScrollPrize/villa/pull/2197). | No duplicate PR. |
| [#2104](https://github.com/ScrollPrize/villa/issues/2104), bounded trace growth | Active fix [#2133](https://github.com/ScrollPrize/villa/pull/2133). | No duplicate PR. |
| [#1360](https://github.com/ScrollPrize/villa/issues/1360), inference failures | Merged [#1827](https://github.com/ScrollPrize/villa/pull/1827) reports the inference error. Current inference, blending and structure-tensor CLI paths return failure on the checked errors/empty result. | No duplicate patch; checked source, no new full inference run. |
| [#1674](https://github.com/ScrollPrize/villa/issues/1674), local Zarr indices | A reproducer in the issue comments found the probed coordinates correct; the sparse local mirror covered another region. | Do not patch coordinate mapping on this report alone. |
| [#1673](https://github.com/ScrollPrize/villa/issues/1673), Zarr render crash | Later issue comments reproduce successful Linux/macOS current releases and identify the stale container's missing June fix. | No current crash established here; no renderer patch. |
| [#2240](https://github.com/ScrollPrize/villa/issues/2240), Zarr merge compatibility | Active [#2244](https://github.com/ScrollPrize/villa/pull/2244). | No duplicate PR. |
| [#1490](https://github.com/ScrollPrize/villa/issues/1490), auxiliary targets | Active [#2252](https://github.com/ScrollPrize/villa/pull/2252). | No duplicate PR. |
| [#2072](https://github.com/ScrollPrize/villa/issues/2072), sheet-tracer area scale | Active [#2073](https://github.com/ScrollPrize/villa/pull/2073). | No duplicate PR. |
| [#1333](https://github.com/ScrollPrize/villa/issues/1333), Volume hint | Active [#2129](https://github.com/ScrollPrize/villa/pull/2129). | No duplicate PR. |

Other searched reports, including winding consistency, cached HTTP 404s and
Copy block-edge seams, also have proposed fixes. Published-data issues such
as #1522 and #1654 still require changes to published artifacts; an unrelated
Villa code patch would not resolve them.

Sources were current GitHub issues and PR searches, plus Villa `origin/main`
at `e2254ebe0168a232e5ba7b94997c749b4e6a4544`, rather than the older local
roadmap. Search results are a dated check, not a guarantee that no work exists
on an unpublished branch. No messages were sent to issue authors.

## Published headless CLI correction

The main installation page calls the AppImage self-contained with all
dependencies bundled, while the packaging notes and release workflow
explicitly leave graphics and font libraries to the host. The packaging
notes also omit an explicit extracted `AppRun <tool>` example. Running the
binary directly bypasses its bundled glibc/loader setup.

The reviewed patch corrects the installation claim and adds runtime package and
extraction instructions. It changes no runtime code. It is committed at
`d119561f3fb89fceae579bcf2e8671fb6d7e2c9a` on local Villa branch
`docs/headless-appimage-cli`, worktree `/workspace/villa-headless-cli`.
The published PR diff matches the reviewed patch. The evidence is preserved
in [Autoresearch #194](https://github.com/jonmarrs/vesuvius-autoresearch/pull/194).

- [Portable patch](../docs/villa_pr_headless_appimage_cli.patch)
- [Prepared PR description](../docs/VILLA_DRAFT_headless_appimage_cli.md)
- [Captured startup output](evidence/villa_headless_cli_2026-10-23.json)

## Measured validation

Downloaded the current release asset
`VC3D-e2254eb-2026-10-22-linux-x86_64.AppImage` (128,809,464 bytes) and checked
its SHA-256 against GitHub's release digest:
`46365113764e2b3cda17565159deb808dd1033a00259479ddfb0bfeae29ce45d`.

On Debian 13 x86_64, with display variables unset and both paths limited to
one OpenBLAS/OpenMP thread:

```sh
./VC3D.AppImage --appimage-extract
./squashfs-root/usr/bin/vc_render_tifxyz --help
# SIGSEGV (Python returncode -11; shell status 139), no output
./squashfs-root/AppRun vc_render_tifxyz --help
# help printed, exit 0
APPIMAGE_EXTRACT_AND_RUN=1 ./VC3D.AppImage vc_render_tifxyz --help
# help printed, exit 0
./squashfs-root/AppRun vc_tifxyz_trim
# usage printed, expected exit 1
```

An initial unrestricted direct invocation hit an OpenBLAS thread-startup
failure first; the comparison above sets the same one-thread environment
for every command to remove that confound.

The documented package list matches the existing prerequisite list and
Linux CI packages. The host already had the libraries; package installation
and a fresh minimal Ubuntu/container were not tested. No scroll render or
GUI test was run. This is evidence about the published CLI launch route,
not rendering quality or a change in runtime behavior. The original real
rendering report remains attributed to @evelynrook in #2153.

`git diff --check`, reverse application of the portable patch and `bash -n`
on `AppRun` pass. The Autoresearch smoke command also passed using the
existing cached interpreter/packages:

```sh
VILLA_REVIEW_ROOT=/workspace/villa-upstream-review AGENTS_AGENT_MODE=1 \
OMP_NUM_THREADS=2 MKL_NUM_THREADS=2 \
/workspace/.local/share/uv/python/cpython-3.10.21-linux-x86_64-gnu/bin/python3.10 \
  /workspace/villa-review-evidence/run_python.py scripts/smoke_test.py
# 8/11 passed, 3 skipped, 0 failed in 8.1s
```

The skipped checks need the absent training data or unavailable bg2
augmentation entry point. No packages were installed and the production
Villa pin, registered research studies and loop state were not changed.
