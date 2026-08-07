"""Register the old hand ground-truth label onto the SOTA re-flattening (segment
20230702185753) and, ONLY after the alignment gate passes, score the canon teacher, the
distilled students, and the legacy detector against registered ground truth. Every score
is 'vs registered ground truth (method + residuals stated)'.

The route that produced the committed result is `warp_obj` (region 3D -> nearest vertex of
the segment's original.obj -> that vertex's vt = 2023 label pixel). The `warp`/similarity
route is the earlier mesh-bridge attempt, kept and unit-tested but superseded (its coarse
tifxyz correspondence did not pass the alignment gate)."""

import json
import os
import sys
from typing import Any

import cv2
import numpy as np
import tifffile
from PIL import Image

sys.path.insert(0, os.path.abspath("."))
from repro.sota_data import distill_run as dr
from repro.sota_data.register import (
    correspondence_field,
    fit_similarity,
    label_line_periodicity,
    ncc,
    read_tifxyz,
    warp_via_field,
)

# Per-segment SOTA surface-volume level-0 shape (y, x), read from the 2.4um OME-Zarr.
#
# This was a single module-level constant hardcoded to 20230702185753's shape and applied
# to EVERY segment. On 20231210121321 (true level-0 51000x39980) that scaled the region
# crop by 9995/9100 in x and 12750/12650 in y, displacing AND stretching the registered
# label -- which is what produced the bogus "held-out reads at chance" result
# (reports/detector/registration_offset_2026-08-07.md). Never reintroduce a shared default:
# a missing entry must raise, not silently borrow another segment's geometry.
LEVEL0_SHAPES = {
    "20230702185753": (50600, 36400),
    "20231210121321": (51000, 39980),
}
LEVEL0_SHAPE: Any = None  # set per-target by _set_target()


def fetch_level0_shape(seg, scroll_key="scroll1"):
    """Authoritative level-0 (y, x) for a segment, straight from the surface-volume zarr."""
    import zarr

    fs = dr._fs()
    pref = dr._scroll_prefix(scroll_key, seg, "surface-volumes")
    zarrs = sorted(p for p in fs.ls(pref, detail=False) if p.endswith(".zarr"))
    preferred = [z for z in zarrs if "2.4um" in z and "-L1" not in z] or zarrs
    if not preferred:
        raise ValueError(f"{seg}: no .zarr under {pref}")
    g = zarr.open(zarr.storage.FSStore(preferred[0], fs=fs), mode="r")
    return tuple(int(n) for n in g["0"].shape[1:3])


def cmd_verify_shapes():
    """Check every hardcoded LEVEL0_SHAPES entry against the bucket. Requires network."""
    bad = 0
    for seg, claimed in sorted(LEVEL0_SHAPES.items()):
        actual = fetch_level0_shape(seg)
        ok = tuple(claimed) == actual
        bad += not ok
        print(
            f"{'OK  ' if ok else 'FAIL'} {seg}: claimed {tuple(claimed)} actual {actual}"
        )
    if bad:
        raise SystemExit(
            f"{bad} segment shape(s) wrong -- registrations using them are invalid"
        )
    print("all level-0 shapes verified")


CKPTS = [
    ("legacy detector", "models/detector/detector_epoch=7.ckpt"),
    ("arm A (1-scroll student)", "models/detector_sota_distill/detector_epoch=9.ckpt"),
    ("arm B (2-scroll student)", "models/detector_xscroll/detector_epoch=7.ckpt"),
    ("arm C (3-scroll student)", "models/detector_xscroll_c/detector_epoch=11.ckpt"),
]
# Segments carrying all three registration inputs (hand label + original.obj + canon
# teacher). "orig" = slice-5 (a TRAIN region for all students); "heldout" = arm-A
# validated but trained by NObody (arms B/C fully clean).
_ALL_STUDENTS = [
    "arm A (1-scroll student)",
    "arm B (2-scroll student)",
    "arm C (3-scroll student)",
]
TARGETS = {
    "orig": {
        "seg": "20230702185753",
        "region": (4000, 2500, 4096),
        "frag_root": "local_data/sota_xscroll",
        "frag_id": "scroll1_20230702185753_y4000_x2500",
        "old_root": "villa/ink-detection/train_scrolls/20230702185753",
        "report_md": "reports/detector/registered_gt_validation.md",
        "report_json": "reports/detector/registered_gt_validation.json",
        "report_title": "First ground-truth-validated scores on SOTA data (registered label)",
        "gate_mode": "enrichment",
        "train_region_models": _ALL_STUDENTS,  # all three students trained on this region
        "selection_caveat_models": [],
        "overlay_ref": "reports/detector/registered_gt_overlay.png",
        "extra_disclosure": (
            "**Confound 1 (train region):** this region was a TRAINING region for all three "
            "distilled students, so their rows are *train-region fit-quality vs ground "
            "truth*, NOT held-out generalization. The **unconfounded** rows are the canon "
            "teacher and the legacy detector (neither trained here).\n\n"
            "The teacher row's label orientation was picked among 4 discrete candidates by "
            "teacher-enrichment (decisive here, 5.05 vs 0.90/1.09/1.50); the correspondence "
            "geometry and residual are teacher-free, so this is at most marginally "
            "optimistic."
        ),
        "binary_caveat": (
            "**Confound (binary vs continuous):** the teacher is a BINARY map; ROC-AUC and "
            "AP reward the ranking that the students' continuous probability maps have and a "
            "binary map cannot, so they structurally understate the teacher. The *fair* "
            "teacher-vs-student comparison is F1 (`f1_at_0.5`): read the students as matching "
            "or modestly exceeding teacher F1, NOT as the larger ROC-AUC/AP gap."
        ),
    },
    "heldout": {
        "seg": "20231210121321",
        "region": (4000, 2500, 4096),
        "frag_root": "local_data/sota_distill",
        "frag_id": "20231210121321_y4000_x2500",
        "old_root": "villa/ink-detection/train_scrolls/20231210121321",
        "report_md": "reports/detector/registered_gt_heldout_validation.md",
        "report_json": "reports/detector/registered_gt_heldout_validation.json",
        "report_title": (
            "Held-out ground-truth scores on SOTA data "
            "(registered label, segment 20231210121321)"
        ),
        "gate_mode": "teacher_free",
        "train_region_models": [],  # NO student trained on this region
        "selection_caveat_models": ["arm A (1-scroll student)"],  # arm A validated here
        "overlay_ref": "reports/detector/registered_gt_heldout_overlay.png",
        "extra_disclosure": (
            "**Held-out (no train confound):** NO student trained on this segment, so the "
            "student rows are genuine *held-out generalization vs ground truth*. arm A used "
            "this segment for best-epoch *selection* (agreement-with-teacher), so its row is "
            "mildly selection-optimistic; **arms B and C are fully clean held-out** and carry "
            "the claim.\n\n"
            "**Alignment validated teacher-free (the enrichment gate false-negatived here).** "
            "The canon teacher reads THIS segment poorly (scattered, non-letterform), so "
            "teacher-enrichment (1.68) is not a valid alignment metric and the enrichment "
            "gate fails by design. Registration is validated on the codified teacher-free "
            "gate (`gate_mode=teacher_free`): 3D correspondence residual 7.85 old-scan voxels "
            "(vs the independently-validated slice-5 registration's 7.92) and registered-"
            "label text-line periodicity 0.871 (slice-5 orig computes 0.900 by the same "
            "`register.label_line_periodicity`). **Scope of this evidence:** residual, "
            "periodicity and the overlay's crisp letterforms are *convention-blind* -- they "
            "confirm real text landed on the correct 3D manifold, but NOT the 2D orientation. "
            "The `rowHv_colu` orientation is carried from slice 5 as an export-pipeline "
            "invariant (same scroll/scan/tooling), weakly corroborated here by "
            "enrichment 1.68>1 and teacher AP-lift 1.15>1 (a mirrored convention would give "
            "≈1.0). That the teacher is weak here is itself a finding: agreement-with-"
            "teacher would reward reproducing this segment's noise, so a held-out ground-"
            "truth score measures real reading, not mimicry."
        ),
        "binary_caveat": (
            "**Metric note (everything reads near chance here):** at this region's ink "
            "prevalence (~0.18) the trivial all-positive predictor already scores F1 "
            "≈ 0.31 -- the legacy detector predicts all-positive and sits exactly there "
            "-- so `val_f1`/F1 is degenerate and the binary-teacher caveat does NOT rescue "
            "the teacher. The robust reads are AP-prevalence-lift and ROC-AUC: teacher "
            "1.15/0.563, arms B/C 1.16-1.17/0.55-0.56, legacy 1.00/0.50 -- all ≈ chance. "
            "At `f1_at_0.5` the students actually TRAIL the teacher (0.23-0.26 vs 0.295)."
        ),
    },
}

# module globals rebound by _set_target from the TARGETS dict (declared here so
# references resolve at import; typed Any because _set_target fills them in).
SEG: Any = None
REG_DIR: Any = None
OLD_ROOT: Any = None
MESH_OLD: Any = None
MESH_NEW: Any = None
OBJ_PATH: Any = None
REGION_L2: Any = None
FRAG_ID: Any = None
XSCROLL_ROOT: Any = None
MARKER: Any = None
REG_LABEL: Any = None
REG_STATS: Any = None
REPORT_MD: Any = None
REPORT_JSON: Any = None
REPORT_TITLE: Any = None
TRAIN_REGION_MODELS: Any = None
SELECTION_CAVEAT_MODELS: Any = None
OVERLAY_REF: Any = None
EXTRA_DISCLOSURE: Any = None
GATE_MODE: Any = None
BINARY_CAVEAT: Any = None


def _set_target(key):
    global LEVEL0_SHAPE
    global SEG, REG_DIR, OLD_ROOT, MESH_OLD, MESH_NEW, OBJ_PATH, REGION_L2
    global FRAG_ID, XSCROLL_ROOT, MARKER, REG_LABEL, REG_STATS, REPORT_MD, REPORT_JSON
    global REPORT_TITLE, TRAIN_REGION_MODELS, SELECTION_CAVEAT_MODELS, OVERLAY_REF
    global EXTRA_DISCLOSURE, GATE_MODE, BINARY_CAVEAT
    if key not in TARGETS:
        raise ValueError(
            f"unknown registration target '{key}'; known: {sorted(TARGETS)}"
        )
    t = TARGETS[key]
    SEG = t["seg"]
    if SEG not in LEVEL0_SHAPES:
        raise ValueError(
            f"no level-0 shape recorded for segment {SEG}. Add it to LEVEL0_SHAPES "
            f"(get it with fetch_level0_shape('{SEG}')). Refusing to fall back to another "
            f"segment's geometry -- that bug invalidated the 2026-07 held-out result."
        )
    LEVEL0_SHAPE = LEVEL0_SHAPES[SEG]
    REGION_L2 = t["region"]
    FRAG_ID = t["frag_id"]
    XSCROLL_ROOT = t["frag_root"]
    OLD_ROOT = t["old_root"]
    REPORT_MD = t["report_md"]
    REPORT_JSON = t["report_json"]
    REPORT_TITLE = t["report_title"]
    GATE_MODE = t["gate_mode"]
    TRAIN_REGION_MODELS = set(t["train_region_models"])
    SELECTION_CAVEAT_MODELS = set(t["selection_caveat_models"])
    OVERLAY_REF = t["overlay_ref"]
    EXTRA_DISCLOSURE = t["extra_disclosure"]
    BINARY_CAVEAT = t["binary_caveat"]
    REG_DIR = os.path.join("local_data/sota_registration", key)
    MESH_OLD = "intermediate/tifxyz_original"  # the 2023 label parameterization
    MESH_NEW = f"{SEG}-on-20230205180739-7.91um.tifxyz"  # new UV domain, old-scan frame
    OBJ_PATH = os.path.join(REG_DIR, f"{SEG}_original.obj")
    MARKER = os.path.join(REG_DIR, "VALIDATED")
    REG_LABEL = os.path.join(REG_DIR, "registered_label_l2region.png")
    REG_STATS = os.path.join(REG_DIR, "registration_stats.json")


_set_target("orig")  # import-time default = slice-5 behavior


def _mesh_path(name):
    return os.path.join(REG_DIR, name)


def cmd_probe():
    os.makedirs(REG_DIR, exist_ok=True)
    fs = dr._fs()
    pref = dr._scroll_prefix("scroll1", SEG, "mesh")
    entries = fs.ls(pref, detail=False)
    print("mesh dir entries:")
    for e in entries:
        print("  " + e.rsplit("/", 1)[-1], flush=True)
    for name in (MESH_OLD, MESH_NEW):
        dst = _mesh_path(name)
        if not os.path.exists(dst):
            # a .tifxyz is a DIRECTORY (meta.json + x/y/z.tif planes) -- fetch recursively
            fs.get(f"{pref}/{name}", dst, recursive=True)
        meta = os.path.join(dst, "meta.json")
        if os.path.exists(meta):
            with open(meta) as f:
                print(f"{name} meta.json: {f.read().strip()}", flush=True)
        xyz = read_tifxyz(dst)
        pts = xyz.reshape(-1, 3)
        finite = np.isfinite(pts).all(axis=1)
        nz = finite & ~(np.abs(pts) < 1e-9).all(axis=1)
        print(
            f"{name}: grid {xyz.shape[:2]}, valid {nz.mean():.3f}, "
            f"xyz range {pts[nz].min(0).round(1)} .. {pts[nz].max(0).round(1)}",
            flush=True,
        )


def _load_meshes():
    old_xyz = read_tifxyz(_mesh_path(MESH_OLD))
    new_xyz = read_tifxyz(_mesh_path(MESH_NEW))
    return old_xyz, new_xyz


def _region_in_mesh(new_xyz):
    """Crop the new mesh to the measured region (level-2 coords scaled to mesh grid)."""
    mh, mw = new_xyz.shape[:2]
    sy, sx = mh / (LEVEL0_SHAPE[0] / 4), mw / (LEVEL0_SHAPE[1] / 4)  # mesh vs level-2
    y0, x0, size = REGION_L2
    ys, xs = int(round(y0 * sy)), int(round(x0 * sx))
    ye, xe = int(round((y0 + size) * sy)), int(round((x0 + size) * sx))
    return new_xyz[ys:ye, xs:xe]


def cmd_warp():
    old_xyz, new_xyz = _load_meshes()
    print(
        f"fitting similarity new->old from meshes "
        f"(old grid {old_xyz.shape[:2]}, new grid {new_xyz.shape[:2]}) ...",
        flush=True,
    )
    s, R, t, med_fit = fit_similarity(new_xyz.reshape(-1, 3), old_xyz.reshape(-1, 3))
    print(f"fit: scale={s:.4f} med_residual={med_fit:.2f} (old-scan units)", flush=True)

    region_xyz = _region_in_mesh(new_xyz)
    field, res = correspondence_field(region_xyz, s, R, t, old_xyz, stride=1)
    med_res = float(np.nanmedian(res))
    print(
        f"region correspondence: median residual {med_res:.2f}, "
        f"p90 {float(np.nanquantile(res, 0.9)):.2f}",
        flush=True,
    )

    old_label = cv2.imread(os.path.join(OLD_ROOT, f"{SEG}_inklabels.png"), 0)
    old_mid = cv2.imread(
        sorted(__import__("glob").glob(os.path.join(OLD_ROOT, "layers", "*.tif")))[13],
        0,
    )
    if old_label is None or old_mid is None:
        raise ValueError("old label / mid layer unreadable")
    # mesh-grid coords -> old-label pixel coords (grids may differ slightly in size)
    oh, ow = old_xyz.shape[:2]
    lf = field.copy()
    lf[..., 0] *= old_label.shape[0] / oh
    lf[..., 1] *= old_label.shape[1] / ow
    size = REGION_L2[2]
    reg_label = warp_via_field(
        old_label, lf, (size, size), interpolation=cv2.INTER_NEAREST
    )
    mf = field.copy()
    mf[..., 0] *= old_mid.shape[0] / oh
    mf[..., 1] *= old_mid.shape[1] / ow
    reg_mid = warp_via_field(old_mid, mf, (size, size))
    cv2.imwrite(REG_LABEL, reg_label)
    cv2.imwrite(os.path.join(REG_DIR, "registered_oldsurface_l2region.png"), reg_mid)
    with open(REG_STATS, "w") as f:
        json.dump(
            {
                "method": "mesh-bridge (PCA+trimmed-ICP similarity, stride-8 field)",
                "fit_scale": s,
                "fit_median_residual": med_fit,
                "region_median_residual": med_res,
                "region_p90_residual": float(np.nanquantile(res, 0.9)),
                "registered_ink_fraction": float((reg_label > 127).mean()),
            },
            f,
            indent=2,
        )
    print(
        f"registered label ink fraction: {float((reg_label > 127).mean()):.3f} "
        f"(teacher-positive on this region was 0.193)",
        flush=True,
    )


def cmd_warp_obj():
    """The obj-exact route (the one that passed visual + enrichment checks): region 3D
    (on-7.91um tifxyz, old-scan frame) -> NN over original.obj vertices -> vt (2023 label
    px, OBJ bottom-left origin: row = H - v, col = u). Registration is teacher-free apart
    from the 4-way discrete vt-convention pick (enrichment table printed, disclosed)."""
    from scipy.spatial import cKDTree

    if not os.path.exists(OBJ_PATH):
        fs = dr._fs()
        pref = dr._scroll_prefix("scroll1", SEG, "mesh")
        fs.get(f"{pref}/intermediate/{SEG}_original.obj", OBJ_PATH)
    vs, vts = [], []
    with open(OBJ_PATH) as f:
        for line in f:
            if line.startswith("v "):
                vs.append([float(x) for x in line.split()[1:4]])
            elif line.startswith("vt "):
                vts.append([float(x) for x in line.split()[1:3]])
    v = np.array(vs, np.float32)
    vt = np.array(vts, np.float32)
    # Assumes a 1:1 positional v<->vt export (vt[i] is vertex i's texture coord); `f` faces
    # are not parsed. Guarded by the len check below AND the enrichment gate downstream (a
    # bad pairing scatters the label -> enrichment ~= 1 -> gate fails). Holds for this obj.
    if len(v) != len(vt):
        raise ValueError(f"obj v/vt count mismatch: {len(v)} vs {len(vt)}")
    old_label = cv2.imread(os.path.join(OLD_ROOT, f"{SEG}_inklabels.png"), 0)
    old_mid = cv2.imread(
        sorted(__import__("glob").glob(os.path.join(OLD_ROOT, "layers", "*.tif")))[13],
        0,
    )
    if old_label is None or old_mid is None:
        raise ValueError("old label / mid layer unreadable")
    h_lab, w_lab = old_label.shape
    new_xyz = read_tifxyz(_mesh_path(MESH_NEW))
    region_xyz = _region_in_mesh(new_xyz)
    rh, rw = region_xyz.shape[:2]
    pts = region_xyz.reshape(-1, 3)
    valid = (
        np.isfinite(pts).all(1)
        & ~(np.abs(pts + 1) < 1e-6).all(1)
        & ~(np.abs(pts) < 1e-9).all(1)
    )
    d, idx = cKDTree(v).query(pts[valid], k=1)
    uv = vt[idx]
    teacher = (
        cv2.imread(os.path.join(XSCROLL_ROOT, FRAG_ID, f"{FRAG_ID}_inklabels.png"), 0)
        > 127
    )
    size = REGION_L2[2]
    cands = {
        "rowv_colu": np.stack([uv[:, 1], uv[:, 0]], 1),
        "rowHv_colu": np.stack([h_lab - uv[:, 1], uv[:, 0]], 1),
        "rowv_colWu": np.stack([uv[:, 1], w_lab - uv[:, 0]], 1),
        "rowHv_colWu": np.stack([h_lab - uv[:, 1], w_lab - uv[:, 0]], 1),
    }
    enr = {}
    for name, rc in cands.items():
        fld = np.full((rh, rw, 2), np.nan, np.float32)
        fld.reshape(-1, 2)[valid] = rc
        lab = (
            warp_via_field(
                old_label, fld, (size, size), interpolation=cv2.INTER_NEAREST
            )
            > 127
        )
        enr[name] = float(lab[teacher].mean() / max(lab[~teacher].mean(), 1e-6))
        print(f"convention {name}: enrichment {enr[name]:.2f}", flush=True)
    best = max(enr, key=enr.get)
    print(
        f"chosen convention: {best} (letterform orientation must also be verified "
        "visually in the overlay)",
        flush=True,
    )
    field = np.full((rh, rw, 2), np.nan, np.float32)
    field.reshape(-1, 2)[valid] = cands[best]
    reg_label = warp_via_field(
        old_label, field, (size, size), interpolation=cv2.INTER_NEAREST
    )
    reg_mid = warp_via_field(old_mid, field, (size, size))
    cv2.imwrite(REG_LABEL, reg_label)
    cv2.imwrite(os.path.join(REG_DIR, "registered_oldsurface_l2region.png"), reg_mid)
    with open(REG_STATS, "w") as f:
        json.dump(
            {
                "method": f"obj-exact: original.obj vt ({len(v)} vertices), NN bridge "
                f"via on-7.91um tifxyz (same old-scan frame), vt convention "
                f"{best} (selected by teacher-enrichment among 4 discrete "
                f"candidates, disclosed; orientation verified visually)",
                "region_median_residual": float(np.median(d)),
                "region_p90_residual": float(np.quantile(d, 0.9)),
                "registered_ink_fraction": float((reg_label > 127).mean()),
                "enrichment_all_candidates": enr,
            },
            f,
            indent=2,
        )
    print(
        f"3D NN residual: median {np.median(d):.2f} p90 {np.quantile(d, 0.9):.2f} "
        f"(old voxels); ink fraction {(reg_label > 127).mean():.3f}",
        flush=True,
    )


def cmd_validate():
    if not os.path.exists(REG_STATS):
        raise ValueError(f"{REG_STATS} missing; run warp first")
    with open(REG_STATS) as f:
        stats = json.load(f)
    # thresholds are CLI-settable; the gate CRITERION is target-driven (GATE_MODE):
    #   "enrichment"  -> teacher-dependent (registered ink inside/outside teacher strokes)
    #   "teacher_free"-> residual + text-line periodicity (used when the teacher is weak on
    #                    this segment, so enrichment would false-negative a good alignment)
    import argparse

    ap = argparse.ArgumentParser()
    ap.add_argument("--max-median-residual", type=float, required=True)
    ap.add_argument("--min-enrichment", type=float, default=0.0)
    ap.add_argument("--min-periodicity", type=float, default=0.0)
    args = ap.parse_args(sys.argv[2:])

    frag_mid = cv2.imread(os.path.join(XSCROLL_ROOT, FRAG_ID, "layers", "30.tif"), 0)
    reg_mid = cv2.imread(os.path.join(REG_DIR, "registered_oldsurface_l2region.png"), 0)
    reg_label = cv2.imread(REG_LABEL, 0)
    if frag_mid is None or reg_mid is None or reg_label is None:
        raise ValueError("warp outputs / fragment layers missing")
    sel = reg_mid > 0
    score_ncc = ncc(np.where(sel, frag_mid, np.nan), np.where(sel, reg_mid, np.nan))
    stats["surface_ncc"] = score_ncc
    # renders: label over SOTA surface; label over teacher
    overlay = cv2.cvtColor(frag_mid, cv2.COLOR_GRAY2BGR)
    overlay[reg_label > 127] = (0, 0, 255)
    cv2.imwrite(
        os.path.join(REG_DIR, "overlay_label_on_sota.png"),
        cv2.resize(overlay, (1024, 1024)),
    )
    teacher = cv2.imread(
        os.path.join(XSCROLL_ROOT, FRAG_ID, f"{FRAG_ID}_inklabels.png"), 0
    )
    tover = cv2.cvtColor(teacher, cv2.COLOR_GRAY2BGR)
    tover[reg_label > 127] = (0, 0, 255)
    cv2.imwrite(
        os.path.join(REG_DIR, "overlay_label_on_teacher.png"),
        cv2.resize(tover, (1024, 1024)),
    )
    # both signals always computed + recorded (enrichment as a diagnostic even in
    # teacher_free mode, so its false-negative is visible in the stats).
    lab = reg_label > 127
    t = teacher > 127
    enrichment = float(lab[t].mean() / max(lab[~t].mean(), 1e-6))
    periodicity = label_line_periodicity(reg_label)
    stats["teacher_enrichment"] = enrichment
    stats["text_line_periodicity"] = periodicity
    res_ok = stats["region_median_residual"] <= args.max_median_residual
    if GATE_MODE == "teacher_free":
        passed = res_ok and periodicity >= args.min_periodicity
        gate = {
            "mode": "teacher_free",
            "max_median_residual": args.max_median_residual,
            "min_periodicity": args.min_periodicity,
            "periodicity": periodicity,
            "enrichment_diagnostic": enrichment,
            "passed": bool(passed),
            "note": "teacher-dependent enrichment is only a DIAGNOSTIC here; residual "
            "and periodicity are convention-blind (they confirm real text on "
            "the manifold, not the 2D orientation, which is carried from the "
            "slice-5 export-pipeline convention).",
        }
    else:
        passed = res_ok and enrichment >= args.min_enrichment
        gate = {
            "mode": "enrichment",
            "max_median_residual": args.max_median_residual,
            "min_enrichment": args.min_enrichment,
            "passed": bool(passed),
        }
    stats["gate"] = gate
    with open(REG_STATS, "w") as f:
        json.dump(stats, f, indent=2)
    tail = (
        f"median_res={stats['region_median_residual']:.2f}, enrichment={enrichment:.2f}"
        f", periodicity={periodicity:.3f}, mode={GATE_MODE}"
    )
    if passed:
        with open(MARKER, "w") as f:
            f.write(f"validated ({GATE_MODE})\n")
        print(f"VALIDATION PASSED ({tail}) -- marker written", flush=True)
    else:
        if os.path.exists(MARKER):
            os.remove(MARKER)
        print(
            f"VALIDATION FAILED ({tail}) -- NO scoring will run; inspect the overlays",
            flush=True,
        )


def cmd_score():
    if not os.path.exists(MARKER):
        raise ValueError(
            "registration not validated -- refusing to score against a "
            "possibly-misaligned label (run validate; inspect overlays)"
        )
    with open(REG_STATS) as f:
        stats = json.load(f)
    from vesuvius_autoresearch.detector.metrics import segmentation_metrics

    reg_label = (cv2.imread(REG_LABEL, 0) > 127).astype(np.uint8)
    mask = np.ones_like(reg_label, bool)
    # Row confounds are TARGET-driven (set by _set_target): which students trained on this
    # region (TRAIN_REGION_MODELS) and which merely selected on it (SELECTION_CAVEAT_MODELS).
    # The teacher (released prediction) and legacy (trained Fr47->Fr143) are always
    # unconfounded ground-truth calibrations.
    rows = {}
    # the canon teacher itself, vs registered ground truth
    teacher = cv2.imread(
        os.path.join(XSCROLL_ROOT, FRAG_ID, f"{FRAG_ID}_inklabels.png"), 0
    )
    rows["canon teacher (binarized release)"] = segmentation_metrics(
        teacher.astype(np.float32) / 255.0, reg_label, mask
    )
    for label, ckpt in CKPTS:
        m, _prob = dr._measure(ckpt, FRAG_ID, data_root=XSCROLL_ROOT)
        # re-score the prob map against the REGISTERED label, not the teacher
        prob = _prob
        rows[label] = segmentation_metrics(prob, reg_label, mask)
    for v in rows.values():
        v.pop("metrics_by_threshold", None)

    def tag(name):
        if name in TRAIN_REGION_MODELS:
            return " *(trained on this region)*"
        if name in SELECTION_CAVEAT_MODELS:
            return " *(selection-only; not trained here)*"
        return ""

    def row(name, m):
        return (
            f"| {name}{tag(name)} | "
            + " | ".join(f"{m.get(c, float('nan')):.4f}" for c in dr.COLS)
            + " |"
        )

    lines = [
        f"# {REPORT_TITLE}",
        "",
        "**All rows are scored against the REGISTERED hand ground-truth label** "
        f"(method: {stats['method']}; region median correspondence residual "
        f"{stats['region_median_residual']:.2f} old-scan voxels; registration is "
        "approximate -- residual noise depresses every row about equally, so absolute "
        "values are conservative and the ranking is the robust signal). The 'canon "
        "teacher' row scores the released model prediction itself against human "
        "labels.",
        "",
        EXTRA_DISCLOSURE,
        "",
        BINARY_CAVEAT,
        "",
        f"Segment `{SEG}`, level-2 region (4000,2500)+4096.",
        "",
        "| model (vs registered ground truth) | " + " | ".join(dr.COLS) + " |",
        "|---|" + "|".join(["---"] * len(dr.COLS)) + "|",
    ]
    lines += [row(k, v) for k, v in rows.items()]
    lines += [
        "",
        f"Overlays: `{REG_DIR}/overlay_label_on_sota.png`, "
        f"`overlay_label_on_teacher.png` (git-ignored); committed evidence render: "
        f"{OVERLAY_REF}.",
    ]
    with open(REPORT_MD, "w") as f:
        f.write("\n".join(lines) + "\n")
    with open(REPORT_JSON, "w") as f:
        json.dump(
            {"segment": SEG, "registration": stats, "rows": rows},
            f,
            indent=2,
            default=float,
        )
    print(
        "\n".join(
            f"{k}: val_f1={v.get('val_f1', float('nan')):.4f} "
            f"lift={v.get('ap_prevalence_lift', float('nan')):.4f}"
            for k, v in rows.items()
        ),
        flush=True,
    )


if __name__ == "__main__":
    cmds = {
        "probe": cmd_probe,
        "warp": cmd_warp,
        "warp_obj": cmd_warp_obj,
        "validate": cmd_validate,
        "score": cmd_score,
        "verify_shapes": cmd_verify_shapes,
    }
    if len(sys.argv) < 2 or sys.argv[1] not in cmds:
        sys.exit(
            f"usage: python -m repro.sota_data.register_run "
            f"{{{'|'.join(cmds)}}} [orig|heldout] [--flags]"
        )
    # optional target key as argv[2] (absent or a --flag => default 'orig');
    # strip it so cmd_validate's argparse (which reads sys.argv[2:]) is unaffected.
    key = "orig"
    if len(sys.argv) > 2 and not sys.argv[2].startswith("-"):
        key = sys.argv[2]
        del sys.argv[2]
    _set_target(key)
    cmds[sys.argv[1]]()
