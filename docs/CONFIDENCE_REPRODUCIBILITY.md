# Confidence and ink agreement: analysis version 2

This CPU analysis tests the registered association between detector confidence
and ink agreement across three seeds at all three registered volume binnings.
It does not measure ink correctness or whether thresholding improves a map.
See the [registration](preregistration/2026-09-13_does_confidence_predict_reproducibility.md)
and the [historical follow-up](../reports/confidence_predicts_but_thresholding_does_not_help.md).

```bash
python scripts/measure_confidence_vs_reproducibility.py \
    --spiral-out /path/to/spiral_out --arms curbase_s1 curbase_s2 curbase_s3 \
    --json /path/to/reports/confidence-v2.json
```

The three distinct arm names resolve to `outer_<name>` directories. Each needs:

- `meshes/concat/w120-129_flat/{x,y,z}.tif`: matching 2D coordinate grids;
- `ink_metric/metrics.json`: the original complete single-strip score;
- `ink_metric_prob/metrics.json`: the complete re-score with probabilities kept;
- `ink_metric_prob/predictions/*_flat_prob.npy`: exactly one whole-strip map,
  saved with `INK_METRIC_KEEP_PROB=1`;
- the re-score's matching `<strip>_mask.png`, or contiguous
  `<strip>_mask.000.png`, `.001.png`, ... tiles in the same predictions directory.

Saved masks determine which pixels count as ink; re-thresholding quantized
float16 probabilities could change that set. Probability dimensions must be
exactly ten times the coordinate grid on both axes, with floating finite values
in [0, 1]. Masks must be scalar binary 0/1 or 0/255 images. Extra/ambiguous maps,
unrelated/missing mask tiles and incompatible shapes fail with a diagnostic.

## Measurement and gates

The loader sums probabilities **only at saved ink pixels**, and separately
counts those pixels in each 10×10 cell. It accumulates column groups in global
strip coordinates, preserving cells cut by a PNG tile or processing-block edge.
Each arm is loaded once and reused at all binnings. The shared volume axis comes
from the first requested arm's valid coordinates, as before.

Both metrics files must contain integer summary counts consistent with their
single strip, and total pixels must match the paired artifacts. The re-score's
foreground count must equal its saved masks. Its difference from the original
foreground count must be at most **0.1% of the original**, including the boundary;
zero original ink passes only with zero re-scored ink. A failed gate or missing
source exits 1 before replacing a report. Count agreement alone does not prove
pixelwise equivalence, independent seeds, model identity or spatial correctness.

At each of 48×128, 96×256 and 192×512 bins, the statistic is the difference in
mean bin confidence between unanimous and lone-arm bins. Each bin confidence is
its summed ink-pixel probability divided by its ink count across arms. Bins are
weighted equally within the two cohorts, matching the registered bin-level
shuffle comparison. Each cohort needs at least 30 bins; smaller cohorts produce
`INDETERMINATE` with null statistics and a reason.

The seed-0, 1,000-shuffle two-sided test now uses `(exceedances + 1) / 1001`;
zero Monte Carlo p-values are not reported. Differences within 1e-14 are treated
as ties when counting exceedances. The registered difference >0.05 and p<0.05
rule must hold at all three binnings for a positive association. A significant
negative association also needs all three; mixed directions or partial support
are `BIN-DEPENDENT`. No detected effect does not establish absence of an effect.
Inference beyond three seeds on one ROI, spatial exchangeability and threshold
selection are not validated by this implementation review.

## Reports and resource use

JSON has `analysis_version: 2`, `statistic_kind`, ordered arms, shared axis,
binnings, shuffle method, per-arm validity gates and metrics SHA-256 captures,
observed source file states, per-binning status/statistics, verdict and reason.
It records that ink correctness and thresholding benefit were not tested.
An underpowered analysis writes a finite JSON report and exits 1; a complete
comparison exits 0 regardless of its effect direction. Usage errors exit 2.

Reports must be separate from arm directories and declared input files, including
resolved paths and inode aliases. Publication is atomic and retains the mode of
an existing report. Source device/inode/size/mtime/ctime states are checked around
loading and before publication. Those observations detect ordinary changes;
they are not content hashes of every large source or a shared immutable snapshot.
Keep inputs stable and serialize writers.

The probability NPY remains memory mapped. Processing blocks hold at most
8,388,608 pixels and 5,120 columns; mask headers are checked before decoding
tiles of at most 134,217,728 pixels. Coordinate grids are limited to 16,777,216
cells. These bounds are not an RSS limit: TIFF grids, a decoded mask tile,
working arrays and all three reduced arms also occupy host memory. Full-strip
runtime and peak memory were not measured in this review.

Version 1 multiplied the **whole-cell** mean probability by the cell's ink
count, so background affected the quantity labeled mean ink confidence. Its
historical JSON and numbers remain preserved. Version 2 corrects that aggregation,
enforces the declared count gate and changes p-value handling and verdict text.
The old experiment must be re-run on its original artifacts before its numbers
or conclusion can be presented as version-2 evidence. No such re-run is claimed.
