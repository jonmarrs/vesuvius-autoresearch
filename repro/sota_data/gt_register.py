"""Register a 2023 hand ink-label onto a SOTA surface region via the segment's original.obj
vertex texture coordinates (fixed rowHv_colu convention -- the export-pipeline constant from
slice 5, teacher-independent), gate on residual + text-line periodicity, and write a
detector-format GROUND-TRUTH training fragment. Unlike distillation, the label here is human
ground truth, not a teacher prediction."""

import glob
import os
import sys

import cv2
import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.qualitative import write_fragment
from repro.sota_data.register import (
    label_line_periodicity,
    level0_shape,
    placement_peak,
    read_tifxyz,
    warp_via_field,
)

# Level-0 shapes now come from register.LEVEL0_SHAPES (single source of truth). This module
# used to carry its own hardcoded copy pinned to 20230702185753, applied to every segment --
# a second instance of the bug that produced the retracted 2026-07 result. On 20231005123336
# (true level-0 34880x97280 vs the assumed 50600x36400) that is a 167% x-scale error, so the
# GT fine-tune trained on catastrophically misplaced labels.
MESH_NEW_TMPL = "{seg}-on-20230205180739-7.91um.tifxyz"


def parse_obj_vt(path):
    vs, vts = [], []
    with open(path) as f:
        for line in f:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
    v = np.asarray(vs, np.float32)
    vt = np.asarray(vts, np.float32)
    if len(v) != len(vt):
        raise ValueError(f"obj v/vt count mismatch: {len(v)} vs {len(vt)}")
    return v, vt


def register_label_to_region(region_xyz, obj_v, obj_vt, old_label, size):
    """NN-bridge each region 3D point to the nearest obj vertex, read its vt (row=H-v,col=u),
    sample old_label. Returns (reg_label[size,size], median residual, periodicity)."""
    region_xyz = np.asarray(region_xyz, np.float32)
    rh, rw = region_xyz.shape[:2]
    pts = region_xyz.reshape(-1, 3)
    valid = (
        np.isfinite(pts).all(1)
        & ~(np.abs(pts + 1) < 1e-6).all(1)
        & ~(np.abs(pts) < 1e-9).all(1)
    )
    d, idx = cKDTree(obj_v).query(pts[valid], k=1)
    uv = obj_vt[idx]
    H = old_label.shape[0]
    rc = np.stack([H - uv[:, 1], uv[:, 0]], axis=1)  # rowHv_colu
    field = np.full((rh, rw, 2), np.nan, np.float32)
    field.reshape(-1, 2)[valid] = rc
    reg = warp_via_field(
        old_label, field, (size, size), interpolation=cv2.INTER_NEAREST
    )
    residual = float(np.median(d)) if len(d) else float("inf")
    return reg, residual, label_line_periodicity(reg)


def _region_in_mesh(new_xyz, seg, y0, x0, size):
    mh, mw = new_xyz.shape[:2]
    l0 = level0_shape(seg)
    sy, sx = mh / (l0[0] / 4), mw / (l0[1] / 4)
    ys, xs = int(round(y0 * sy)), int(round(x0 * sx))
    ye, xe = int(round((y0 + size) * sy)), int(round((x0 + size) * sx))
    return new_xyz[ys:ye, xs:xe]


def _fetch(seg, reg_dir):
    os.makedirs(reg_dir, exist_ok=True)
    fs = dr._fs()
    pref = dr._scroll_prefix("scroll1", seg, "mesh")
    obj = os.path.join(reg_dir, f"{seg}_original.obj")
    if not os.path.exists(obj):
        fs.get(f"{pref}/intermediate/{seg}_original.obj", obj)
    mesh = os.path.join(reg_dir, MESH_NEW_TMPL.format(seg=seg))
    if not os.path.exists(mesh):
        fs.get(f"{pref}/{MESH_NEW_TMPL.format(seg=seg)}", mesh, recursive=True)
    return obj, mesh


def _teacher_crop_for(frag_id):
    """Locate the canon-teacher crop for a region, or None.

    NOTE `local_data/sota_gt/<frag>/*_inklabels.png` is the registered GT itself, i.e. this
    function's own output, NOT the teacher. Scoring GT against it yields a meaningless
    perfect placement, so that root is deliberately excluded here.
    """
    for cand in (
        f"local_data/sota_distill/{frag_id}/{frag_id}_inklabels.png",
        f"local_data/sota_xscroll/scroll1_{frag_id}/scroll1_{frag_id}_inklabels.png",
    ):
        if os.path.exists(cand):
            return cand
    return None


def gt_prep_fragment(
    seg,
    y0,
    x0,
    size,
    out_root,
    max_residual=12.0,
    min_periodicity=0.6,
    max_placement_offset=None,
    allow_unverified_placement=False,
):
    """Register one GT training region, keeping it only if it passes every gate.

    PLACEMENT is gated here, not only in register_run's cmd_validate. The training path had
    no placement check at all, which is how the GT fine-tune came to train on labels
    displaced by up to a 167% scale error: residual and periodicity both looked fine.
    Residual measures correspondence scatter and never constrained position.

    A region whose placement cannot be checked (no teacher crop on disk) is DROPPED rather
    than assumed good, matching the withheld-target policy. Pass
    `allow_unverified_placement=True` to override; the region then records
    `placement_verified: False` so the gap stays visible downstream.
    """
    reg_dir = os.path.join("local_data/sota_gt_meshes", seg)
    obj_path, mesh_path = _fetch(seg, reg_dir)
    obj_v, obj_vt = parse_obj_vt(obj_path)
    new_xyz = read_tifxyz(mesh_path)
    region_xyz = _region_in_mesh(new_xyz, seg, y0, x0, size)
    old_label = cv2.imread(
        f"villa/ink-detection/train_scrolls/{seg}/{seg}_inklabels.png", 0
    )
    if old_label is None:
        raise ValueError(f"{seg}: hand label unreadable")
    reg_label, residual, periodicity = register_label_to_region(
        region_xyz, obj_v, obj_vt, old_label, size
    )
    frag_id = f"{seg}_y{y0}_x{x0}"
    passed = residual <= max_residual and periodicity >= min_periodicity
    info = {
        "frag_id": frag_id,
        "residual": residual,
        "periodicity": periodicity,
        "gt_ink_fraction": float((reg_label > 127).mean()),
        "passed": bool(passed),
    }
    if not passed:
        print(
            f"DROP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f}",
            flush=True,
        )
        return info

    if max_placement_offset is None:
        from repro.sota_data.register_run import MAX_PLACEMENT_OFFSET_L2PX

        max_placement_offset = MAX_PLACEMENT_OFFSET_L2PX

    # Agreement with the teacher must peak at ZERO shift; residual and periodicity are both
    # blind to a bodily displaced label.
    teacher_path = _teacher_crop_for(frag_id)
    if teacher_path is None:
        info["placement_verified"] = False
        if not allow_unverified_placement:
            info["passed"] = False
            info["placement_note"] = (
                f"no teacher crop for {frag_id}, so placement could not be checked; "
                "dropped rather than assumed good"
            )
            print(
                f"DROP {frag_id}: placement UNVERIFIABLE (no teacher crop)", flush=True
            )
            return info
        print(f"WARN {frag_id}: placement unverified (no teacher crop)", flush=True)
    else:
        dy, dx, _, _ = placement_peak(reg_label, cv2.imread(teacher_path, 0))
        offset = float(np.hypot(dy, dx))
        info["placement_offset_level2_px"] = offset
        info["placement_verified"] = True
        if offset > max_placement_offset:
            info["passed"] = False
            print(
                f"DROP {frag_id}: placement {offset:.1f} px (dy={dy}, dx={dx}) exceeds "
                f"{max_placement_offset:.0f} px",
                flush=True,
            )
            return info
    # SOTA surface layers: reuse the Phase-2 distill fragment if present, else extract.
    src_layers = os.path.join("local_data/sota_distill", frag_id, "layers")
    out_seg = os.path.join(out_root, frag_id)
    if os.path.isdir(src_layers):
        region_stack = np.stack(
            [
                cv2.imread(os.path.join(src_layers, f"{i:02d}.tif"), 0)
                for i in range(17, 43)
            ],
            axis=0,
        )
    else:
        region_stack, _, _ = dr.extract_region(seg, y0, x0, scroll_key="scroll1")
    write_fragment(region_stack, out_root, frag_id)  # layers + zero label + mask
    cv2.imwrite(
        os.path.join(out_seg, f"{frag_id}_inklabels.png"), reg_label
    )  # GT label
    print(
        f"KEEP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f} "
        f"gt_ink={info['gt_ink_fraction']:.3f}",
        flush=True,
    )
    return info
