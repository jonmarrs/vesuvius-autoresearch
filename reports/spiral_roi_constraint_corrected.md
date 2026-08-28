# The z-ROI constraint was sized against a pool the default fit never loads

**2026-08-28.** Corrects the "roughly a third of the scroll" figure used throughout this session.

## What changed

`scripts/size_spiral_roi.py` sized the affordable z window against the **47.48 GiB** resident-pool
payload, of which **32.58 GiB (69%) is the surf-SDT store**. That gave 14 to 16 GiB of pool budget
buying 2,400 to 2,688 z slices, about a third of the occupied range.

The SDT is **not loaded by the default configuration**. `input_use_surf_sdt` is `False` and the
default `dense_spacing_mode` is `winding_model`, so `_phase_bundle_enabled()` is `False`. This
follows directly from the error retracted in `spiral_published_dataset_cannot_run_default_mode.md`:
having wrongly concluded the fit *required* the SDT, I also sized the ROI as though it were resident.

Measured from the pools' own `brick_coords.npy`, counting channels:

| pool | bricks | channels | full-range size | loaded by default |
|---|---:|---:|---:|---|
| normals (nx+ny, paired) | 166,243 | 2 | 10.15 GiB | yes |
| grad_mag | 155,809 | 1 | 4.75 GiB | yes |
| surf_sdt | 1,067,536 | 1 | 32.58 GiB | **no** |

**Active pools total 14.90 GiB for the entire z range**, leaving about 9.09 GiB of a 23.99 GiB card.

## What this does and does not establish

**Does:** the resident pools are no longer the binding constraint on z extent. The full range fits.
Note the two active pools are `respool_g4` with `grid_z` 149, against the SDT's `g1` and `grid_z`
297, so they are coarser and far smaller than the headline payload suggested.

**Does not:** prove a full-range fit runs. Model parameters, activations and optimizer state share
the remaining 9.09 GiB, and the per-step sample counts scale with the z range by design
(`scale_counts_for_z_range`), so a wider range costs proportionally more activation memory. Only a
run settles it.

**Independent limit, unchanged:** patches were fetched only for the ROI, so a fit is bounded by
what was downloaded (working z 13056 to 18432) regardless of VRAM. Widening the fit means fetching
more patches first.

## Why this is recorded rather than quietly edited

The "third of the scroll" figure was stated repeatedly, including in a merge commit message. It was
arithmetic performed correctly on a premise that was wrong, which is why re-checking the arithmetic
would never have caught it. The premise came from reading a default off a `.get()` fallback instead
of instantiating the config.
