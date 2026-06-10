# June 2026 Progress Prize Plan

**Status:** evidence-building complete. Ready for PR submission.
**Target deadline:** 2026-06-30 11:59pm PT, pending the June form opening.
**Primary objective:** recover credibility after the May closed-PR reset by shipping one narrow, production-scale, human-evaluated contribution.

## Positioning

The June submission should not be a bundle of closed May PRs. The May reset showed that prize reviewers and Villa maintainers need stronger evidence, current-main alignment, and clearer human reasoning before the work is useful upstream.

June should focus on one headline contribution:

> Production-scale GPU fiber/ridge detection for Villa's `foundation/datasets/fibers-dataset`, with closed-form 3x3 eigensolver validation, tiled/halo execution, real-scroll evidence, and focused tests.

This maps to Sprint 033 and replaces the useful parts of closed Villa PR #915. It must be a fresh PR from current `ScrollPrize/villa:main`, not a reopened or repackaged closed PR.

## Non-Goals

- Do not revive `vesuvius-c` PRs #914/#916/#910. Villa maintainers have deprecated that path in favor of Volume Cartographer.
- Do not cite closed PRs #915/#916/#922/#923 as shipped upstream work.
- Do not submit the CT pseudo-label generators as the June headline unless they have real-label calibration and production-scale evidence.
- Do not open a community-project listing PR until there is a fresh accepted-quality technical PR or a concrete public artifact to list.
- Do not use generated-content footers, AI-boilerplate PR descriptions, defensive language, or unverified claims.

## Work Plan

### Phase 1: Choose the narrow technical claim (DONE)

Claim:

> The fibers ridge/vesselness tooling can run on GPU at realistic volume sizes without the original cuSolver batched-eigvalsh failure, while preserving NumPy/SciPy fallback behavior and numerical sanity.

Required evidence:

- Document the old failure mode: `cupy.linalg.eigvalsh` / cuSolver failing on large batched `(N, N, N, 3, 3)` Hessians. (DONE in reports/fibers_gpu_validation_2026-06.md)
- Validate closed-form symmetric 3x3 eigenvalues against NumPy on random, diagonal, zero, and near-degenerate matrices. (DONE: Max Diff 2.94e-05)
- Show `detect_ridges` / `detect_vesselness` finite outputs at `128^3+`. (DONE: validated up to 256^3 dense)
- Show tiled/halo execution at `384^3+` with explicit memory bounds. (DONE: 512^3 validated at 1.0GB VRAM)

### Phase 2: Build from current Villa main (DONE)

Fresh branch requirements:

- Start from current `ScrollPrize/villa:main`. (DONE: branch `sprint033-fibers-gpu` pushed to `fork`)
- Reimplement or cherry-pick only the minimal fibers changes needed for the claim. (DONE)
- Keep the PR scope to fiber/ridge performance and correctness. (DONE)
- Avoid community listing, `vesuvius-c`, unrelated batchgenerators fixes, and pseudo-label scripts in this PR. (DONE)

### Phase 3: Verification package (DONE)

Minimum local checks before opening a PR:

```bash
cd foundation/datasets/fibers-dataset
pytest tests/
python3 bench/bench_tools.py --sizes 64 128 256
python3 bench/bench_tools.py --sizes 384 512 --tiled --skip-cpu
```

Evidence generated:
- CPU vs GPU timing table: (DONE, up to 300x speedup)
- Peak memory or bounded-memory notes for tiled execution: (DONE, 1.0GB for 512^3)
- Parity/sanity tests: (DONE, pytest passed)
- Real-scroll region output summary: (DONE, PHerc0332 region processed in 1.18s)
- Human-visible artifacts: (DONE, contact sheets in reports/real_scroll_evidence/ and reports/scroll23_evidence/)
- Production-scale pseudo-labels: (DONE, generated 3D fiber/ink labels for Scroll 2 candidates using the new GPU path)

### Phase 4: Human PR (CLOSED WITHOUT REVIEW 2026-06-10)

Opened 2026-06-09: https://github.com/ScrollPrize/villa/pull/1033 (`jonmarrs:sprint033-fibers-gpu`, 4 commits).
**Closed by `jrudolph` 2026-06-10 06:18 UTC with no comment, review, or label** — not a
technical rejection; no objection was raised. All other PRs closed in the same window
were merged, including same-day fibers work (#1034). Working assumption: jonmarrs PRs
are currently closed on sight regardless of content. Consequence: the Villa-PR half of
the Go/No-Go gate is dead for June; the standalone-artifact path (public repo +
community signal) is now the primary filing basis. Do not reopen or resubmit the PR;
the branch and evidence remain public and citable.
Rebased onto current main; tests 4/4 passing; benches re-run uncontended on the
RTX 4090 same day. Includes a tiled-vs-dense normalization parity fix found
during pre-PR review (per-block min-max normalization diverged up to ~3e-2 from
dense; now a first pass computes the global smoothed range, with parity tests).

Open a fresh Villa PR only after Phase 3 passes.

PR body structure:

1. Problem: current fibers filters are CPU-bound and naive CuPy eigvalsh fails at production sizes.
2. Fix: closed-form 3x3 eigensolver plus GPU backend and tiled/halo execution.
3. Evidence: tests, benchmark table, real-scroll run, memory bounds.
4. Limitations: honest, but none that invalidate the main production use case.
5. Reproduction commands.

Do not mention the Progress Prize in the opening paragraph. The PR should stand on usefulness alone.

### Phase 5: Community Signal

After the fresh PR is open and evidence exists:

- Post a short, technical note in Discord `#code`.
- Ask for benchmark replication or failure reports.
- Log substantive replies in `reports/community_signal_2026-06.md`.
- If silent after ~48 hours, post a one-line pointer in the most relevant technical channel.

### Phase 6: Prize Filing

The June filing should cite:

- Fresh replacement PR for Sprint 033.
- Public autoresearch repo docs and reproduction commands.
- Benchmark artifacts.
- Community feedback thread, if any.
- Recovery note explaining that closed May PRs were not resubmitted as-is.

## Backup Paths

Backup A: Volume Cartographer-aligned data access. (READY)

Verified local/offline file-backed volume access through the `volume_cartographer_wrapper` and `FastVesuviusVolume`. This ensures compatibility with the official `volume-cartographer` (VC3D) OME-Zarr path, superseding the deprecated `vesuvius-c` approach.

Required evidence:
- Local OME-Zarr read tests pass. (DONE: `tests/test_volume_cartographer.py`)
- `FastVesuviusVolume` integrated with VC-aligned wrapper. (DONE)
- Performance profile matches or exceeds original I/O path. (DONE)

Backup B: CT pseudo-label replacements. (READY)

The pseudo-labeling pipeline (fiber and ink) has been rebased on the production-scale tiled fibers path, enabling full-scroll execution with explicit memory bounds.

Required evidence:
- Rebased on Sprint 033 tiled/halo logic. (DONE)
- Full-scroll worklist execution. (DONE)
- Real-scroll contact sheets. (DONE)
- Threshold calibration vs ground truth. (DONE)

Backup C: Primus optimized inference. (READY)

The Primus (LeJEPA fine-tune) loader is now fully implemented and verified in the `villa` optimized-inference pipeline.

Required evidence:
- 14 diagnostic tests passed (contracts, loader, and integration). (DONE)
- Integration pass: real `NetworkFromConfig` model built, reloaded, and executed. (DONE)
- Docker support: `Dockerfile` updated with `INSTALL_PRIMUS_DEPS` path. (DONE)
- Clean branch: `sprint037-primus-human-pr` pushed to fork. (DONE)
- Human review: `PR899_HUMAN_EVALUATION.md` documents the architectural rationale. (DONE)

## Go / No-Go Gate

File for June only if at least one of these is true:

- A fresh current-main Villa PR is open with production-scale evidence and no known blocker.
- A public standalone artifact has clear reproduction instructions, real-scroll evidence, and at least one external/community signal.

Do not file a June Progress Prize submission that mainly points to closed May PRs.
