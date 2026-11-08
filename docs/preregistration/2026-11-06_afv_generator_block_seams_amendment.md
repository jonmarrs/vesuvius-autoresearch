# Amendment to the block-seams registration: the patch to propose keeps ends at the zone's border

**Written 2026-11-06 at 19:10 PST, while the held-out chain ran.** Only the one-block arm of the first cube,
`s3_00994_00494_01994_512`, had finished (main: 494 fibers written; ERLpen 17.63 at τ = 2 and 48.47 at τ = 4). No
eight-block row and no patched row of any held-out cube had been seen. The registration
(`2026-11-06_afv_generator_block_seams.md`), its script, its patch and its decision rule are unchanged, and the record
will measure the registered patch.

## What changes

The registered patch keeps a cut end only at the border of the volume. In VC3D a zone usually lies inside a larger
volume. Its outer blocks then read 32 voxels past the zone, and the registered patch trims the ends at those borders
too, though no other block reads past them to supply the ends. The amended patch,
`repro/fibers/villa_fiber_generator_trim_cut_ends_zone_7e6b82164.patch` (also on villa main `7e6b82164`), replaces
the volume's shape with the box the zone's blocks read together: the zone and its margin, clipped to the volume. That
is the box the CLI already gives `ExteriorBlack`. The amended patch therefore trims only at borders another block reads
past, and leaves a one-block zone unchanged. Its villa test adds that case, and both corners where an end lies beside
the zone's own border.

## Why the registered test still decides it

Every held-out cube is run as a whole volume, so the zone's box is the volume and the two patches trim alike.
`tests/test_afv_generator_block_seams_amendment.py` runs both patches' `trim_cut_ends` on 1,000 random blocks. Their
output is identical on every one, and over 900 had something trimmed. The test also checks that a one-block zone
inside a larger volume is left alone by the amended patch and trimmed by the registered one, and it pins the
registered patch's hash.

## What it does not cover

The held-out test does not measure the zone-inside-a-volume case. There the registered patch removes only points 16
to 32 voxels outside the zone. Inside the zone the two patches differ only through the length thresholds
(`MIN_LENGTH` in the trim, `--min-length` in cleanup) and the catalogue's decisions on the shortened copies.
