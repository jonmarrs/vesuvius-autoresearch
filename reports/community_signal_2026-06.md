# Community Signal: June 2026 Progress Prize

## Discord Post (Draft)

**Channel:** `#code`

**Message:**
> Just pushed a production-scale fix for the fibers ridge/vesselness filters to my villa fork (`sprint033-fibers-gpu`).
>
> Main changes:
> 1. Replaced `cupy.linalg.eigvalsh` with a closed-form analytical 3x3 eigensolver. This fixes the common cuSolver `(N, N, N, 3, 3)` batch failure on large volumes.
> 2. Added `detect_ridges_tiled` and `detect_vesselness_tiled` for memory-efficient processing of full scroll divisions (validated 512^3 in ~1.0GB VRAM).
> 3. Benchmarks on 4090 show ~300x speedup over CPU for 256^3 regions.
>
> Full benchmark table and parity validation vs NumPy is in the PR draft: [Link to PR if open, or repo doc]
>
> If anyone has a very large fiber annotation volume that was previously OOMing or slow, I'd appreciate a test run on this branch.

## Responses Log

*Log substantive replies or feedback here for the prize submission.*

- [2026-06-02]: (Awaiting post)
