"""Does villa's metric satisfy a REAL traced patch, and can the test patch be built from one?

PRE-REGISTERED. Committed before the run, decision rule included.

WHY. Every number in the winding-blindness report is measured on a synthetic
patch placed exactly on a winding. `reports/exceedance_denominator.txt` had to
disclose that its degenerate class was empty by construction for that reason,
and closed by saying: whether a REAL traced patch is satisfied at zero scatter
is a different question, not asked anywhere. This asks it.

It matters two ways. If real patches are satisfied, the report's reference
condition transfers and the blindness describes a situation villa actually
encounters. If they are not, then villa's metric rejects them on their own
merits, displaced or not, and the practical reach of the finding is narrower
than the report implies -- the exact algebra would still hold, but it would
describe patches that do not occur.

THE SCALE PROBLEM, which is half the point of this probe. The synthetic patch
is 12x16 cells spanning about 22 x 66 voxels: 165 quads over a small area,
because its cells are 2.0 and 4.4 voxels apart. Real traced patches are sampled
at about 20 voxels per cell. So a real window cannot match both at once:

    matching EXTENT   (2x4 cells, 20 x 60 vox) gives 3 quads, not 165
    matching QUADS    (12x16 cells, 165 quads) spans 220 x 300 vox, 10x the area

Both are measured here, and the disagreement between them is reported as a
result rather than resolved by picking one. The report's claim that a 3x4-cell
window is "comparable to the synthetic patch" matches extent in one axis only,
and that has never been stated with the quad count beside it.

METHOD. Take fully valid windows from real traced patches, translate them into
the umbilicus-centred frame villa's metric expects (subtracting the umbilicus
position interpolated at each point's own z), and score them with villa's
unmodified `get_patch_satisfied_areas` at the published median winding spacing.
Then displace by one whole winding and score again. No synthetic geometry is
involved anywhere.

DECISION RULE, fixed in advance, on the EXTENT-matched windows since those are
what the report treats as comparable:

  * If at least half of real windows are satisfied, the reference condition
    transfers: the report's synthetic patch is not unrepresentative in this
    respect, and the blindness describes a reachable situation.
  * If fewer than half are satisfied, the report must carry the qualification
    that real patches at this scale are mostly rejected by villa's metric
    anyway, which bounds how much the blindness can matter in practice.
  * The whole-winding verdict comparison is reported alongside in both cases.
    On the algebra of section 1 it should be identical for any patch lying on a
    winding; a real patch does not lie exactly on one, so this is a genuine
    test rather than a restatement.

WHAT THIS CANNOT DO. `dr` is taken as the published median 12.81 voxels rather
than fitted per patch, so a patch sitting where the local spacing differs is
scored against a spacing it does not have. The real spacing varies 11.32 to
16.74 across shards, so this is a real limitation and the sensitivity to it is
swept rather than assumed.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_real_patch_satisfaction.py
"""

import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402
import torch  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

from probe_real_patch_scatter import (  # noqa: E402
    load_patch,
    load_umbilicus,
    patch_dirs,
)
from probe_spiral_satisfaction_robustness import _patch_is_satisfied  # noqa: E402
from probe_spiral_satisfaction_splicing_and_seam import (  # noqa: E402
    REPORTING,
    score_with,
)
from probe_spiral_satisfaction_winding import (  # noqa: E402
    IdentityTransform,
    SyntheticPatch,
    displace,
)

REAL_DR = 12.81
DR_SWEEP = [11.32, 12.81, 16.74]
EXTENT_MATCHED = (2, 4)
QUAD_MATCHED = (12, 16)
N_WINDOWS = 60
SEED = 20260826
SATISFIED_SHARE_LIMIT = 0.50
OUT = os.path.join(_REPO, "reports", "real_patch_satisfaction.txt")


def real_windows(shape, n_windows=N_WINDOWS, seed=SEED):
    """Fully valid windows of real traced patches, in the umbilicus-centred frame.

    Pooled across patches with a per-patch cap. The outer-loop break that made a
    ten-patch statistic into a one-patch statistic elsewhere in this series is
    the reason the cap is here rather than a global quota.
    """
    h, w = shape
    uz, ux, uy = load_umbilicus()
    rng = np.random.default_rng(seed)
    dirs = list(patch_dirs())
    per_patch = max(1, n_windows // max(1, len(dirs)))
    out = []
    for d in dirs:
        xs, ys, zs, valid = load_patch(d)
        if valid.shape[0] < h or valid.shape[1] < w:
            continue
        got = 0
        for _ in range(4000):
            i = int(rng.integers(0, xs.shape[0] - h + 1))
            j = int(rng.integers(0, xs.shape[1] - w + 1))
            if not valid[i : i + h, j : j + w].all():
                continue
            X = xs[i : i + h, j : j + w]
            Y = ys[i : i + h, j : j + w]
            Z = zs[i : i + h, j : j + w]
            zyxs = torch.zeros(h, w, 3, dtype=torch.float32)
            zyxs[..., 0] = torch.tensor(Z, dtype=torch.float32)
            zyxs[..., 1] = torch.tensor(Y - np.interp(Z, uz, uy), dtype=torch.float32)
            zyxs[..., 2] = torch.tensor(X - np.interp(Z, uz, ux), dtype=torch.float32)
            out.append(
                (
                    os.path.basename(d),
                    SyntheticPatch(
                        zyxs=zyxs,
                        valid_quad_mask=torch.ones([h - 1, w - 1], dtype=torch.bool),
                        area=1.0,
                    ),
                )
            )
            got += 1
            if got >= per_patch:
                break  # inner loop only
    return out


def score_windows(windows, dr):
    """Satisfied fraction and verdict, correctly placed and displaced one winding."""
    rows = []
    for _, patch in windows:
        total = int(patch.valid_quad_mask.sum().item())
        a = score_with(patch, dr, REPORTING, IdentityTransform())
        moved = displace(patch, dr, n_windings=1.0)
        b = score_with(moved, dr, REPORTING, IdentityTransform())
        thresh = REPORTING["satisfied_patch_quad_fraction"]
        rows.append(
            (
                a,
                b,
                _patch_is_satisfied(a, total, thresh),
                _patch_is_satisfied(b, total, thresh),
            )
        )
    return rows


def summarise(rows):
    if not rows:
        return None
    a = np.array([r[0] for r in rows])
    sat = np.array([r[2] for r in rows])
    differ = np.array([r[2] != r[3] for r in rows])
    delta = np.array([abs(r[1] - r[0]) for r in rows])
    return {
        "n": len(rows),
        "frac_p50": float(np.median(a)),
        "satisfied": float(sat.mean()),
        "verdict_differs": float(differ.mean()),
        "max_delta": float(delta.max()),
    }


def main():
    lines = [
        "Does villa's metric satisfy a REAL traced patch?",
        "",
        "Every number in the winding-blindness report is measured on a synthetic patch",
        "placed exactly on a winding. This scores villa's unmodified function on real",
        "traced geometry instead, in the umbilicus-centred frame, with no synthetic",
        "patch involved.",
        "",
        "=== The scale problem, which cannot be resolved, only stated ===",
        "  The synthetic patch is 12x16 cells over about 22 x 66 voxels: 165 quads in a",
        "  small area, because its cells sit 2.0 and 4.4 voxels apart. Real traced patches",
        "  are sampled at about 20 voxels per cell, so a real window matches extent or quad",
        "  count, never both.",
        "",
        "   window        cells     quads   extent (vox)",
        "  " + "-" * 58,
        "   synthetic     12x16       165   ~22 x 66",
        f"   extent-matched {EXTENT_MATCHED[0]}x{EXTENT_MATCHED[1]}         "
        f"{(EXTENT_MATCHED[0] - 1) * (EXTENT_MATCHED[1] - 1):3d}   "
        f"~{(EXTENT_MATCHED[0] - 1) * 20} x {(EXTENT_MATCHED[1] - 1) * 20}",
        f"   quad-matched  {QUAD_MATCHED[0]}x{QUAD_MATCHED[1]}       "
        f"{(QUAD_MATCHED[0] - 1) * (QUAD_MATCHED[1] - 1):3d}   "
        f"~{(QUAD_MATCHED[0] - 1) * 20} x {(QUAD_MATCHED[1] - 1) * 20}",
        "",
    ]

    results = {}
    for label, shape in (
        ("extent-matched", EXTENT_MATCHED),
        ("quad-matched", QUAD_MATCHED),
    ):
        windows = real_windows(shape)
        results[label] = {dr: summarise(score_windows(windows, dr)) for dr in DR_SWEEP}
        lines.append(f"=== {label} windows ({shape[0]}x{shape[1]} cells) ===")
        if not windows:
            lines.append("  no fully valid windows of this shape exist in the data")
            lines.append("")
            continue
        lines.append(
            "     dr      n   satisfied-frac p50   share satisfied   verdict differs   max |delta|"
        )
        lines.append("  " + "-" * 88)
        for dr in DR_SWEEP:
            r = results[label][dr]
            lines.append(
                f"   {dr:5.2f}  {r['n']:4d}   {r['frac_p50']:16.3f}   {r['satisfied']:14.1%}"
                f"   {r['verdict_differs']:15.1%}   {r['max_delta']:11.4f}"
            )
        lines.append("")

    ext = results["extent-matched"].get(REAL_DR)
    lines.append("=== Verdict on the pre-registered rule ===")
    if ext is None:
        lines.append("  No extent-matched windows; the rule cannot be evaluated.")
    elif ext["satisfied"] >= SATISFIED_SHARE_LIMIT:
        lines.append(
            f"  {ext['satisfied']:.1%} of real extent-matched windows are satisfied at"
            f" dr={REAL_DR}, at or above the pre-registered {SATISFIED_SHARE_LIMIT:.0%}."
        )
        lines.append(
            "  The reference condition transfers: the report's synthetic patch is not"
        )
        lines.append(
            "  unrepresentative in this respect, and the blindness describes a situation"
        )
        lines.append("  villa can actually be in.")
    else:
        lines.append(
            f"  ⚠ Only {ext['satisfied']:.1%} of real extent-matched windows are satisfied at"
            f" dr={REAL_DR}, below the pre-registered {SATISFIED_SHARE_LIMIT:.0%}."
        )
        lines.append(
            "  villa's metric rejects most real patches at this scale on their own merits,"
        )
        lines.append(
            "  displaced or not. The exact algebra of the report still holds, but it"
        )
        lines.append(
            "  describes a reference condition most real windows do not meet, and the report"
        )
        lines.append("  must carry that qualification.")
    lines.append("")
    lines.append(
        f"Limits. dr is swept over {DR_SWEEP} rather than fitted per patch, because the"
        " real spacing varies 11.32 to 16.74 across shards and a patch scored against a"
        " spacing it does not have would fail for the wrong reason. A per-patch fit is the"
        " follow-up. Windows are pooled with a per-patch cap, not a global quota."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
