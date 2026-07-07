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
from repro.sota_data.register import (label_line_periodicity, read_tifxyz, warp_via_field)
from repro.sota_data.qualitative import write_fragment

LEVEL0_SHAPE = (50600, 36400)
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
    valid = (np.isfinite(pts).all(1) & ~(np.abs(pts + 1) < 1e-6).all(1)
             & ~(np.abs(pts) < 1e-9).all(1))
    d, idx = cKDTree(obj_v).query(pts[valid], k=1)
    uv = obj_vt[idx]
    H = old_label.shape[0]
    rc = np.stack([H - uv[:, 1], uv[:, 0]], axis=1)  # rowHv_colu
    field = np.full((rh, rw, 2), np.nan, np.float32)
    field.reshape(-1, 2)[valid] = rc
    reg = warp_via_field(old_label, field, (size, size), interpolation=cv2.INTER_NEAREST)
    residual = float(np.median(d)) if len(d) else float("inf")
    return reg, residual, label_line_periodicity(reg)


def _region_in_mesh(new_xyz, y0, x0, size):
    mh, mw = new_xyz.shape[:2]
    sy, sx = mh / (LEVEL0_SHAPE[0] / 4), mw / (LEVEL0_SHAPE[1] / 4)
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


def gt_prep_fragment(seg, y0, x0, size, out_root, max_residual=12.0, min_periodicity=0.6):
    reg_dir = os.path.join("local_data/sota_gt_meshes", seg)
    obj_path, mesh_path = _fetch(seg, reg_dir)
    obj_v, obj_vt = parse_obj_vt(obj_path)
    new_xyz = read_tifxyz(mesh_path)
    region_xyz = _region_in_mesh(new_xyz, y0, x0, size)
    old_label = cv2.imread(
        f"villa/ink-detection/train_scrolls/{seg}/{seg}_inklabels.png", 0)
    if old_label is None:
        raise ValueError(f"{seg}: hand label unreadable")
    reg_label, residual, periodicity = register_label_to_region(
        region_xyz, obj_v, obj_vt, old_label, size)
    frag_id = f"{seg}_y{y0}_x{x0}"
    passed = residual <= max_residual and periodicity >= min_periodicity
    info = {"frag_id": frag_id, "residual": residual, "periodicity": periodicity,
            "gt_ink_fraction": float((reg_label > 127).mean()), "passed": bool(passed)}
    if not passed:
        print(f"DROP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f}",
              flush=True)
        return info
    # SOTA surface layers: reuse the Phase-2 distill fragment if present, else extract.
    src_layers = os.path.join("local_data/sota_distill", frag_id, "layers")
    out_seg = os.path.join(out_root, frag_id)
    if os.path.isdir(src_layers):
        region_stack = np.stack([
            cv2.imread(os.path.join(src_layers, f"{i:02d}.tif"), 0) for i in range(17, 43)],
            axis=0)
    else:
        region_stack, _, _ = dr.extract_region(seg, y0, x0, scroll_key="scroll1")
    write_fragment(region_stack, out_root, frag_id)   # layers + zero label + mask
    cv2.imwrite(os.path.join(out_seg, f"{frag_id}_inklabels.png"), reg_label)  # GT label
    print(f"KEEP {frag_id}: residual={residual:.2f} periodicity={periodicity:.3f} "
          f"gt_ink={info['gt_ink_fraction']:.3f}", flush=True)
    return info
