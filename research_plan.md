# Research Plan: Vesuvius Challenge (Project 002)

## Objective
Optimize 3D ink detection for cross-scroll generalization, targeting the $1M Grand Prize. We utilize an autonomous research loop to evolve high-performance models while adhering to strict hardware and data constraints.

## Strategic Roadmap
For the comprehensive systematic progress plan, hardware constraints (RTX 4090), and data management policy, refer to:
**[RESEARCH_STRATEGY.md](./RESEARCH_STRATEGY.md)**

## Current Breakthrough
- **Model:** 3D Temporal Attention Hybrid with Anisotropic Fiber Extraction (5.97M params).
- **Setup:** Transitioning from synthetic targets to a **Gold Standard Labeled Library** (Fragments 1-6 + Monster Segment).
- **Performance:** **31.77M voxels/sec** (verified on RTX 4090).
- **Isolation:** **5,767x interlayer isolation** (zero ghosting between papyrus wraps).

## Core Research Focus
1.  **Cross-Scroll Generalization:** Maximizing Dice score on unseen scrolls (Scroll 5 / Paris fragments).
2.  **Autonomous Evolution:** Running 12-hour "Night Shift" sprints with 5-minute experiment iterations.
3.  **Gold Standard Alignment:** Perfectly aligning local unrolled layers with manual ink annotations.

## Technical Goals
- **Patch Optimization:** Scale from 64x64 to **256x256 patches** using 24GB VRAM.
- **Denoising:** Autoresearch kernels to handle high X-ray noise floor in carbonized regions.
- **Throughput:** Maintain >50M voxels/sec for rapid full-scroll inference.

## Verification
- Daily morning review of `results.tsv` from the Night Shift loop.
- Automated Dice score benchmarking against the Gold Standard Library.
- Inference consistency checks on unseen "wild" segments.
