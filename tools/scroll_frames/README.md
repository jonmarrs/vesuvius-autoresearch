# scroll-frames

**83% of segments in the Vesuvius Challenge open data ship several `.tifxyz` meshes of the
same object. 79% of those declare identical `scale` metadata for coordinate frames that
differ by up to 40x.**

```bash
pip install "scroll-frames[s3] @ git+https://github.com/jonmarrs/scroll-frames"
scrollframes list PHercParis4/20230702185753
```
```
    mesh                                       um/voxel  grid           rel. scale
    -on-20260608103018-1.129um                    1.129  -                   1.00x  <- finest
    -on-20260411134726-2.4um                      2.400  -                   2.13x
    -on-20230205180739-7.91um                     7.910  -                   7.01x
    -on-20260310170716-45.532um                  45.532  -                  40.33x

    COLLISION: all 4 meshes declare scale 0.05, but their voxel sizes span 40.3x.
    Coordinates are NOT interchangeable and the metadata does not say so.
```

Exits non-zero on a collision. Pure stdlib; `s3fs` only for the live lookup.

## The problem

Every one of those meshes says:

```json
"scale": [0.05, 0.05]
```

That is **correct in each file**. It means "one grid cell is 20 voxels *of my own scan*".
It is also indistinguishable between files whose voxel sizes differ 40-fold. The only thing
telling them apart is the scan id inside the directory name, and the voxel size appears
nowhere in `meta.json` at all.

So coordinates from two meshes of one segment look interchangeable, and are not.

Measured across the catalog: **257 of 311** segments carry multiple frames, **204** of those
are indistinguishable from their metadata, median spread **7x**, worst **40.3x**.

## Why existing auditors do not flag it

They should not. [`scroll-data-audit`](https://github.com/Bullo27/scroll-data-audit) checks
artifacts against the catalog; [`tifxyz-repair`](https://github.com/Nieuwlaar/tifxyz-repair)
checks them against VC3D's loader semantics. Every one of these files passes both, and both
tools are right to pass them. Nothing here is invalid.

The gap is a different axis: two valid artifacts describing one object, silently in
different frames. That is not a validity question, so a validity checker will never see it.

## What this does NOT give you

**A transform.** The `rel. scale` column is a ratio of stated voxel sizes and nothing more.
Two scans of one object do not share an origin or an orientation, and the segmented surfaces
may genuinely differ: on one segment we fitted a similarity between two meshes and it left a
**median residual of 81 voxels**, because the 2023 and 2026 segmentations are not the same
surface.

Scaling coordinates by that ratio and calling them converted is how a frame mismatch becomes
a permanent fudge factor. Use this to learn you are in the wrong frame. Derive the transform
separately, and verify it with something that has to peak at zero shift, such as
[placement-check](https://github.com/jonmarrs/placement-check).

## Provenance

Found the hard way. Assuming one mesh's grid mapped proportionally onto another scan's
volume produced a month of false results in
[vesuvius-autoresearch](https://github.com/jonmarrs/vesuvius-autoresearch): a ground-truth
label displaced 1766 voxels, and a published conclusion that no model could read held-out
data, when the models were reading fine.

MIT.
