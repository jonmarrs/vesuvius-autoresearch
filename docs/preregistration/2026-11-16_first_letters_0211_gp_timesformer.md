# Pre-registration: on the surface that won PHerc. 211's First Letters prize, does the 2023 Grand Prize TimeSformer put ink where the winning reader did, more closely than the recipe's four models?

**Written 2026-11-16, before this model has been run on any PHerc. 211 data.** Finding 122.

## The question

Findings 118 to 121 established two things about PHerc. 211's winning surface:

- **The geometry is not the gap.** Our pipeline finds the ink there: r 0.52 end to end, against 0.54 for the same
  models on the winner's own surface.
- **The readers are.** Neither the recipe's four models (r 0.53) nor Reader V3 (r 0.63, MIT) draws a readable
  word there, where the winning reader (Studio, CC BY-NC) does.

Using the winning reader is the owner's decision. This tests the other permissive reader already on this machine:
the canonical TimeSformer of the 2023 Grand Prize, which drew legible Greek on Scroll 1 here in June. **On the same
render and cells, does it agree with the winning reader's map more closely than the four models do?**

## Reachability, checked before this was written

- **The model:** `timesformer_wild15_20230702185753_0_fr_i3depoch=12.ckpt`, the winners' canonical checkpoint.
  - **Licence:** linked from the README of the 2023 winners' repository (github.com/younader/Vesuvius-Grandprize-Winner,
    MIT). The checkpoint's own licence is not stated separately.
  - **On this machine:** downloaded from the authors' Drive on 2026-06-19 as
    `villa/ink-detection/timesformer_weights.ckpt` (SHA-256 `93f56e56…`, the same bytes as the downloaded file).
    June's replication drew legible text on two Scroll 1 segments with it.
- **Exposure.** Trained on Scroll 1 (PHerc. Paris 4) segments at 7.91 µm in 2023. PHerc. 211 was scanned in
  2025 at 9.362 µm and 113 keV, so it could not have been in the training data.
- **Safe to load.** The winners' script loads the checkpoint with full unpickling, and torch's weights-only
  unpickler cannot rebuild the `collections.defaultdict` its optimizer state holds.
  - **The check used instead:** `audit_pickle.py` reads the pickle's opcodes without running them. It lists every
    name the pickle can import: tensor rebuilders, `torch.FloatStorage`, `dict`, `OrderedDict`, `defaultdict`,
    `torch.optim.adamw.AdamW` and `torch.optim.lr_scheduler.CosineAnnealingLR`, and nothing else. The run refuses
    the file unless that remains so.
- **Nothing leaves the machine.** The script logs its predictions to wandb. The run puts a stub `wandb` module
  first on the path (`gp_stub/wandb.py`) whose calls do nothing. A smoke run on random layers wrote its
  prediction and created no wandb folder.
- **The script runs here.** villa's copy of the winners' script (`villa/deprecated/ink-detection/
  inference_timesformer.py`) ran on random layers in June's environment (torch 2.12.1, CUDA) and wrote a
  prediction PNG.
- **Not checked:** nothing has run on PHerc. 211.
  - The model's reading side and resolution on this scan are unknown.
  - Its input range differs: it clips at 200 an 8-bit CT taken at another energy.

## Procedure

`run_gp_timesformer.sh` (`repro/first_letters/pherc0211_control/`), run once, each step only if the one before
exited 0: checksum, pickle audit, segments, inference in each layer order, comparison.

- **Segments.** Finding 118's 66-layer render of the winner's surface, unchanged, written as the script's segment
  layout in both layer orders, with no mask, so every tile is read.
- **Window.** The model reads 26 layers from `start_idx` 17 of 65-layer volumes with the surface at layer 32,
  i.e. 15 layers on one side of the surface and 10 on the other. Our render's surface is layer 33, so the window
  is:
  - render layers 18 to 43 in the forward order (`start_idx` 18);
  - layers 17 to 42 of the reversed order (`start_idx` 17), which are render layers 48 down to 23.
- **Inference.** The winners' script at its defaults (tile 64, stride 32, batch 64), at this scan's own
  resolution. No rescaling.
- **The reading side is the reversed order, fixed now.** The recipe's ink_9um models were trained on surface
  volumes made the same way as the 2023 ones, and they read this render on its reversed order (finding 118: r
  0.53 against −0.006). The forward order is its other side.
- **Comparison.** `gp_timesformer.py compare` is finding 120's comparison with this model in Reader V3's place:
  finding 118's alignment, cells and reference, and the same numbers.
  - **r** against the winner's map, both with their broad background taken off. Controls: the other side, and the
    map slid 64 pixels in four directions.
  - **Overlap:** the Dice coefficient of the winner's ink cells (probability at least 0.5) against as many of
    the model's strongest cells. Control: the map slid 64 pixels, leaving out cells that wrapped round.

  Both are set against the four-model ensemble at depth +1.

## Predictions, fixed now

- **What I expect: `GP_FARTHER`, with moderate confidence.** The model was trained on one scroll, at 7.91 µm and a
  different energy, and the reader that did best here (Reader V3) was trained on six scrolls including scans like
  this one. Against that: it drew legible text on Scroll 1, and its 26-layer window is wider than the ink_9um
  models' 17 layers.

## Decision rule

Δr and Δoverlap are this model's number minus the ensemble's, each rounded to four places first. The table is
finding 120's.

| outcome | verdict |
|---|---|
| a step fails, no alignment within 16 pixels, fewer than half the mask's cells compared, or a number missing | `DOES_NOT_RUN` |
| this model's r is not at least twice the absolute value of each of its controls | `GP_FAILS_CONTROLS` |
| Δr at least +0.10 and Δoverlap at least +0.05 | `GP_CLOSER` |
| Δr at most −0.10, or Δoverlap at most −0.05 | `GP_FARTHER` |
| otherwise | `GP_NO_CLOSER` |

What each does to the campaign:

- **`GP_CLOSER`:** the owner looks at the image for legibility. If it is legible where Reader V3 is not, this
  model is read beside Reader V3 on the next band, from a checkpoint whose repository is MIT.
- **Any other verdict:** no permissive reader on this machine comes closer than Reader V3. The reader question
  rests on the owner's decision about the winning reader.
- **`GP_FAILS_CONTROLS` with the forward order clearing them:** the reading side was fixed wrongly. This is said
  in the report, and the verdict stands.

## Described, not deciding

- the forward order scored as if it were the reading side;
- the spread of Δr over 1,000 resamplings of 64-cell blocks;
- this model's r with the ensemble and with Reader V3;
- Reader V3's numbers on the same cells;
- an image of the ensemble, Reader V3, this model and the winner's map, one above another, for the owner, on this
  machine.

## What the result cannot do

- **Legibility.** r and overlap measure where ink is; the image is for the owner's eye and decides nothing.
- **A fair test of the model at its own resolution.** No rescaling is tried. A miss at 9.362 µm does not say how it
  would read a rescaled render.
- **The reference is one reader's map;** a model that draws strokes differently is scored down.

## Cost

Inference on 1,740 × 6,020 pixels in each order, about two to five minutes each on the GPU, after a compile of
about a minute. Segments 0.55 GB on disk. Comparison a minute. Nothing is uploaded.
