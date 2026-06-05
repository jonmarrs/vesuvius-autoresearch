# Vesuvius AutoResearch — Progress Prize Submission

**Track:** Open-Source Tooling (monthly Progress Prize)
**What this is:** a tool/methodology submission, not a state-of-the-art ink-model claim.

<!--
REVIEW BEFORE FILING (internal note, delete before submitting):
- Verify the current month's form URL + deadline in villa/scrollprize.org/docs/34_prizes.md
  (the old forms.gle/... link is stale; next deadline is 2026-06-30 11:59pm PT).
- Do NOT paste any val_bpb improvement number here unless you have re-derived it
  from a clean run of results.tsv. The earlier "0.274 -> 0.087" claim is unverified
  and was removed for that reason. Insert a verified figure or leave the qualitative
  framing below.
- Record a short walkthrough (setup + one cycle) and link it where marked.
-->

## Overview

`Vesuvius AutoResearch` (project codename `bountyhunter`) is an autonomous research
loop for 3D ink detection on the Vesuvius Challenge. It samples a configuration
space (architectures, losses, augmentations), trains each candidate under a fixed
time budget, evaluates it against a held-out cross-fragment baseline, and keeps only
configurations that improve on that baseline. Every cycle is gated by an evidence
check and a preflight model smoke test, so the loop fails fast on broken
configurations instead of burning a training budget.

The submission packages this as reusable open-source tooling: integrated
architecture baselines, a metric suite, a reproducible config/evaluation contract,
and an automated execution loop. All machine-learning outputs use a 64×64 window
(`patch_size=64`), within the Challenge's 0.5×0.5 mm hallucination-mitigation cap.

## Provenance

This project has been developed in the open since **2026-03-23** (public MIT repo:
`github.com/jonmarrs/vesuvius-autoresearch`), with continuous commit history and an
earlier round of upstream `ScrollPrize/villa` contributions in May 2026. We note
the date only as factual provenance; the work stands on its own evidence.

## What it does that's distinctive

- **Grand-Prize-lineage architectures:** native TimeSformer, ResNet3D-101, and
  Inception-I3D paths alongside a gated UNet-transformer, selectable per cycle.
- **Topological evaluation:** models are scored with `centerline_dice` and
  `skeleton_distance_length`, not just pixel overlap.
- **Multi-task supervision:** on-the-fly 3D structure-tensor and ridge/fiber targets.
- **Calibration baseline:** periodic re-evaluation against a fixed reference recipe
  to detect research drift.
- **Reproducibility/safety gates:** preflight smoke test per cycle, plus local
  validators for scale-bar, provenance, ML-window, and train/predict-overlap rules.

## Quick start

Single NVIDIA GPU (e.g. RTX 4090), `uv` for dependencies:

```bash
uv sync
# Place Vesuvius scroll data under local_data/ (see https://scrollprize.org/data).
PYTHONPATH=. uv run python scripts/training/train.py --config config.json --smoke  # preflight: build model + one fwd/bwd
uv run run_autoresearch_loop.py               # start the autonomous loop
```

See [`REPRODUCE.md`](./REPRODUCE.md) for the exact, verified verification steps.
A short walkthrough (setup + one cycle): _[link to be added before filing]_.

## Results

This submission is about the **search-and-evaluation tooling**, not a
breakthrough detector — and the included evidence is reported honestly.

The 17 logged cycles in `results.tsv` show the loop's selection mechanism working
as designed: cross-fragment validation `val_bpb` improves monotonically under the
keep-only-if-better rule, from **0.4136** (first cycle) to **0.4123** (best). That
is a small gain — the point demonstrated is the reproducible, evidence-gated search
process, not a strong ink model. Topological scores over the same run
(`centerline_dice` ≈ 0.07–0.10) confirm there is substantial headroom; these
numbers are included precisely so reviewers can see the real state.

Reviewers can reproduce the table directly from `results.tsv` and the included
configs; the best checkpoint is published at
`huggingface.co/jonmarrs/vesuvius-autoresearch`.

## Built on Villa

This project integrates components imported from the official `ScrollPrize/villa`
repository — the evaluation metrics, the structure-tensor computation, and the
optional Primus/LeJEPA backbone — via the `villa/` submodule (nothing is copied in).
The scroll augmentation code (`scroll_augmentations.py`) is original work offered
toward villa issue #201, not borrowed from villa. Full component-level attribution
and licenses are in [`CREDITS.md`](./CREDITS.md).

## Reproducibility & method

See [`METHOD.md`](./METHOD.md) for the search/evaluation methodology and
[`REPRODUCE.md`](./REPRODUCE.md) for exact environment and reproduction steps.

## License

MIT (see [`LICENSE`](./LICENSE)). You may use, modify, and redistribute with
attribution; if borrowing code, preserve the upstream notices recorded in
`CREDITS.md`.
