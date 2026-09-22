# POSTED 2026-09-22 as villa PR #1866 — https://github.com/ScrollPrize/villa/pull/1866

> Approved by the user, verified, and posted. Landed as **1 file, +2/−0**, branch
> `jonmarrs:flatten-determinism-note`, zero AI-authorship markers. The pinned submodule never
> moved: the commit was built with a temporary index so the running chain's `be09a8503` checkout
> was untouched. Open PRs now 2 of villa's 3-open cap (#1842, #1866).
>
> Prior-art search done at post time: #1317 reports the same class of problem in the **tracer**
> (`vc_grow_seg_from_seed`), with an RNG seed knob the flatten does not have. Complementary, not
> duplicate, and cited in the body.

**Target:** `spiral-fitting/autoresearch.md`, the `**Stochasticity**` paragraph (line 52).
**Shape:** one doc paragraph, ~6 lines added, no behaviour change. Same shape as #1721 and #1722,
both of which merged.
**Slots:** villa caps at 3 open PRs; #1842 is open, #1723 and #1728 were auto-closed by the
inactivity bot on 2026-09-22, so two slots are free. New-PR budget is 1/week.

---

## Why this one

`autoresearch.md` already tells the reader the code "is sensitive to the random seed **and CUDA
non-determinism**" and to prefer changes robust across "seeds/runs". That is correct and this PR does
not contradict it. What the paragraph does not say is **where** the CUDA half lives, **how big** it
is, or that it can be **switched off** — and all three change how the prescribed two-run check should
be read.

## The proposed addition

> **CORRECTION 2026-09-22, after this was posted as villa PR #1866.** "Land on surfaces about 7 voxels
> apart" and "7.15 vx … 6.6–7.3 vx" below misdescribe the geometry. The flattens lie on the **same
> surface** (0.25 vx apart along the normal) and differ by a ~7 vx **in-plane re-parametrisation**
> (`reports/the_flatten_moves_the_grid_not_the_surface.md`). The 3.04%, the cause and the switch are
> unaffected. A correction comment is drafted in `docs/VILLA_PR_1866_CORRECTION_DRAFT.md` and is
> **NOT posted**: that needs the owner's approval.

> The CUDA half of that is the **lasagna flatten**, and it is larger than it looks. Two renders of
> byte-identical meshes on one commit, same GPU, same code, land on surfaces about **7 voxels apart**
> and differ by **3.04%** on `total_fg_pixels` — the scorer itself contributes 0.003%, so almost none
> of it is downstream of the flatten. There is no seed for it: the flatten has no RNG on its path, and
> the variation is floating-point reduction order. Setting
> `torch.use_deterministic_algorithms(True)` with `CUBLAS_WORKSPACE_CONFIG=:4096:8` makes two flattens
> of one mesh set produce **byte-identical** `x/y/z.tif`, at roughly **9.5× the flatten time** (~11
> min instead of ~4 on one 4090, against a ~2 h render). Worth doing when a comparison manipulates a
> *fixed* surface; it does **not** tighten comparisons between different fits, where the seed's own
> variation dominates.

## Evidence for the PR body

* **Non-determinism**: two renders, one mesh set (md5-identical tifs), one commit, byte-identical
  `render_ink.py` → `total_fg_pixels` 1,698,831 vs 1,750,482 (**+3.04%**); nearest-neighbour distance
  between the two flattened surfaces **7.15 vx** mean (p50 7.34, p90 10.75) in `w120–w129`, and
  **0.535 vx** in `w010–w019`.
* **Not the scorer**: re-scoring one fixed strip three times moves the count **0.0032%** — ~950× too
  little to explain the above.
* **No RNG to seed**: `fit.py`, `optimizer.py`, `model.py` contain no `manual_seed`/`randn`/`rand(`/
  `randint`/`shuffle`/`permutation`/`np.random`/`torch.rand`; every "seed" on that path is a
  geometric one (`cylinder_seed`, `seed_xyz`). What is present is 174 scatter/atomic call sites,
  `grid_sample`, and a fused Triton kernel, with determinism never requested.
* **The fix works**: with `use_deterministic_algorithms(True, warn_only=True)` +
  `CUBLAS_WORKSPACE_CONFIG=:4096:8`, two flattens of one mesh set gave **md5-identical** `x.tif`,
  `y.tif`, `z.tif`; loss matched at every logged step; **zero** "does not have a deterministic
  implementation" warnings on torch 2.11.0+cu128.
* **Cost**: stage0 throughput 16.4 it/s vs ~155 stock, measured at matched steps across four runs.
* **The limit, stated up front**: this buys *reproducibility*, not correctness — a deterministic
  flatten lands 6.6–7.3 vx from *both* stock surfaces, i.e. it fixes one reduction order and picks an
  arbitrary member of the same distribution. And six seeds re-flattened deterministically give a CV of
  **0.09 [0.06, 0.22]**, statistically indistinguishable from the same six with stock flattens
  (F(5,5) p=0.67), so it does not make fit comparisons cheaper.

## Pre-post checks

- [x] every number traced to a committed report, not to memory
- [x] the paragraph's existing claim ("sensitive to … CUDA non-determinism") is **acknowledged as
      already correct**, not presented as missing — an earlier draft here overstated that and was
      corrected 2026-09-21
- [x] no AI-authorship markers anywhere in the branch or body
- [x] measured on one machine / one GPU / torch 2.11 — said in the body, since deterministic CUDA is
      deterministic *per configuration*
- [ ] **user approval to post** — not sought yet
- [ ] villa's own `test_flatten_state_handoff.py` covers *export* determinism, not optimisation
      determinism; worth one sentence in the PR conversation if a reviewer raises it
