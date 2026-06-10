# Community Signal: June 2026 Progress Prize

## Discord Post (POSTED 2026-06-10)

**Channel:** ScrollPrize Discord `#code`
**Posted by:** Jon (jdmarrs)
**Artifact:** https://github.com/ScrollPrize/villa/pull/1033
**Thread link:** _add once available_

**Message as posted** (final text from `docs/DISCORD_POST_DRAFT_2026-06.md`):

> **production-scale GPU fiber/ridge detection - replication wanted**
>
> I opened a PR for villa's fibers-dataset ridge/vesselness tooling: https://github.com/ScrollPrize/villa/pull/1033
>
> The CPU path takes ~19 s for a 256^3 volume, and a naive CuPy port dies in batched cuSolver eigvalsh at exactly the sizes that matter. The PR replaces that with a closed-form 3x3 symmetric eigensolver (Cardano), adds a CuPy backend with NumPy/SciPy fallback, and tiled/halo execution for volumes that don't fit in VRAM — 512^3 runs in ~3-5 s inside ~1 GB of GPU memory on an RTX 4090. One subtlety worth knowing about: per-block min-max normalization silently diverges from dense output by up to ~3e-2, so the tiled path computes the global smoothed range first; parity tests verify tiled == dense to 1e-4.
>
> Reproduce:
> cd foundation/datasets/fibers-dataset
> pytest tests/test_gpu.py
> python3 bench/bench_tools.py --sizes 64 128 256
> python3 bench/bench_tools.py --sizes 384 512 --tiled --skip-cpu
>
> Real-scroll contact sheet (256^3 PHerc0332 region, ~1.2 s): https://github.com/jonmarrs/vesuvius-autoresearch/blob/main/reports/real_scroll_evidence/vesselness_contact_sheet.png
>
> Specifically looking for:
> - benchmark numbers on other GPUs (especially smaller cards — does 512^3 tiled fit on 4-8 GB?);
> - parity/failure reports;
> - cases where tiled output disagrees with dense beyond the documented halo limits.

## Follow-Through Checklist

- [x] 2026-06-09: PR #1033 opened on current `ScrollPrize/villa:main` (4 tests passing, benches re-run uncontended same day).
- [x] 2026-06-10: Posted in `#code`.
- [ ] Check replies after 24 hours (by 2026-06-11).
- [ ] If silent after ~48 hours (by 2026-06-12), post a one-line pointer in the most relevant technical channel.
- [ ] Log substantive replies below with handle, timestamp, thread link, and result.

## Responses Log

*Log substantive replies or feedback here for the prize submission. PR comments from villa maintainers also count as community signal — log those here too.*

- (none yet)
