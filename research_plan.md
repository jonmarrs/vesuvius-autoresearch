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
3.  **Hallucination Mitigation:** Strictly limiting prediction window size to **0.5x0.5 mm (64x64 pixels)** and maintaining zero overlap with training regions.

## Technical Goals
- **Throughput Optimization:** Maximize voxel/sec throughput on the RTX 4090 while maintaining small patch sizes.
- **Denoising:** Autoresearch kernels to handle high X-ray noise floor in carbonized regions.
- **Reproducibility:** Provide a verified Docker image for automated validation.

## Verification & Submission
- **Scale Bar Implementation:** Ensure `predict.py` generates images with a programmatic 1 cm scale bar.
- **3D Context:** Include 3D segmentation IDs and coordinates for all text discovered.
- **Non-Overlap Audit:** Verify that discovered text regions were never exposed to the model during training.
