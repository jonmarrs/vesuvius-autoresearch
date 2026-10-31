# Review label edits before adopting them

The command creates a **proposal**, with before/after images and every addition
highlighted. It does not establish better ink labels: enclosed spaces can be valid
letter counters, and filling them can erase letterforms. No CT or independent
annotation is consulted.

```bash
python scripts/preprocess_labels.py --input /data/fragment/inklabels.png \
  --out /data/reviews/fragment-holes --max-hole-pixels 4 --max-added-pixels 64
```

Open `review.md` in the new directory. White pixels are original positives, orange
pixels are proposed additions, and black pixels are background. The report links
the proposed binary image and additions-only image and lists each hole's area and
bounding box. Images retain the full source grid. `proposal.json` records exact
source PNG copies, three tool-source captures, settings, runtime versions, counts
and artifact hashes. These captures are not a complete environment snapshot.

`--dry-run` computes the same bounded proposal counts and prints JSON without
creating an output directory or bundle. Both modes read only the declared PNGs;
they do not read CT or access CUDA. Help needs only Python. Execution uses the
existing NumPy, OpenCV, Pillow and Zarr helper dependencies.

The algorithm finds connected background components. A component touching any
image edge is exterior background and cannot be filled. Other components must
have at most `--max-hole-pixels` pixels (default 16). `--connectivity 8` is the
default background connectivity; `4` can produce different proposals at diagonal
gaps. Original positives are never removed. Constant masks remain unchanged.

An optional `--region-mask eligible.png` declares eligible pixels. Every pixel in
a hole must be eligible; partly unknown holes are rejected whole. The region mask
neither clips nor creates holes. Without it, the whole image is eligible, without
asserting annotation coverage.

Limits:

- Inputs must be single-frame binary PNGs: 0/1, 0/255 or one-bit encoding. Color,
  transparency, probabilities, mixed encodings and mismatched region shapes fail.
- A source has at most 16 MiB of encoded bytes and 4,194,304 decoded pixels.
  `--max-pixels` can lower the cap. Larger inputs require a separately recorded
  crop; this command cannot infer its CT transform.
- At most `--max-added-pixels` pixels (default 4096) and 256 holes may be selected.
  Exceeding a cap fails the whole proposal. Numeric limits must be positive
  integers no larger than the global pixel cap.
- Output must be a new directory outside every source PNG folder. Existing
  outputs, aliases and image/dataset names fail. No automatically preferred
  `inklabels_refined.png` or `inklabels_filled.png` is created.

Written images are decoded and checked. Sources, code captures and output hashes
are rechecked before the final JSON and directory publication. Serialize readers
and writers, including source/code edits. A killed build can leave hidden staging
files; these are not a completed bundle. Power-loss durability is not guaranteed.

Exit 0 means a proposal or dry run completed, not that edits were approved. Input,
algorithm and publication failures exit 1; usage errors exit 2. Inspect actual
labels and independent evidence before a separate data change. If validation
targets change, re-score the incumbent before comparing candidates. Existing
targets, scores and filename-preference rules are not changed by this command.

## Migration

`--output` remains an alias for `--out` but now names a new review directory, not
an output PNG. `--alpha`, `--fill-value`, `--skip-inner` and `--skip-outer` are
retired. Villa's spiral-region functions were not ink-stroke repair tools: its
pinned inner-region function added 588 background pixels to four small marks
containing only 16 positives in a synthetic reproduction.

`scripts/refine_labels_villa.py` delegates to the same proposal command. Its bulk,
EDT/Frangi and in-place options fail before reading inputs or writing outputs.
The former fallback's equivalence and label quality were never established, and
its basename flattening could overwrite different fragments' results. Its old
Python helpers are removed; Git history preserves their implementation. 3D label
editing needs a separately reviewed workflow; a 3D input is never silently treated
as a 2D proposal.

The June cross-scroll specification already documents overfilled labels
(**89–97% ink**, against 0.057–0.079 for `inklabels.png`) being set aside. This engineering change prevents these entry points from
repeating that workflow. It does not revalidate historical data or results.
