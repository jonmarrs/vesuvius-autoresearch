# Draft reply for ScrollPrize/villa#1588 (not yet posted)

Target: comment on #1588, the stale-image tracker. Not a new issue: a new issue would duplicate #1588, and
the weekly new-item slot is not needed for a reply. Every number below is bound to a file in
`reports/sampler_repro/` or to `spiral_out/` and was checked before posting. No AI sign-off.

---

Another concrete consequence, this one for `total_fg_pixels`, the metric `spiral-fitting/autoresearch.md` optimises: **on the same flat surface, the stale image and a current-source `vc_render_tifxyz` give ink counts 5.3% apart.**

The cause is #1146 (`8ae89fdcd`, 2026-07-14, "use correct isotropic scaling when group_idx > 0"). It removed a `dsScale` factor from the slice offsets (`zi * sliceStep * dsScale` became `zi * sliceStep`). Since then, `buildOffsetList` steps one level-g voxel per slice along the normal, where the 05-13 image steps one level-0 voxel. At `render_ink.py`'s `--group-idx 1 --num-slices 5` defaults, the slice stack is therefore twice as thick on a source build. `render_ink.py` max-composites that stack before scoring.

What I measured, all on one flat surface (10 windings of a PHercParis4 fit, reused, not re-flattened), with the same Python stage and scorer:

- **Same sampling, shifted slices.** The centre slice is byte-identical between the two binaries. The source build's slice 1 equals the image's slice 0, and its slice 3 equals the image's slice 4 (about a dozen of ~404 M pixels differ). So the volume is read identically and only the step differs.
- **Different ink count.** `total_fg_pixels` is 3,279,498 from the image's slices and 3,453,819 from the source build's slices, **+5.32%**. Re-scoring identical slices moves it by 59 pixels, so this is not scorer noise.
- **Deterministic reference.** The image's render is deterministic: two renders of this surface are byte-identical.

Two caveats:

- The source build I scored was #1905's head (main plus its band-prefetch change), because unpatched main was OOM-killed on this render under a 24 GB container limit. #1905 does not change how the slice offsets are computed, and its description reports byte-identical output to main.
- This is one surface. The +5.3% will vary with how much ink sits just off the surface.

I am not suggesting #1146 is wrong; isotropic spacing is the right fix. The practical point for the autoresearch loop is that a result is only comparable to baselines rendered by the same `vc_render_tifxyz` build. Until the image is refreshed, it may be worth saying which build defines the metric.
