# Local data catalogues

These commands describe existing local paths and selected binary images. They
invoke no download, training, evaluation or label producer. Choose a root and a
new output directory; keep sources stable and serialize writers while a command
runs. Operational errors return nonzero and do not publish a partial bundle.

## Metadata inventory

```bash
.venv/bin/python scripts/generate_manifest.py --root local_data --out reports/my_inventory
```

The bundle contains `inventory.md` and `inventory.json`. Every observed entry is
included, even a small directory or a file directly under the root. Totals use
regular-file apparent bytes (logical sizes), not physical disk allocation.
Sparse files therefore contribute their logical size, and hardlinks count once
per pathname. Symlink targets are never traversed; special-file contents are
never read. The root must be a real directory, not a symlink.

JSON records relative paths, entry kinds, stat metadata, resolved root, scan
limits, top-level summaries and a canonical metadata SHA-256. It also records
the Markdown artifact's byte count and SHA-256. This scan does not hash file
content, inspect CT/labels, infer scroll or division identity from a name, or
assess ground truth, coverage, readiness or eligibility. A directory named
`Scroll_2_div_10_1GB` gets the same descriptive treatment as any other directory.
An empty root yields an explicit zero-entry inventory.

The default and hard maximum limits are 100,000 entries and 32 directory levels;
`--max-entries` and `--max-depth` can lower them. The root itself is not counted
as an entry; immediate child directories have depth one. Exceeding a limit,
encountering an inaccessible entry, or detecting changed metadata aborts the
whole report. Select a smaller explicit root instead of treating a partial scan
as a total. The legacy Python `get_dir_size` helper uses the same bounded scan
and returns only regular-file apparent bytes.

## Binary-label overview

```bash
.venv/bin/python scripts/generate_training_atlas.py --root local_data --out reports/my_label_atlas --limit 12 --max-pixels 4194304
```

Candidates are immediate regular child directories with an `inklabels.png`
entry. Selection takes the first names in lexicographic order, up to `--limit`;
it is not a random sample or a population estimate. The bundle records discovered,
selected and uninspected candidate counts. Invalid selected sources fail the
command; invalid sources outside the selection remain uninspected. Directory
symlinks are excluded. Labels and optional masks must be regular files, not
symlinks or special files.

Each selected label must be a nonempty 2D PNG in mode `1` or `L`, using either
binary 0/1 or 0/255 values. Both encodings render as black/white; mixed 1/255,
arbitrary grayscale, RGB, RGBA, palette and 16-bit modes are rejected. Zero ink
is a valid observed count. A present `mask.png` must satisfy the same binary
contract, match the label's YX shape, and contain positive pixels. A missing
mask is explicitly `absent`. Matching array dimensions do not establish CT
registration or independent training contexts.

JSON records original dimensions, exact full-array ink counts, optional mask
support and ink inside/outside the mask, plus each decoded source's path, exact
byte count, SHA-256 and stat signature. It also records source-list metadata,
selection, limits, thumbnail recipe, verified canvas dimensions and output
PNG/SVG hashes. CT data and label lineage are not inspected. A matching binary
encoding is not evidence that a label is human ground truth.

The bundle contains `atlas.png`, `atlas.svg` and `atlas.json`. PNG/SVG embed the
same scope, root, selection and selected source hashes as JSON. Nearest-neighbor
thumbnails preserve aspect ratio with a maximum side of 512 pixels; resampling
can omit features and does not supply the counts. Up to three panels occupy
each row, including the single-fragment case. The canvas uses a white background
and explicit text colors without changing caller plotting state. Headers align
at the top of each panel; names occupy at most two caption lines. Long names are
truncated with `...` and flagged in JSON, which retains the full name.

Defaults: 12 selected fragments, 4,194,304 pixels per PNG, and 4,096 immediate
root entries. Hard maxima: 24 fragments, 16,777,216 pixels per PNG, 4,096 root
entries and 16 MiB per source PNG. Pixel/byte checks precede image decode; Pillow's
decompression-bomb protection remains enabled. Limits can be lowered with
`--limit`, `--max-pixels` and `--max-entries`; choose an explicitly prepared
smaller crop when a source exceeds them. A missing root or no label candidates
is an error, rather than an empty successful atlas.

## Publication and migration

Omitting `--out` chooses a new timestamped `data_inventory` or `label_atlas`
directory under `reports` relative to the working directory. Explicit absolute
inputs and outputs also work when invoked outside the checkout. Outputs must
be new and disjoint from the source root; existing files, directories, valid or
broken symlinks, and ancestor/descendant aliases are rejected.

All bundle files are staged and read back before a directory rename publishes
them together. Metadata is rescanned before publication; selected PNG bytes are
rehash-checked as well. Failed reads, rendering, JSON writes, source changes or
an appearing destination remove staging and preserve prior artifacts. This is
the existing serialized local-writer contract, not an adversarial filesystem
snapshot or a concurrent-writer API. Metadata-only inventories cannot detect
content edits that preserve stat metadata. Source copies are not retained; keep
the source files if later independent revalidation is needed.

The generators no longer overwrite root `local_data_manifest.md` or fixed
`training_data_atlas` images. Existing assets remain historical and are not
consumed by these commands. The committed
[historical manifest](local_data_manifest.md) preserves unverified old rows.
For actual dataset sample inspection or spatial partitions, use
[Spatial partitions and inspection](SPATIAL_PARTITIONS_AND_INSPECTION.md).
