# Running the released PHerc.1667 ink ablation checkpoints

Six sibling checkpoints, `scrollprize/PHerc.1667-iteration-0` through `-5`, released with **identical
architecture and identical step budget** (12,396 optimizer steps) and differing **only in
pseudo-label density**. That controlled series is the reason this line of work is possible at all.

## Environment: isolated, and pinned to 4.57.6

```bash
uv venv --python 3.11 .venv
uv pip install torch --index-url https://download.pytorch.org/whl/cu128
uv pip install "transformers==4.57.6" safetensors numpy zarr fsspec aiohttp
```

Two things that each cost a run:

* **`transformers` must be 4.57.6**, the version in the checkpoints' `config.json`. On 5.x the
  weights load (338/338) and then `from_pretrained` dies in `_finalize_model_loading` with
  `'InkDetectionModel' object has no attribute 'all_tied_weights_keys'`: 5.x renamed
  `_tied_weights_keys` and the released `modeling_inkdetection.py` predates it.
* **Use a separate venv.** Installing `transformers` into this repository's venv fails on
  `safetensors>=0.8.0 required, found 0.7.0`, and that venv is what 713 tests run against. It was
  installed, the conflict appeared, and it was uninstalled again; do not repeat that.

## Input

The checkpoints take `(B, 1, 62, 256, 256)`, z-score normalised per tile, and return
`(B, 1, 64, 64)` logits, so the prediction is 4x downsampled from the input tile.

Data comes from the open-data bucket, which is anonymous and region-addressable, so no bulk download
is needed:

```
s3://vesuvius-challenge-open-data/PHercParis4/segments/20231210121321/surface-volumes/
  2.4um-0.22m-78keV-volume-20260411134726.zarr    level 2: (109, 12750, 9995) uint8, chunks (109,128,128)
```

Chunks carry full depth, so a `[:, y0:y1, x0:x1]` slice costs only the tiles it covers.

**This is the same source ScrollGT's `scroll1_20231210121321` target was registered against**, which
is the point: the ground truth needs no new coordinate bridge. Our worst published error, the
"everything reads at chance" retraction, was a bridge wrong in a way its own checks could not see.

## Verified on 2026-08-30

Checkpoint `iteration-0`, the cross-segment baseline whose `config.json` records training on
`500p2a + 658 + 20250910185200 + 20250919125754*` and therefore **not** on `20231210121321`:

```
loaded 83.3M params
input  (4, 1, 62, 256, 256)   output (4, 1, 64, 64)
sigmoid  min 0.0022  max 0.9708  mean 0.0632  std 0.1144   above 0.5: 2.8%
per-tile mean: 0.060  0.065  0.062  0.066
```

Well-behaved rather than degenerate: full probability range, a plausible firing rate, and consistent
per-tile means without collapsing to a constant.
