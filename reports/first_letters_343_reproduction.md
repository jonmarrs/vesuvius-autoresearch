The published PHerc. 343 First Letters image rebuilds on this machine from the public mesh, CT and models: 99.95% of its pixels are identical and none differs by more than 5 of 255 (2026-11-10)

This is the kill test of the First Letters campaign in `docs/RESEARCH_STRATEGY.md`: before the published
[PHerc. 343 recipe](https://github.com/Nieuwlaar/pherc343-first-letters) (commit `e8370f1f`) is tried on a scroll
nobody has read, show that its compute chain gives its known result here. Host: 4 cores, 31 GB of RAM, one RTX 4090.
Record: `reports/first_letters_343_reproduction.json`. Scripts as run are preserved at commit `9fa747c5`;
`repro/first_letters/pherc343/README.md` describes the later checkpoint-reporting correction.

**Verdict `REPRODUCED`, for the part of the chain that was run.** The chain from the two published windings to the
image was run here: mesh join, render from streamed CT, the four ink models at the one depth the image shows, map
merge, image. The step that produced the windings (spiral fit, snap, flatten) was not run, and neither was the
31-depth sweep whose pooled statistics set the image's contrast. Those statistics were copied from the published
sidecar. The test says nothing about whether the recipe finds text on an unread scroll.

## What matched

| Step | Check | Result |
|---|---|---|
| Mesh join (`mesh/build_concat.py`) | SHA-256 of `x.tif`, `y.tif`, `z.tif`, `meta.json` against `outputs/SHA256SUMS` | 4 of 4 identical |
| 66-layer render | decoded layer 34 inside the image area, and the valid mask of all 66 layers, against the sidecar's hashes | both identical; valid fraction 0.6418 on both sides |
| 66-layer render | hash of the zarr file tree | **differs**: 1,009 files on both sides, 945,626,693 bytes here against 945,626,701 published. Cause not identified |
| Ink maps, depth +1, reading side, after the tile-phase merge | SHA-256 against the sidecar | dense_native and Hecate identical; ink_9um seeds 42 and 43 differ |
| Image, with the published statistics | pixels of the whole 5854 × 2881 PNG | 8,727 of 16,865,374 differ (0.052%), by at most 5 of 255 |
| Image, data panel only (5641 × 2455) | ink drawn on both / on either | IoU 0.9999; in each of the 18 letter boxes at least 0.9997 |

The ink_9um maps differ because that model is not deterministic on this card. One model (seed 42, plain render) run
twice here gave maps that differ on 0.264% of pixels (reading side; 0.253% on the other side), never by more than
one grey level. The recipe's README reports the same size of difference between GPU types. The dense_native map is
identical although its checkpoint is a rebuild: the original `.pth` is not public and the recipe's script rebuilds
it from the published safetensors.

**Control for the comparison.** The same panel comparison with our panel displaced diagonally gives IoU 0.570 at
16 px, 0.179 at 64 px and 0.052 at 256 px (tint correlation 0.800, 0.228, 0.006). The match is therefore positional
and not a property of the papyrus-wide ink statistics.

## Without the depth sweep the image is weaker, but the same letters show

The recipe z-scores each model against statistics pooled over depths −15 to +15 (496 GPU jobs). A second image was
built from the depth +1 maps alone, with no published statistics. Against the published image:

| | published statistics | depth +1 statistics only |
|---|---|---|
| ink drawn, share of the panel (published 0.0851) | 0.0851 | 0.0623 |
| IoU of drawn ink with the published image | 0.9999 | 0.7324 |
| tint correlation with the published image | 1.000 | 0.956 |
| letter boxes: lowest / median IoU | 0.9997 / 1.000 | 0.514 / 0.811 |

Every model's mean and spread are higher at depth +1 than pooled (Hecate: mean 0.074 against 0.045), so the same ink
scores lower against its own depth. The strokes are in the same places and fainter. On a new scroll the sweep is
therefore needed for the published contrast, but one depth is enough to see whether a band has row-aligned ink at
all, at 1/31 of the GPU time. That is an inference from this one image, where the ink depth was already known.

## Cost on this machine

| Step | Wall time | Notes |
|---|---|---|
| Render, 66 layers of 2560 × 6720 | 7 min 44 s | 2 threads, 3 GB chunk cache, container capped at 8 GB; 4.42 GB of CT streamed from the public bucket and cached |
| Ink, 8 jobs (4 models × plain and padded render, depth +1) | 17 min 10 s | one villa job and one Hecate job at a time; peak GPU memory 3,174 MiB |
| Per job | dense_native 171–190 s, ink_9um 157–180 s, Hecate 424–427 s | |

The training loop was stopped for the ink step, 09:58 to 10:20 PST, and restarted. Finding 109 used the GPU
intermittently during it, so the ink times are upper bounds. At this rate the full sweep is 31 × 1,030 s, about 9
hours with one job of each kind at a time; the recipe quotes roughly 6 hours on one RTX 4090 with two of each. The
whole working directory, with the environment, checkpoints, CT cache and outputs, is 14 GB.

Host memory of the ink jobs was not recorded. The render's container was sampled at about 1.5 GB and not logged.

## Differences from the recipe as published

- **Renderer.** The recipe names the VC3D `41701aa` AppImage. The render here used our source build of villa
  `75c79ac5f`, whose `volume-cartographer` tree is identical to `41701aa`. This build caches streamed chunks under
  `$HOME/.VC3D/remote_cache`, so the container was given a persistent `HOME`.
- **Ink environment.** A virtual environment built with villa `0fb38c45`'s own bootstrap script (Python 3.14.3,
  torch 2.13.0+cu130) instead of the recipe's draft Dockerfile.
- **Checkpoints.** The historical record claims all four load with `torch.load(weights_only=True)`, but that
  flag was hardcoded and the checker could return success after a refusal or no inputs. No identity-bound
  load receipts are committed, so this claim is unverified, not a checkpoint safety certification.
  The JSON now marks verification unknown and retains the original claim with immutable source provenance;
  every other historical field is unchanged. This correction does not show that any checkpoint failed or was unsafe.
  Villa's loader at that commit calls `torch.load` with `weights_only=False`.

## What this does not show

1. That the recipe finds text anywhere new. The join's two grid offsets were measured in the text rows, and the
   letter boxes that set the row lines were placed on a result already in view. Both are the author's and were
   reused as published.
2. That the spiral fit, snap and flatten run on 4 cores and 31 GB. That is the next unknown, and the larger one.
3. That the pooled statistics reproduce. They were copied.
