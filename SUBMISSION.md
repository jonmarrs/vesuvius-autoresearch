# Vesuvius AutoResearch — Progress Prize Submission

**Track:** Open-Source Tooling (monthly Progress Prize)
**What this is:** a tool/methodology submission, not a state-of-the-art ink-model claim.

<!--
REVIEW BEFORE FILING (internal note, delete before submitting):
- The live monthly filing text is docs/PRIZE_FILING_DRAFT_2026-07.md (deadline
  2026-07-31 11:59pm PT); this file is the repo-level summary and must stay
  consistent with it. Verify the current form URL in
  villa/scrollprize.org/docs/34_prizes.md before filing.
- Refresh all numbers against the latest committed reports under reports/detector/.
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

- **A working, reproducible ink detector** (`vesuvius_autoresearch.detector`): the proven
  2023 Grand-Prize TimeSformer recipe productionized with a one-command `reproduce` —
  held-out same-scroll `val_f1` 0.393 / prevalence-lift 2.07 (ROC-AUC 0.709) at the
  prize-compliant 64 px window. See `reports/detector/REPRODUCTION.md`.
- **Honest metrics as a contract** (`detector/metrics.py` + `measure` CLI): threshold-swept
  F1 primary, average precision + AP-prevalence-lift as imbalance-robust gates, ROC-AUC
  secondary — plus the first valid cross-scroll measurement with it (lift 2.07 same-scroll
  → 1.29 cross-scroll). An inherited `skeleton_distance_length` "prize gate" was **removed
  after we proved it invalid** (location-blind; probe script included).
- **SOTA open-data tooling + distillation** (`repro/sota_data/`): anonymous-S3 discovery/
  fetch/conversion for `s3://vesuvius-challenge-open-data/`, a documented survey of what the
  bucket ships (no ground-truth labels aligned to the new re-flattening), and a
  teacher–student distillation pipeline that lifts held-out agreement-with-teacher from the
  chance floor to `val_f1` 0.662 / lift 3.24 on one GPU.
- **The autonomous loop:** Grand-Prize-lineage architectures (TimeSformer, ResNet3D-101,
  Inception-I3D, gated UNet-transformer) selectable per cycle, multi-task supervision
  (structure-tensor and ridge/fiber targets), calibration baselines, and per-cycle
  preflight smoke tests plus validators for ML-window and train/predict-overlap rules.

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

This submission is about **honest, reproducible tooling** — and, as of July 2026, a
working detector built with it. All numbers below are from committed reports
(`reports/detector/`), reproducible from public data on a single RTX 4090:

| Result (held-out) | val_f1 | AP | prevalence-lift | ROC-AUC |
| --- | --- | --- | --- | --- |
| Detector, same-scroll (Fr47→Fr143) | 0.393 | 0.357 | 2.07 | 0.709 |
| Detector, cross-scroll (→Scroll 1) | 0.222 | 0.144 | 1.29 | 0.585 |
| SOTA-distilled student (vs teacher)* | 0.662 | 0.742 | 3.24 | 0.865 |

\* Distillation numbers are **agreement with the released canon predictions** (a model
output), not ground-truth accuracy — no ground-truth labels aligned to the SOTA
re-flattening are released; this is stated in the report itself. The cross-scroll row
quantifies the field's central generalization gap; the distilled row shows the SOTA
data + distillation closing it on consumer hardware, with the repo's first
letterform-shaped output. Negative results (a full-resolution ResEncUNet that
underperformed; earlier loop-era chance-floor results and their diagnosis) are kept in
`FINDINGS.md` — reviewers can see the real state, including what did not work.

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
