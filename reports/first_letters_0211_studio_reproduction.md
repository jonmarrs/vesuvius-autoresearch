Studio, the reader that won PHerc. 211's First Letters prize, reproduces the winner's map on this RTX 4090 to bfloat16 rounding, in 75 seconds (2026-11-16)

Finding 123. Findings 118 to 122 found that on PHerc. 211's winning surface our pipeline finds the ink, and that no
permissive reader on this machine draws a readable word there. The winning reader, Studio (code MIT, weights CC
BY-NC 4.0), is the only one known to. The owner approved using it on 2026-11-16. Before it reads anything of ours,
this checked that it runs here as it ran for the winner: the winner's weights, input and command, on this machine.
Registered before Studio ran here: `docs/preregistration/2026-11-16_first_letters_0211_studio_reproduction.md`
(commit `45f2104e`; amendment 1, commit `7700f2a5`). Record: `reports/first_letters_0211_studio_reproduction.json`.
Scripts as run: `repro/first_letters/pherc0211_control/` (`run_studio_reproduction.sh`, `studio_reproduce.py`). The
weights and outputs stay on this machine.

**Verdict `REPRODUCED`**, as predicted: not bit-identical to the winner's output, and r = 1.0 (to six places) over
the 8,838,800 pixels of the winner's mask.

## The registered numbers

| | value |
|---|---|
| our output's SHA-256 equals the record's | no (`EXACT` not reached) |
| r, our map against the published one, over the mask | 1.0 |
| absolute difference: median / 99th percentile / largest | 0.000094 / 0.000645 / 0.003226 |
| mean probability, ours / the winner's | 0.335175 / 0.335175 |
| pixels on the same side of 0.5 | 99.9892% |

The lines were r ≥ 0.99 and a 99th-percentile difference ≤ 0.05; the run is well inside both. The differences
are bfloat16 rounding on a different GPU, as the winner's README expected for anything but its GH200.

## How it ran

- **Inputs.** The weights (893,443,724 bytes) came from the code repository's release, and the 16-plane input from
  the winner's public folder. Each, and the bundled `inference.py`, matched the SHA-256 in the winner's
  `inference-record.json`.
- **Environment.** The winner's pinned packages in an isolated Python 3.11.16: torch 2.14.0+cu130 on the GeForce
  RTX 4090, with bfloat16 supported.
- **Inference.** The record's command: stride 64, Hann blending, batch 32, bfloat16. It took 75 s, with GPU memory
  at most 14,481 MiB (all processes) of the card's 24 GB.

**The first attempt stopped before the model ran** (amendment 1). This machine's uv (0.11.18) has no download for
CPython 3.11.16. The winner's own helper bootstraps `uv==0.13.6` in that case, and the second attempt did the
same. The fetch had already passed its three checksums. Both attempts' records are kept.

## What it cost

| step | wall time |
|---|---|
| fetch and checksums (first attempt, with the downloads) | 44 s |
| environment (second attempt: uv bootstrap, Python, torch 2.14.0 and CUDA 13 wheels) | 84 s |
| inference, 16 × 1,740 × 6,020 voxels | 75 s |
| comparison | 2 s |

## What this does to the campaign

The registered consequence of `REPRODUCED`: "Studio runs here as it ran for the winner, at the measured cost.
Next, registered separately, it reads our own geometry." That stands.

Studio's speed here, 75 s for an 8 cm² surface at 14.5 GB, means reading whole bands with it is cheap on this card.
The next step reads two things with it:

- our render of the winner's surface (finding 118's), which tests our renderer;
- finding 121's windings from our own fit, carried onto the winner's surface, which tests the whole pipeline.

Both are compared with the winner's map and, for legibility, by eye.

## What this does not show

1. Anything about our geometry or renders: inputs, weights and command were all the winner's.
2. That Studio reads other scrolls or other places as well. Its continued training evaluated it repeatedly on
   PHerc. 211, so this surface is not an untouched test of it (strategy review, 2026-11-16).
3. Whether a submission built on Studio's CC BY-NC weights is accepted. The owner decided to use it; the prize page
   does not address third-party non-commercial weights in First Letters.
