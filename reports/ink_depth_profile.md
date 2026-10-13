# The depth band was in the wrong slice numbers, and the loop's windows already showed the surface (finding 87)

**2026-10-13.** A read-only check, **not pre-registered**: step 1 of the depth-band plan
(`docs/DESIGN_ARCHITECTURE_REVIEW_2026-10-13_LOSSES_AND_UPDATE.md`), which needed the GPU host and had not been run.
Script: `scripts/ink_depth_profile.py` at `5e0d4399`; output: `reports/ink_depth_profile.json`.

## Result

**The fragments are 33 slices deep, not 65.** Both zarrs (`PHercParis2Fr47` and `PHercParis2Fr143`, level 0) have
**33** slices. Matched against the layer TIFFs they were built from, zarr slice 0 is surface-volume **layer 16**, so
the zarr holds layers 16–48. Each TIFF matches its slice with a mean absolute difference of at most **0.438** grey
levels, while the next-best slice differs by at least **1.814**.

**So `depth_band: [17, 43]` named the detector's layer files, not the loader's slices.** The detector reads
`layers/17.tif`–`42.tif`, which are zarr slices **[1, 27]** (half-open: 1–26). The labeled dataset indexes the zarr,
and since #52 it refuses a band that runs past the volume. On `main` at `2351651d`, `build_validation_dataset` raised
`depth_band [17, 43] lies outside local_data/PHercParis2Fr143/surface_volume.zarr (33 slices)`. Every loop cycle, and
the incumbent's re-score, would have stopped there. This PR sets the band to `[1, 27]` (protocol
`seeded-sample-400-v2+z1-27`), and `tests/test_config_depth_band_fits_fragments.py` fails on the old band.

**Under protocol v2 (no band), every validation window already contained layer 32.** A read is **24** slices
(`num_layers` 16 plus a 4-slice margin each side) starting at z0 in 0–9. Validation uses the middle 16, so its windows
run from zarr [4, 20) to [13, 29):

| v2 window positions | validation (10) | training (80) |
|---|---:|---:|
| contain zarr 16 (layer 32, the surface volume's middle) | **10 of 10** | **79 of 80** |
| lie entirely inside the detector's band | 8 of 10 | 64 of 80 |
| fewest of the 16 slices inside the band | 14 | 11 |

The review's figures (38% of validation windows contain slice 32, 26% lie inside the band) assumed a 65-slice volume;
on these volumes they are 10 of 10 and 8 of 10. The corrected band narrows validation's start positions from 0–9 to
0–7; the patches' positions in the plane do not change.

**Ink contrast is weak at every depth.** Per slice, the ROC AUC of intensity (5×5 px box mean) for ink against
non-ink pixels inside the mask, 100,000 of each:

| fragment | AUC range over the 33 slices | furthest from 0.5 | brightest slice | validation windows containing the furthest |
|---|---|---|---|---:|
| Fr47 (training) | 0.4303–0.5228 | zarr 20 (layer 36), 0.4303 | zarr 12 (layer 28) | 9 of 10 |
| Fr143 (validation) | 0.4790–0.5238 | zarr 3 (layer 19), 0.5238 | zarr 10 (layer 26) | 0 of 10 |

On Fr47 the contrast is strongest in zarr 17–23 (AUC at most 0.46, ink darker), and 9 of 10 validation windows contain
its furthest slice. On Fr143 there is no concentration. Its furthest slice, zarr 3, which no validation window
contains, is barely further from 0.5 than zarr 24 (0.4790), which 5 of 10 contain. Single-pixel intensity is a crude,
model-free proxy. It says where raw contrast is, not what a model can learn from texture across slices.

## What this means

* **The depth hypothesis does not explain the near-constant incumbent** (finding 86, AUC 0.5527). Its premise, that
  most windows miss the inked surface, does not hold on these fragments. Confidence: high for the coverage (exact
  from the loader's draw), moderate for "does not explain" (the band narrows validation's start positions from ten to
  eight, and v2's windows already overlap the detector's band by at least 14 of 16 slices).
* **A difference that remains, untested:** the detector reads all 26 band slices at once; the loop's model reads 16.
* **The band is still the owner's choice.** `[1, 27]` is the band the owner asked for (the detector's layers), in the
  loader's numbering. `null` would return to protocol v2's sample. Either way the incumbent must be re-scored, and the
  re-score still needs the lasagna decision.
* The benchmark finding in the review (P3, `--z 10` "below the band") was also measured in a 65-slice frame: on these
  volumes `--z 10` reads zarr 10–25, layers 26–41, inside the detector's band.

## Not done

No model was trained or re-scored with the band. Only `config.json`'s `uris` and `val_uri` were checked; a band set
for other fragments must be checked against their depth.
