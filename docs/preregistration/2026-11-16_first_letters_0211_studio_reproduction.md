# Pre-registration: does Studio, the reader that won PHerc. 211's First Letters prize, reproduce the winner's map on this machine?

**Written 2026-11-16, before Studio has been run here.** Finding 123.

## The question

Findings 118 to 122 found that on PHerc. 211's winning surface our pipeline finds the ink (r 0.52 end to end), and
that no permissive reader on this machine draws a readable word there. Reader V3 is the best of the three, at r
0.63. The winning reader, Studio, is the only one known to draw letters there. Its weights are CC BY-NC 4.0, and
the owner approved using it on 2026-11-16.

Before Studio reads anything of ours, it must be shown to run here as it ran for the winner. **From the winner's
own supplied weights and 16-plane input, with the winner's recorded command, does the map Studio makes on this
RTX 4090 match the winner's published map?** The run also measures Studio's speed and memory on a 24 GB card,
which the strategy review of 2026-11-16 listed as untested.

## Reachability, checked before this was written

- **The winner's record** (`inference-record.json` in the winner's surface folder, which finding 118 downloaded)
  names everything:
  - the command: `python inference.py --input planes16.npy --output ink.npy --checkpoint
    studio-softloss-20261023-ema.safetensors --stride 64 --blend hann --batch-size 32`;
  - SHA-256 values for the code, the weights, the input and the output;
  - the environment: torch 2.14.0 with CUDA 13.0, on an NVIDIA GH200, in bfloat16. Two runs there were bitwise
    identical.
  - The winner's README says other GPU types can give rounding differences.
- **The code.**
  - `inference.py` (in that folder; its SHA-256 matches the record's `09752cf7…`) loads the weights with
    `safetensors` and the input with `np.load(..., allow_pickle=False)`, and downloads nothing when it is given a
    local checkpoint.
  - `model.py` defines torch modules only.
  - Both were read in full before this was written. The code repository is MIT.
- **The weights.** One asset of the code repository's release `studio-softloss-20261023`:
  `studio-softloss-20261023-ema.safetensors`, 893,443,724 bytes, SHA-256 `96b32628…` by the record. A safetensors
  file holds tensors only.
- **The input.** `…-v9_model_input_planes16_uint8.npy` in the winner's public folder (Drive id `1Vj74td…`), SHA-256
  `e7cdd509…` by the record: uint8 [16, 1740, 6020], planes 23 down to 8 of a 31-plane render.
- **Exposure.** The winner's README says PHerc. 211 was not used to train the model. The strategy review notes that
  its continued-training record evaluated it repeatedly on PHerc. 211, so the winner's map is not an untouched
  test. That does not matter here: this asks for reproduction, not generalisation.
- **Not checked:** nothing has run.
  - The pinned environment is not built.
  - Memory at batch 32 on a 24 GB card is not known.
  - The 893 MB weights file and the 168 MB input are not downloaded.

## Procedure

`run_studio_reproduction.sh` (`repro/first_letters/pherc0211_control/`), run once, each step only if the one before
exited 0:

1. **Fetch.** The weights from the release URL and the input from the winner's folder, by anonymous reads. Each, and
   the bundled `inference.py`, is checked against the record's SHA-256.
2. **Environment.** The winner's pinned packages (`requirements-inference-exact.txt`, then numpy 2.4.6 and
   safetensors 0.8.0) in a uv venv of Python 3.11.16 under the run directory.
3. **Inference.** The record's command, on this machine's RTX 4090, in bfloat16; GPU memory sampled every 2 s.
4. **Comparison** (`studio_reproduce.py`), over the pixels of the winner's mask:
   - whether our output's SHA-256 equals the record's `e2f8b9afad4dcde91a6775713b5da1e08352ac38adf39e7e75cb9f4b181bd139`;
   - r between our map and the published one;
   - the median, 99th percentile and largest absolute difference.

## Predictions, fixed now

- **What I expect: `REPRODUCED`, not `EXACT`, with moderate-to-high confidence.** A different GPU in bfloat16 should
  change rounding, not the map. The run could also fail for memory at batch 32; that is `DOES_NOT_RUN`, and the
  batch size is not changed in this run.

## Decision rule

| outcome | verdict |
|---|---|
| a step fails (a checksum, the environment, memory) or the output is missing | `DOES_NOT_RUN` |
| our output's SHA-256 equals the record's | `EXACT` |
| r at least 0.99 over the mask and a 99th-percentile absolute difference of at most 0.05 | `REPRODUCED` |
| otherwise | `DIFFERS` |

The 0.99 and 0.05 lines are judgements: rounding noise in bfloat16 should sit well inside them, and a different
model or input would not.

What each does to the campaign:

- **`EXACT` or `REPRODUCED`:** Studio runs here as it ran for the winner, at the measured cost. Next, registered
  separately, it reads our own geometry: finding 121's windings and our render of the winner's surface, against the
  winner's map and by eye. That is the first test of our pipeline with a reader known to draw letters.
- **`DIFFERS`:** the cause is found before Studio reads anything of ours: environment, GPU, or input order.
- **`DOES_NOT_RUN`:** the failure and its fix are reported, then the run is registered again.

## Amendment 1, 2026-11-16, before any inference ran

The first run stopped at step 2 (`DOES_NOT_RUN`).
- **What ran:** the fetch passed, with all three checksums (weights, input, `inference.py`) matching the record.
- **What failed:** this machine's uv (0.11.18) has no download for CPython 3.11.16
  (`No download found for request: cpython-3.11.16-linux-x86_64-gnu`).
- **What was not reached:** nothing of the model ran.

The winner's own helper (`reproduce_submission.sh`) bootstraps `uv==0.13.6` in a venv of its own when uv is not
installed. Step 2 now does the same, in its own folder under the run directory, and is otherwise unchanged. The
first attempt's records are kept beside the second's. Everything else in this registration stands.

## What the result cannot do

- Anything about our geometry or our renders: input, weights and command are all the winner's.
- Anything about letters beyond what the winner's map already shows.

## Cost

Downloads of about 1.1 GB, plus the pinned environment (torch 2.14.0 and CUDA 13 wheels, several GB). Inference on
16 × 1,740 × 6,020 voxels: not measured on this card. Nothing is uploaded; the weights and outputs (CC BY-NC 4.0)
stay on this machine.
