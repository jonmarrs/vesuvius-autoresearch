# Prepare detector fragments

The maintained conversion command prepares the TimeSformer/ResEnc detector's
`layers/NN.tif`, fragment mask and ink-label layout. It runs on the CPU with
NumPy, OpenCV and Pillow; it imports neither Torch nor the detector training
package. It does not prepare the root research loop's Zarr data.

Check an existing fragment before training:

```bash
python repro/gp_winner/convert_fragment.py --frag FragX \
  --dst-root /path/to/converted_fragments --z-start 17 --z-end 43 --check
```

`--dry-run` is an alias for `--check`. This checks the converted images and,
when present, their completion manifest. It reads no original source images,
creates no output directories and uses no CUDA. Exit 0 means reusable; exit 2
means conversion or repair is needed. Argument errors also exit 2. This check
does not predict whether a subsequent conversion will succeed.

Convert or rebuild one fragment:

```bash
python repro/gp_winner/convert_fragment.py --frag FragX \
  --src-root /path/to/raw_fragments --dst-root /path/to/converted_fragments \
  --z-start 17 --z-end 43
```

The source fragment must contain `surface_volume/17.tif` through `42.tif`,
`inklabels.png`, and `mask.png`. Every image must be a single grayscale plane
with the same height and width. TIFF layers must be uint16; labels and mask must
be uint8. Already converted uint8 layers are refused: dividing them by 256 again
would erase their signal. The scale remains **uint16 // 256**, with the detector's
existing clipping to 200 applied later by its loader. Labels are copied byte for
byte; grayscale soft labels are preserved.

Each image is limited to 167,772,160 pixels, enough for the 14830 × 9506
PHercParis2Fr143 fragment and below Pillow's own refusal. `--max-pixels` can
lower that limit.
Each encoded source is limited to `4 * max_pixels + 1 MiB`; a conversion selects
at most 512 layers. Processing and source rechecks proceed one file at a time,
so memory scales with a plane, not with the complete volume. There is no measured
peak-memory guarantee or large-fragment performance benchmark for this change.

The converter stages the complete fragment next to its destination, checks
encoded TIFF values and file readbacks, then rechecks all selected source bytes
and staged output hashes before publication. `conversion.json` records the
fragment ID, layer range, shape, scale, and input/output byte hashes. A failed
conversion preserves the previous fragment. A rebuild replaces the converter's
entire managed generation, so obsolete layer files are removed together.

The destination fragment may contain only `layers/NN.tif`, the canonical
`<id>_inklabels.png`, `<id>_mask.png`, and `conversion.json`, plus the hidden
`.<name>.part` files an interrupted run of the previous converter left beside
them, which a rebuild removes with the rest of the generation. Unrelated files,
annotations, alternate labels and symlinks block replacement; choose a new
destination root to keep those files. Source and destination fragments must be
disjoint. IDs must be single directory names.

Readers and writers must be serialized. Publishing over an existing directory
uses two renames, with rollback on caught failures; it is not a simultaneous
directory swap or a power-loss durability guarantee. If rollback fails, the
error names the retained hidden directory ending in `-previous` for manual
recovery. One invocation converts one fragment. The detector's multi-fragment
`reproduce` command can finish one fragment before a later fragment fails.

Replacements preserve the existing fragment, layer-directory and output-file
permissions, including read-only directories. Cleanup adjusts permissions only
inside disposable private workspaces; a backup retained after rollback failure
keeps its recovery permissions.
Generations are renamed within the same parent, so replacing a read-only root
does not need permission to change that directory's parent link.

`detector reproduce` now uses this same packaged implementation without adding
an ambient `convert_fragment` module to Python's import path. It validates the
requested images' bit depth and geometry before reusing them. A present
completion manifest must cover the requested range and match those output bytes;
a damaged or stale manifest blocks reuse, and an image that cannot be decoded
reads as `NEEDS_CONVERSION`. Existing native/legacy layouts with one
`*inklabels.*` file remain usable after image checks, and are reported as
**legacy image checks; no source provenance**. Hidden files are not labels, as
for the loader.

`READY` verifies the prepared files at check time. It does not reread the original
sources, prove that they are still current, authenticate a manifest, prove
physical registration or annotation quality, or establish a held-out split.
Rerun conversion explicitly to incorporate changed raw inputs. Training and
validation IDs must be distinct before `reproduce` starts converting them.
