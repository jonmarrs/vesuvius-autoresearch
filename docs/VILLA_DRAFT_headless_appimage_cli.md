# Headless AppImage CLI instructions — prepared PR

Candidate: [Villa #2153](https://github.com/ScrollPrize/villa/issues/2153).
Branch `docs/headless-appimage-cli`, commit
`d119561f3fb89fceae579bcf2e8671fb6d7e2c9a`, on Villa `e2254ebe`.
The patch and validation are recorded in
[the opportunity review](../reports/villa_opportunities_2026-10-23.md).

---

**In one sentence:** Linux users can launch the release's CLI tools on a
headless server using the required host libraries and bundled loader.

**One real example:** On Debian 13 x86_64, the current release
`VC3D-e2254eb-2026-10-22-linux-x86_64.AppImage` was extracted with
`--appimage-extract`. With no display configured, calling its
`usr/bin/vc_render_tifxyz --help` directly segfaulted; calling
`AppRun vc_render_tifxyz --help` printed help and exited 0.

**Before:** The main installation page says all dependencies are bundled.
The packaging notes list the host libraries, but give no reusable extracted
CLI command or explanation that direct binary invocation bypasses the
bundled loader. #2153 reports both obstacles while rendering scroll data.

**After this PR:** The installation page states the host-library requirement.
The packaging notes give a Debian/Ubuntu runtime package command, extraction
and `AppRun` commands, and explain why the extracted binary must be launched
through the wrapper.

**Proof:** Same downloaded release and environment for both launch paths:

| Invocation | Result |
| --- | --- |
| `./squashfs-root/usr/bin/vc_render_tifxyz --help` | SIGSEGV; shell status 139; no output |
| `./squashfs-root/AppRun vc_render_tifxyz --help` | Help printed, exit 0 |
| `APPIMAGE_EXTRACT_AND_RUN=1 ./VC3D.AppImage vc_render_tifxyz --help` | Help printed, exit 0 |
| `./squashfs-root/AppRun vc_tifxyz_trim` | Usage printed, expected exit 1 |

**Why / where this is useful:** Our spiral-render reproduction needs the
published VC command-line tools. The AppImage provides newer tools than the
old Docker image, and #2153 documents a real headless render needing this
launch route. This change makes that route explicit without changing the
packaging or renderer.

- [ ] I personally verified that the example and proof above were produced
      by this PR on the stated data.

## Details

Two documentation files, +29/-1 lines. The launch behavior is already in the
release; this patch documents it. Startup validation used Debian 13 x86_64
with the host libraries already present, `DISPLAY` and `WAYLAND_DISPLAY`
unset, and `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` for both paths. The
release SHA-256 is
`46365113764e2b3cda17565159deb808dd1033a00259479ddfb0bfeae29ce45d`.

The package list comes from the existing prerequisites and Linux CI. No
packages were installed, no fresh Ubuntu/container installation was tested,
and this check rendered no scroll data. The original real-data render is
reported by @evelynrook in #2153; the measured comparison here is CLI startup.

The human attestation remains unchecked. Captured output is in
`reports/evidence/villa_headless_cli_2026-10-23.json`.
