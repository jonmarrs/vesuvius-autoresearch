# Spatial mask partitions and dataset inspection

These tools prepare local mask artifacts and inspect actual samples. They do
not train models, measure generalization, or verify held-out lineage. The
sampling and training implementations remain unchanged.

## Prepare a mask pair

```bash
uv run python scripts/spatial_split_mask.py \
  --mask /path/to/source_mask.png --out /path/to/new_split \
  --axis 1 --fraction 0.5 --buffer 128
```

The source is a nonempty, single-channel binary PNG encoded as 0/1 or 0/255.
`axis=0` splits Y and `axis=1` splits X. `fraction` is finite and strictly between
0 and 1; the split index is `floor(axis_length * fraction)`. `buffer` is a
nonnegative integer. Its exact width is removed from both masks. For odd widths,
the extra discarded pixel is on the high-index side; a width of three removes
one pixel before the split and two after it. Zero-width gaps are allowed.

The split and gap must fit without eliminating either side, and both retained
masks must contain positive source pixels. Invalid axes, empty sides, malformed
encodings, RGB images, and impossible gaps fail. Negative bounds never become
NumPy slices that wrap around the image.

A completed directory contains `u.png`, `v.png`, and `split.json`. U retains the
low-index region; V retains the high-index region. The manifest records source
and output hashes, Y/X shape, exact half-open gap indices, requested parameters,
positive-pixel counts, and discarded positive pixels. Both masks are read back
and compared before the pair is published. A failed write, changed source, or
appearing destination prevents completed publication. The output must be new
and source-disjoint; serialize writers and keep inputs stable.

The old `--out-u` and `--out-v` interface is retired: use `--out new_directory`
and consume its `u.png` and `v.png`. Historical commands that wrote masks into
existing fragments must migrate explicitly. The default plane/image bound is
4,194,304 pixels; `--max-pixels` can raise it for a deliberate larger job.

## Mask disjointness and CT context

`mask_pixels_disjoint: true` establishes only that the retained positive pixel
sets do not overlap. `patch_independence_verified` remains false. The actual
sampler accepts patches with partial mask coverage, and training can jitter
coordinates. A patch's CT context can cross a split even when its scored pixels
come from disjoint masks.

A real sampler regression demonstrates the distinction on a 64×256 image split
at X=96 with no gap:

| Region | Positive X indices | CT patch sampled by both |
|---|---|---|
| U | `[0, 96)` | `[64, 128)` |
| V | `[96, 256)` | `[64, 128)` |

A buffer of 128 pixels with 64-pixel patches is a particular historical recipe,
not a general certificate for other patch sizes, jitter, transforms, or teacher
history. Verify the complete CT footprints and actual training/evaluation
sampling configuration independently. No training loss masking or exact ignore
handling is added by these preparation tools. See the
[pseudo-label handoff](PSEUDO_LABEL_HANDOFF.md) for those existing limits.

## Inspect actual dataset samples

```bash
uv run python scripts/scan_dataset.py \
  --uri /path/to/fragment/surface_volume.zarr \
  --labels /path/to/fragment/inklabels.png --mask /path/to/new_split/u.png \
  --samples 1000 --patch-size 64 --num-layers 16

uv run python scripts/scan_val_dataset.py \
  --uri /path/to/fragment/surface_volume.zarr \
  --labels /path/to/fragment/inklabels.png --mask /path/to/new_split/v.png \
  --samples 1000 --patch-size 64 --num-layers 16
```

All CLI input paths are explicit. The Python compatibility functions retain
their historical fragment defaults and return report dictionaries. CLI output
is finite JSON; sampler progress and warnings go to stderr. Invalid inputs or
read failures exit nonzero without a successful report.

CT must be a local, nonempty ZYX Zarr array or a group with explicit level `0`.
Labels and mask must be binary PNGs exactly aligned to H×W; confidence-filtered
pseudo-label PNGs are not accepted as known ground truth. The requested patch
and full depth must fit. Inspection accepts uint8, uint16, or floating CT, and
requires sampled normalized CT to be finite in [0,1].

The shared inspection boundary uses the actual existing three-value dataset
sample: CT, ink target, and fiber target. It reads with `strict_reads=True`,
`jitter=False`, seed 7, no ridge/Lasagna transforms, and a private temporary
coordinate cache. It does not put caches in the source or working directory.
Truncated samples, invalid coordinates, missing requested pixels, nonfinite CT,
nonbinary targets, or changed label/mask hashes fail. CT content is not fully
hashed; only source geometry is rechecked, so keep it stable during inspection.

Reports state requested, available, and **actually sampled** counts. They inspect
up to N initial catalog entries, not a random population estimate. The default
is 1,000 samples; the hard count limit is 10,000. Mean/min/max ink counts and
threshold counts use **only pixels inside each requested mask**. The diagnostic
`masked_ct_mean_above_0_01` is a normalized intensity heuristic, not a papyrus
validity or accuracy measurement. Reports include unjittered Y/X coordinate
previews/hash, source label/mask hashes, and the number of sample footprints
extending outside the mask. These counts include repeated context occurrences,
not unique whole-volume coverage.

`scan_ink_density.py` uses the same explicit CLI with a default 2,000-sample,
**label-conditioned** catalog. Its selection differs from the two mask-conditioned
scanners. The existing sampler can fall back to a patch with no ink; the report
retains zero counts and does not promise one positive pixel. A label-conditioned
patch with no requested mask pixels fails instead of reporting misleading
statistics. Use a mask-conditioned scanner when inspecting a separate region
whose labels extend outside it.

Default plane/image bounds are 4,194,304 pixels (`--max-pixels` overrides them).
An individual requested CT patch is limited to 262,144 voxels; reduce patch size
or depth for larger requests. Scanning streams samples. These checks are local
mechanical inspection, not a whole-volume survey or a model score.

## Visualize samples

```bash
uv run python scripts/visualize_training_data.py \
  --uri /path/to/fragment/surface_volume.zarr \
  --labels /path/to/fragment/inklabels.png --mask /path/to/new_split/u.png \
  --out /path/to/new_sample_view.png --num 5 --patch-size 64 --num-layers 16
```

The visualizer uses the same validated sample boundary and plots up to the
available sample count. It keeps the depth axis when only one layer is requested.
Each row shows the patch's relative middle CT slice, masked binary labels, and
an overlay, with its actual Y/X origin. Labels outside the requested mask are
transparent. Z selection follows the existing seeded dataset; the figure does
not claim a registered global Z origin.

The output must be a new, source-disjoint PNG. It is staged and verified before
publication; failed rendering preserves prior files. The PNG `Description`
contains the same JSON sample report and hashes. CLI inputs and output are now
required; Python callers can retain the default figures directory, where the
fragment basename replaces the colliding generic volume basename. The old
`--patch_size` and `--layers` spellings remain accepted.

The figure limit is 32 samples, with the same CT patch bound. Figures are built
without a global pyplot registry. Visual inspection can reveal bad inputs;
it is not quantitative accuracy evidence. Historical studies were not rerun.
