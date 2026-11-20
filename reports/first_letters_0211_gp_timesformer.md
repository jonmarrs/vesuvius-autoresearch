On the surface that won PHerc. 211's First Letters prize, the 2023 Grand Prize TimeSformer finds the ink weakly, at r 0.24, against 0.53 for the recipe's four models: `GP_FARTHER` (2026-11-16)

Finding 122. Findings 118 to 121 showed that on PHerc. 211's winning surface our pipeline finds the ink and that
the reader is what separates it from letters. This tested the other permissive reader already on this machine: the
2023 Grand Prize winners' canonical TimeSformer (repository MIT), which drew legible Greek on Scroll 1 here in June.
It was run on finding 118's render and compared with the winning reader's map by finding 120's numbers. Registered
before the model ran on any PHerc. 211 data: `docs/preregistration/2026-11-16_first_letters_0211_gp_timesformer.md`
(commit `a5ccdf13`). Record: `reports/first_letters_0211_gp_timesformer.json`. Scripts as run:
`repro/first_letters/pherc0211_control/` (`run_gp_timesformer.sh`, `gp_timesformer.py`, `audit_pickle.py`,
`gp_stub/wandb.py`). The maps and the image stay on this machine; this report carries numbers.

**Verdict `GP_FARTHER`**, as predicted, by the registered table: every step exited 0, the model's r clears its
controls, and it is 0.293 below the ensemble's in r and 0.1424 below in overlap, past both margins.

## The registered numbers

Finding 118's alignment (render layer 33, r 0.8128, shift (0, 0)) and cells (550,480 of 550,482); the winner's ink
cells (probability at least 0.5): 121,191. The model read the reversed layer order as its reading side, fixed in
the registration.

| | ensemble (four models) | 2023 Grand Prize TimeSformer | difference |
|---|---|---|---|
| **r against the winner's map** | 0.53 | 0.237 | **−0.293** (margin −0.10) |
| control: other side | −0.0059 | −0.0035 | |
| control: slid 64 pixels, largest absolute | 0.093 | 0.0501 | |
| **overlap (Dice) with the winner's ink cells** | 0.5076 | 0.3652 | **−0.1424** (margin −0.05) |
| control: overlap slid 64 pixels, largest | 0.3315 | 0.2865 | |

The model's r is more than four times its largest control, so it finds this scroll's ink: weakly. Above its slid
floor its overlap gains 0.08, against the ensemble's 0.18.

## Described, as registered

None of this changes the verdict.

- **The reading side was the right one.** Scored with the forward order as its reading side, r is −0.0035 and the
  overlap 0.212.
- **The spread of Δr.** Over 1,000 resamplings of 168 blocks, the 95% interval of Δr is −0.3424 to −0.2449, wholly
  past the margin.
- **Agreement with the other readers.** r 0.1637 with the ensemble and 0.2436 with Reader V3.
- **Reader V3 on the same cells.** r 0.6271, overlap 0.6095, as in finding 120.

## What the maps look like

My reading of the image (the ensemble, Reader V3, this model and the winner's map, one above another), a judgement
and not a measurement:

- **This model** draws scattered dots over the whole surface, densest in the middle third, with the faint grid of
  its 32-pixel tiling. There is no letter shape and no line structure that I can see.
- **The other three panels** are as findings 118 and 120 described.

## The checkpoint, and what was done to load it safely

- **Checksum.** The file's SHA-256 matched the registration's (`93f56e56…`).
- **Pickle audit.** torch's weights-only unpickler cannot rebuild the `collections.defaultdict` this training
  checkpoint carries, so `audit_pickle.py` read the pickle's opcodes without running them. The only names it
  imports are:
  - tensor rebuilders and `torch.FloatStorage`;
  - `dict`, `OrderedDict` and `defaultdict`;
  - `torch.optim.adamw.AdamW` and `torch.optim.lr_scheduler.CosineAnnealingLR`.

  The audit passed, and only then did the winners' script load it.
- **Nothing logged leaves the machine.** That script logs its predictions to wandb. A stub `wandb` module first on
  the path made every such call do nothing.

## What it cost

| step | wall time |
|---|---|
| checksum and pickle audit | 1 s |
| segments (26 layers in each order, 353 MB) | 37 s |
| inference, forward order / reversed order | 40 s / 37 s |
| comparison | 37 s |

2 min 32 s in all, on the GPU for 77 s of it.

## What this does to the campaign

The registered consequence of anything but `GP_CLOSER` reads: "no permissive reader on this machine comes closer
than Reader V3. The reader question rests on the owner's decision about the winning reader."

It stands. Of the three permissive readers tried on this surface, Reader V3 is the best (r 0.63), the recipe's four
models next (0.53), and the 2023 Grand Prize model a distant third (0.24). None draws a readable word.

The only reader known to draw letters on this surface is the winning reader, Studio, whose weights are CC BY-NC.
Whether it may be used in a submission is the owner's decision.

## What this does not show

1. **How the model would read a rescaled render.** It was trained at 7.91 µm and ran here at 9.362 µm, unscaled.
   A rescaled read was not registered and was not tried.
2. **Legibility as a measurement.** The statements about letters are my reading of one image.
3. **More than one surface of one scroll,** refined by hand until letters showed under the winning reader.
4. **Variation between runs.** Each map was made once.
