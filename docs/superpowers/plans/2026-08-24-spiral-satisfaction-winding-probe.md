# Spiral Satisfaction Winding-Blindness Probe — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Determine whether villa's spiral-fit satisfaction metric can detect a patch placed exactly one winding away from where it belongs — the "sheet switch" failure mode the maintainers rank fourth in their own bottleneck table.

**Architecture:** Two legs. A synthetic leg builds an analytic spiral and a hand-constructed patch, scores it with villa's own unmodified `get_patch_satisfied_areas`, displaces it by exactly one winding in spiral space, and rescores. A real-data leg repeats the displacement on a fitted checkpoint from the public `spiral-input` dataset. The synthetic leg is decisive for the *property* and needs no GPU and no downloads; the real leg establishes that it matters in practice. A sensitivity control runs in both legs and is what makes the null interpretable.

**Tech Stack:** Python, PyTorch (CPU for the synthetic leg), villa's `volume-cartographer/scripts/spiral/` modules imported unmodified, rclone for the real-data pull.

**Spec:** This document doubles as the pre-registration. It must be committed **before** any measurement in Task 2 or later runs. That commit is what makes the gate below binding.

---

## Pre-registration

Stated before any number is produced.

**Hypothesis (H1).** `get_patch_satisfied_areas` is invariant under a displacement of exactly one winding. A patch moved onto the adjacent wrap scores the same satisfied-quad fraction as the correctly placed patch.

**Why we expect it.** Reading `satisfaction_metrics.py`, both satisfaction conditions are constructed relative to a target that is itself derived from the patch's own position:

- Condition (a), spiral-space: the per-patch target is `round(median_shifted_radius / dr) * dr`. Adding `dr` to every point's shifted radius adds `dr` to the median, which adds `dr` to the snapped target. The residual `adjusted_shifted - target_shifted_radius` is unchanged.
- Condition (b), scan-space: the target point is rebuilt at the *same theta and z* with the new target radius, then inverted to scan space. Both the patch and its target move outward by `dr`, so `target_scan - orig_scan` is unchanged.

Neither condition ever reads an annotated winding number. `winding_is_absolute` appears in `fit_spiral.py` and `spiral_helpers.py` but **never** in `satisfaction_metrics.py`.

**Primary outcome.** `satisfied_quad_fraction` for the displaced patch minus the same quantity for the reference patch.

**Pre-registered gate.**

| Result | Interpretation |
| --- | --- |
| \|Δ satisfied fraction\| ≤ 1e-6 **and** the control in Task 3 shows a drop > 0.5 | **H1 confirmed.** The metric is blind to one-winding displacement. Finding is real; proceed to write it up. |
| \|Δ satisfied fraction\| > 1e-6 | **H1 falsified.** The metric detects the displacement. Report the negative, drop the lane, do not publish a claim. |
| Control shows no drop | **Probe is uninformative.** The instrument is not exercising the metric at all. Fix the harness before interpreting anything. |

**The control is not optional.** A null from a probe that cannot produce a non-null is worthless. Task 3 must demonstrate the metric *does* move before the Task 2 null means anything. This is the lesson from `reports/fiber_tracer_improvement.md` — audit the favourable number hardest.

**Disclosed in the report regardless of outcome:** both satisfaction conditions separately (not just the combined flag), the control curve, the exact villa commit scored against, and the fact that the synthetic leg is synthetic.

**What this probe does NOT claim.** It says nothing about whether spiral fits in practice *do* misplace patches by a winding, nor about the quality of any fit. It is a statement about what the metric can and cannot detect, nothing more.

## Global Constraints

- villa is a submodule pinned at `ced62390e`. Do **not** modify anything under `villa/`. The probe imports villa code unmodified and lives in our repo.
- Spiral fitting moved to a top-level `spiral-fitting/` directory on villa main as of 2026-08-21 (PR #1548). Our pin still has it at `villa/volume-cartographer/scripts/spiral/`. Any eventual upstream-facing writeup must reference the **new** path; the probe reads the pinned one.
- Synthetic leg must run on CPU with no network. Set `CUDA_VISIBLE_DEVICES=""`.
- No AI-authorship markers in any commit message, file, or eventual comment. Commit trailers use `Co-Authored-By` only.
- Probe scripts follow the precedent of `scripts/probe_skel_dist_validity.py`: a module docstring stating what is being probed and what the outcomes mean, and a `Run:` line.

---

### Task 1: Free disk and confirm the environment

Only Task 4 (real data) depends on this. Tasks 2 and 3 can run first and should — they are the decisive ones.

**Files:**
- Modify: none (this task is environment work)

**Interfaces:**
- Consumes: nothing
- Produces: ≥ 150 GB free on `/`, a working `nvidia-smi`

- [ ] **Step 1: Confirm what is safe to delete**

Two targets were verified during the spike. Do not widen this list without re-checking availability.

```bash
du -sh /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/PHercParis2Fr47/0/
du -sh /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection/outputs/vesuvius/
curl -sI --max-time 20 "https://dl.ash2txt.org/fragments/Frag1/PHercParis2Fr47.volpkg/working/54keV_exposed_surface/surface_volume/00.tif" -o /dev/null -w "%{http_code}\n"
```

Expected: `116G`, `17G`, `200`.

- [ ] **Step 2: Delete, largest first**

```bash
rm -rf /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/PHercParis2Fr47/0/
rm -rf /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/ink-detection/outputs/vesuvius/
df -h /
```

Expected: `Avail` rises from ~92 GB to ~225 GB.

**Never delete these** — checked during the spike and each is load-bearing:

| Path | Size | Why it stays |
| --- | --- | --- |
| `villa/ink-detection/train_scrolls/20231210121321/` | 16 GB | The held-out ScrollGT pixel target — the single usable hand-labelled Scroll-1 segment |
| `villa/ink-detection/all_labels/` | 45 MB | GT source for the detector |
| `local_data/fiber_skeletons/` | 3.1 GB | ScrollGT fiber targets |
| `local_data/sota_gt/`, `sota_distill*/`, `rendered_1667/`, `sota_xscroll/` | ~8.6 GB | Registered-GT and column-target inputs |

`memory/gt-training-data-exhausted.md` records that three labelled segments are **absent** from open data. "We can download it again" does not hold for `train_scrolls/`. It does hold for Fr47, which is why Fr47 is on the list and `train_scrolls/` is not.

- [ ] **Step 3: Fix the GPU driver**

```bash
nvidia-smi
```

Currently fails with `Driver/library version mismatch` (NVML 595.84). This is a loaded-kernel-module vs userspace-library mismatch after a driver update, and the fix is a reboot — **Jon runs this, not the agent.** No fitting happens until `nvidia-smi` prints the 4090.

- [ ] **Step 4: Commit nothing**

This task changes no tracked files. Do not commit.

---

### Task 2: Synthetic invariance probe

The decisive test. No GPU, no downloads, no fitted checkpoint.

**Files:**
- Create: `scripts/probe_spiral_satisfaction_winding.py`
- Create: `tests/test_probe_spiral_satisfaction_winding.py`

**Interfaces:**
- Consumes: `get_patch_satisfied_areas` from villa, unmodified
- Produces: `build_synthetic_patch(dr, winding, n_rows, n_cols, theta0, theta1, z0, dz) -> SyntheticPatch`, `IdentityTransform`, `score(patch, dr) -> float` returning the satisfied-quad fraction, and `displace(patch, dr, n_windings) -> SyntheticPatch`

- [ ] **Step 1: Verify the villa import chain works standalone**

`satisfaction_metrics.py` imports from `sample_spiral`, `spiral_helpers`, `tracks`, and `visualization`. Confirm those resolve on CPU before writing the probe, because a heavy transitive dependency would change the approach.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run python -c "
import sys; sys.path.insert(0, 'villa/volume-cartographer/scripts/spiral')
from satisfaction_metrics import get_patch_satisfied_areas, metrics_config
print('ok', metrics_config)
"
```

Expected: `ok {'satisfaction_radius_tolerance': 0.45, ...}`.

If this fails on a missing dependency, record the exact ImportError in the report and add the minimal stub to `sys.modules` before the import — do not edit villa.

- [ ] **Step 2: Write the failing test**

```python
# tests/test_probe_spiral_satisfaction_winding.py
"""The probe's own harness must be correct before its null means anything."""
import os
import sys

os.environ["CUDA_VISIBLE_DEVICES"] = ""
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

import numpy as np
import pytest
import torch

from probe_spiral_satisfaction_winding import (
    DR,
    build_synthetic_patch,
    displace,
    score,
)


def test_reference_patch_is_fully_satisfied():
    """A patch built exactly on winding 5 must score 1.0, or the harness is wrong."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    assert score(patch, DR) == pytest.approx(1.0, abs=1e-9)


def test_displacement_is_exactly_one_winding():
    """displace() must move every point's shifted radius by exactly dr."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    moved = displace(patch, DR, n_windings=1)
    sys.path.insert(0, os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral"))
    from sample_spiral import get_theta_and_radii

    dr_t = torch.tensor(DR)
    _, _, before = get_theta_and_radii(patch.zyxs[..., 1:], dr_t)
    _, _, after = get_theta_and_radii(moved.zyxs[..., 1:], dr_t)
    assert torch.allclose(after - before, torch.full_like(before, DR), atol=1e-4)
```

- [ ] **Step 3: Run it to confirm it fails**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run pytest tests/test_probe_spiral_satisfaction_winding.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'probe_spiral_satisfaction_winding'`.

- [ ] **Step 4: Write the probe**

```python
# scripts/probe_spiral_satisfaction_winding.py
"""Probe whether villa's spiral-fit satisfaction metric can detect a patch placed
exactly one winding away from where it belongs.

`satisfaction_metrics.get_patch_satisfied_areas` decides whether a patch is
"satisfied" against a target winding it derives from the patch's OWN median
shifted-radius (snapped to the nearest integer winding). It never reads the
absolute winding annotations that `fit_spiral.get_patch_abs_winding_loss` uses to
fit. This script measures the consequence:

    reference patch, on winding 5      -> satisfied fraction 1.00
    displaced by exactly 1 winding     -> satisfied fraction 1.00   <- blind
    displaced by 0.5 winding (control) -> satisfied fraction drops  <- metric works

The 0.5-winding control is what makes the null interpretable: it shows the
instrument is capable of reporting dissatisfaction at all.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_winding.py
"""

import os
import sys
from dataclasses import dataclass

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np
import torch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPIRAL = os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
sys.path.insert(0, _SPIRAL)

from satisfaction_metrics import get_patch_satisfied_areas  # noqa: E402

DR = 100.0
Z_BEGIN = 0
Z_END = 100000


class IdentityTransform:
    """The synthetic scroll is built directly in spiral space, so scan == spiral."""

    def __call__(self, zyx):
        return zyx

    def inv(self, zyx):
        return zyx


@dataclass
class SyntheticPatch:
    zyxs: torch.Tensor          # (H, W, 3) float32
    valid_quad_mask: torch.Tensor  # (H-1, W-1) bool
    area: float


def build_synthetic_patch(dr, winding, n_rows=12, n_cols=16,
                          theta0=0.30, theta1=1.30, z0=1000.0, dz=2.0):
    """A patch lying exactly on `winding`.

    get_theta_and_radii defines shifted_radius = radius - theta/(2pi)*dr, so a
    point with radius = winding*dr + theta/(2pi)*dr has shifted_radius exactly
    winding*dr. theta stays well inside (0, 2pi) so no theta=0 seam is crossed.
    """
    thetas = torch.linspace(theta0, theta1, n_cols, dtype=torch.float32)
    radii = winding * dr + thetas / (2 * np.pi) * dr
    ys = torch.sin(thetas) * radii
    xs = torch.cos(thetas) * radii
    zs = z0 + dz * torch.arange(n_rows, dtype=torch.float32)

    zyxs = torch.empty([n_rows, n_cols, 3], dtype=torch.float32)
    zyxs[..., 0] = zs[:, None]
    zyxs[..., 1] = ys[None, :]
    zyxs[..., 2] = xs[None, :]
    return SyntheticPatch(
        zyxs=zyxs,
        valid_quad_mask=torch.ones([n_rows - 1, n_cols - 1], dtype=torch.bool),
        area=1.0,
    )


def displace(patch, dr, n_windings):
    """Move every point radially outward by n_windings * dr, at fixed theta and z.

    This is the physically meaningful displacement: it places the patch where the
    adjacent wrap sits. Fractional n_windings are used for the control.
    """
    zyxs = patch.zyxs.clone()
    ys = zyxs[..., 1]
    xs = zyxs[..., 2]
    radii = torch.sqrt(ys ** 2 + xs ** 2)
    thetas = torch.arctan2(ys, xs) % (2 * np.pi)
    new_radii = radii + n_windings * dr
    zyxs[..., 1] = torch.sin(thetas) * new_radii
    zyxs[..., 2] = torch.cos(thetas) * new_radii
    return SyntheticPatch(
        zyxs=zyxs,
        valid_quad_mask=patch.valid_quad_mask.clone(),
        area=patch.area,
    )


def score(patch, dr):
    """Satisfied-quad fraction under villa's unmodified metric."""
    _, _, _, masks, _, _ = get_patch_satisfied_areas(
        IdentityTransform(),
        torch.tensor(dr),
        [patch],
        Z_BEGIN,
        Z_END,
    )
    mask = masks[0]
    total = int(patch.valid_quad_mask.sum().item())
    return int(mask.sum().item()) / max(total, 1)


def main():
    ref = build_synthetic_patch(dr=DR, winding=5)
    ref_score = score(ref, DR)
    print(f"reference (winding 5)          satisfied = {ref_score:.6f}")

    moved = displace(ref, DR, n_windings=1)
    moved_score = score(moved, DR)
    print(f"displaced by 1 winding         satisfied = {moved_score:.6f}")
    print(f"delta                                    = {moved_score - ref_score:+.6e}")

    print()
    print("control sweep (fractional displacements):")
    for frac in [0.0, 0.25, 0.40, 0.50, 0.60, 0.75, 1.0, 2.0]:
        s = score(displace(ref, DR, n_windings=frac), DR)
        print(f"  {frac:5.2f} winding  satisfied = {s:.6f}")


if __name__ == "__main__":
    main()
```

- [ ] **Step 5: Run the tests until they pass**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run pytest tests/test_probe_spiral_satisfaction_winding.py -v
```

Expected: 2 passed. If `test_reference_patch_is_fully_satisfied` fails, the harness is wrong — the geometry does not put the patch on a winding. Fix that before reading any delta; a broken reference makes the whole probe meaningless.

- [ ] **Step 6: Run the probe and record the output verbatim**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_spiral_satisfaction_winding.py | tee reports/spiral_satisfaction_winding_probe.txt
```

Do not interpret yet. Task 3 decides whether the number means anything.

- [ ] **Step 7: Commit**

```bash
git add scripts/probe_spiral_satisfaction_winding.py tests/test_probe_spiral_satisfaction_winding.py reports/spiral_satisfaction_winding_probe.txt
git commit -m "probe: does spiral satisfaction detect a one-winding displacement

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Sensitivity control — prove the instrument can say no

Without this, the Task 2 null is indistinguishable from a broken harness.

**Files:**
- Modify: `tests/test_probe_spiral_satisfaction_winding.py`

**Interfaces:**
- Consumes: `build_synthetic_patch`, `displace`, `score`, `DR` from Task 2
- Produces: nothing new — this task adds assertions only

- [ ] **Step 1: Write the failing control test**

```python
def test_metric_does_detect_a_half_winding_displacement():
    """The control. A half-winding offset sits outside the 0.45*dr tolerance,
    so the metric MUST reject it. If this passes as satisfied, the probe is not
    exercising the metric and the one-winding null means nothing."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    half = displace(patch, DR, n_windings=0.5)
    assert score(half, DR) < 0.5


def test_metric_does_not_detect_a_whole_winding_displacement():
    """The finding itself, pinned as a regression test."""
    patch = build_synthetic_patch(dr=DR, winding=5)
    whole = displace(patch, DR, n_windings=1.0)
    assert abs(score(whole, DR) - score(patch, DR)) <= 1e-6
```

- [ ] **Step 2: Run them**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
CUDA_VISIBLE_DEVICES="" uv run pytest tests/test_probe_spiral_satisfaction_winding.py -v
```

Expected: 4 passed.

**Read the gate now, not before.** If the half-winding control does *not* drop below 0.5, stop — the harness is not exercising the metric, and no conclusion may be drawn. If the control drops and the whole-winding delta is ≤ 1e-6, H1 is confirmed.

- [ ] **Step 3: Commit**

```bash
git add tests/test_probe_spiral_satisfaction_winding.py
git commit -m "test: sensitivity control for the winding-displacement probe

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Real-data leg

Requires Task 1 complete (disk + GPU). Runs only if Tasks 2 and 3 confirmed H1 — there is nothing to corroborate otherwise.

**Files:**
- Create: `scripts/probe_spiral_satisfaction_real.py`
- Create: `reports/spiral_satisfaction_winding_real.md`

**Interfaces:**
- Consumes: a fitted checkpoint, `displace` from Task 2
- Produces: `load_fitted(checkpoint_path) -> (transform, dr_per_winding)`, reusing `find_inconsistent_windings.py`'s loader pattern at lines 226–256

- [ ] **Step 1: Pull only what is needed**

The full dataset is ~90 GB; the annotation truth is 2.5 MB. Pull the small pieces first and confirm a fit is even possible before committing the bulk.

```bash
mkdir -p /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/spiral_phercparis4
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/spiral_phercparis4
for f in abs_winding.json relative_windings.json same_windings.json umbilicus.json; do
  curl -sO --max-time 120 "https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/$f"
done
ls -la
```

Expected: four files, ~2.5 MB total (`abs_winding.json` ≈ 20 KB, `relative_windings.json` ≈ 774 KB, `same_windings.json` ≈ 1.7 MB, `umbilicus.json` ≈ 12 KB).

- [ ] **Step 2: Pull the patches and shell**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/local_data/spiral_phercparis4
rclone copy :http: ./ --http-url https://dl.ash2txt.org/datasets/spiral_datasets/PHercParis4/ \
  --include "verified_patches/**" --include "outer_shell/**" --progress
du -sh verified_patches outer_shell
df -h /
```

Stop and reassess if this exceeds 60 GB — the lasagna volume inputs can be skipped by setting their paths to `None` per `docs/38_tutorial_spiral.md`, but patches are mandatory.

- [ ] **Step 3: Fit a short spiral over a narrow z-range**

Fit quality does not matter — the claim is about the metric, not the fit. A narrow z-range keeps this cheap.

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch/villa/volume-cartographer/scripts/spiral
# Edit dataset_path and the z-range constants at the top of fit_spiral.py to point at
# local_data/spiral_phercparis4 with --z-range 10000,11000, then:
uv run python fit_spiral.py 2>&1 | tee /tmp/claude-1000/-home-jon-openclaw-workspace-Neo-VM-projects-vesuvius-autoresearch/19faecff-47a9-4b76-b3ab-dc6bb8da304d/scratchpad/fit.log
```

Expected: a `checkpoint_fitted.ckpt` plus printed satisfaction metrics. Record the baseline satisfied fractions per input type.

- [ ] **Step 4: Displace one real patch and rescore**

```python
# scripts/probe_spiral_satisfaction_real.py
"""Real-data leg of the winding-blindness probe: displace one real patch from a
fitted PHercParis4 spiral by exactly one winding and rescore it with villa's own
satisfaction metric.

Run:
    uv run python scripts/probe_spiral_satisfaction_real.py --checkpoint <path>
"""

import argparse
import os
import sys

import torch

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_SPIRAL = os.path.join(_REPO, "villa", "volume-cartographer", "scripts", "spiral")
sys.path.insert(0, _SPIRAL)

from satisfaction_metrics import get_patch_satisfied_areas  # noqa: E402
import fit_spiral as fs  # noqa: E402


def load_fitted(checkpoint_path):
    """Mirrors find_inconsistent_windings.py lines 226-256."""
    model = fs.load_model_from_checkpoint(checkpoint_path)
    return model.get_slice_to_spiral_transform(), model.get_dr_per_winding()


def displace_in_spiral_space(patch_zyxs, transform, dr, n_windings):
    """Move the patch to the adjacent wrap: convert to spiral space, add
    n_windings*dr radially at fixed theta and z, convert back."""
    flat = patch_zyxs.reshape(-1, 3)
    spiral = transform(flat)
    ys, xs = spiral[..., 1], spiral[..., 2]
    radii = torch.sqrt(ys ** 2 + xs ** 2)
    thetas = torch.arctan2(ys, xs)
    new_radii = radii + n_windings * dr
    moved = torch.stack([
        spiral[..., 0],
        torch.sin(thetas) * new_radii,
        torch.cos(thetas) * new_radii,
    ], dim=-1)
    return transform.inv(moved).reshape(patch_zyxs.shape)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--checkpoint", required=True)
    ap.add_argument("--z-begin", type=int, default=10000)
    ap.add_argument("--z-end", type=int, default=11000)
    args = ap.parse_args()

    transform, dr = load_fitted(args.checkpoint)
    patches = fs.load_patches_for_probe(args.z_begin, args.z_end)
    target = patches[0]

    def frac(p):
        _, _, _, masks, _, _ = get_patch_satisfied_areas(
            transform, dr, [p], args.z_begin, args.z_end)
        return int(masks[0].sum().item()) / max(int(p.valid_quad_mask.sum().item()), 1)

    print(f"reference             satisfied = {frac(target):.6f}")
    for n in [0.5, 1.0]:
        moved = type(target)(
            zyxs=displace_in_spiral_space(target.zyxs, transform, dr, n),
            valid_quad_mask=target.valid_quad_mask,
            area=target.area,
        )
        print(f"displaced {n:4.2f} winding  satisfied = {frac(moved):.6f}")


if __name__ == "__main__":
    main()
```

`fs.load_model_from_checkpoint` and `fs.load_patches_for_probe` are placeholders for whatever `fit_spiral.py` actually exposes — **read `find_inconsistent_windings.py` lines 200–260 and copy its real loader calls before running this.** That file does exactly this job and is the reference implementation.

- [ ] **Step 5: Run and record**

```bash
cd /home/jon/openclaw-workspace/Neo-VM/projects/vesuvius-autoresearch
uv run python scripts/probe_spiral_satisfaction_real.py --checkpoint <path> | tee reports/spiral_satisfaction_winding_real.txt
```

Expected if H1 holds: the 1.0-winding row matches the reference to ~1e-6; the 0.5 row drops.

- [ ] **Step 6: Commit**

```bash
git add scripts/probe_spiral_satisfaction_real.py reports/spiral_satisfaction_winding_real.txt
git commit -m "probe: real-data leg of the winding-displacement probe

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: Write the report, decide whether anything goes outward

**Files:**
- Create: `reports/spiral_satisfaction_winding_blindness.md`

**Interfaces:**
- Consumes: outputs of Tasks 2, 3, 4
- Produces: the report; no outward action

- [ ] **Step 1: Write the report**

Required sections, matching `reports/fiber_tracer_improvement.md` house style:

1. Bottom line up front, including the outcome even if negative.
2. The pre-registered gate as stated here, verbatim, and whether it was met.
3. Both satisfaction conditions reported separately.
4. The control sweep as a table.
5. Limits, stated plainly: the synthetic leg is synthetic; the probe says nothing about how often real fits misplace patches; villa commit `ced62390e` is what was scored, and spiral fitting has since moved to `spiral-fitting/` upstream.
6. What would change the conclusion.

- [ ] **Step 2: Commit**

```bash
git add reports/spiral_satisfaction_winding_blindness.md
git commit -m "report: spiral satisfaction winding-blindness probe result

Co-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>"
```

- [ ] **Step 3: Stop. Do not post anything.**

Whether this becomes an upstream issue, a #191-style comment, or a September Progress Prize submission is **Jon's call**, made after reading the report. `memory/no-reviewer-nudges-quality-over-volume.md` and `memory/villa-prs-closed-on-sight.md` both apply. The substance test comes before any outward action.

---

## Self-Review

**Spec coverage.** The pre-registration names one hypothesis, one primary outcome, one gate, and one control. Task 2 produces the outcome, Task 3 produces the control and reads the gate, Task 4 corroborates on real data, Task 5 reports. Task 1 is a prerequisite for Task 4 only, and is explicitly marked as not blocking the decisive tasks.

**Placeholder scan.** One deliberate placeholder remains and is flagged in-line: `fs.load_model_from_checkpoint` / `fs.load_patches_for_probe` in Task 4, because the real loader entry points live in `find_inconsistent_windings.py` and must be read from the pinned source at execution time rather than guessed here. Every other step carries runnable content.

**Type consistency.** `build_synthetic_patch`, `displace`, `score`, and `DR` are defined in Task 2 Step 4 and used under those exact names in Tasks 3 and 4. `SyntheticPatch` exposes `zyxs`, `valid_quad_mask`, and `area` — the three attributes `get_patch_satisfied_areas` reads. `displace` takes `n_windings` as a float in both legs.

**Known risk.** Task 2 Step 1 exists because `satisfaction_metrics.py` has four transitive villa imports and one of them (`visualization`) may pull a plotting stack. If the import chain fails, that is discovered in the first two minutes rather than after the probe is written.
