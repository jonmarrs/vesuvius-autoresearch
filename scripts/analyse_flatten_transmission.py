"""Does a radial offset applied to the MESHES survive the lasagna flatten?

Implements `docs/preregistration/2026-09-22_does_the_flatten_transmit_a_mesh_offset.md`.
**Written before either flatten ran.**

villa's autoresearch loop may edit only fitting code; the flatten and render are
frozen. So any "offset lever" on `total_fg_pixels` is reachable by the loop only
if an offset in the fitted meshes reaches the flattened surface the render reads.
Two meshes sets displaced by exactly -4 / +4 vx are flattened deterministically
and compared with the deterministic flatten of the undisplaced meshes.

T is self-calibrated: the reference flat surface is shifted by the same radial
amount in memory and measured with the same tool. T = 1: fully transmitted.
T = 0: the flatten put the displaced input back where it was.
"""

import argparse
import glob
import json
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from measure_flatten_normal_offset import load_grid, normal_offset  # noqa: E402

REF, IN, OUT = "flatten_det_a", "flatten_rin", "flatten_rout"
MESH_SRC = (
    "radial_work_rad0"  # the undisplaced meshes; the offset axis is derived from these
)
DELTA = 4.0
FLAT = "meshes/concat/w120-129_flat"
HI, LO = 0.8, 0.2  # registered bands


def radial_shift(P: np.ndarray, m: np.ndarray, axis, delta: float) -> np.ndarray:
    Q = P.copy()
    dx, dy = P[..., 0] - axis[0], P[..., 1] - axis[1]
    r = np.hypot(dx, dy)
    r_safe = np.where(r > 1e-9, r, 1.0)
    Q[..., 0] = np.where(m, axis[0] + dx / r_safe * (r + delta), P[..., 0])
    Q[..., 1] = np.where(m, axis[1] + dy / r_safe * (r + delta), P[..., 1])
    return Q


def transmission(PA, mA, Pin, mIn, Pout, mOut, axis, delta, frac=1.0):
    def d(PB, mB):
        return normal_offset(PA, mA, PB, mB, frac=frac, axis=axis)

    ref_in = d(radial_shift(PA, mA, axis, -delta), mA)["normal_outward_median"]
    ref_out = d(radial_shift(PA, mA, axis, delta), mA)["normal_outward_median"]
    a_in, a_out = d(Pin, mIn), d(Pout, mOut)
    return {
        "ref_in": ref_in,
        "ref_out": ref_out,
        "arm_in": a_in["normal_outward_median"],
        "arm_out": a_out["normal_outward_median"],
        "in_plane_in": a_in["in_plane_p50"],
        "in_plane_out": a_out["in_plane_p50"],
        "T_in": a_in["normal_outward_median"] / ref_in,
        "T_out": a_out["normal_outward_median"] / ref_out,
    }


def verdict(t_in: float, t_out: float) -> tuple[str, str]:
    if t_in >= HI and t_out >= HI:
        return "TRANSMITS", (
            "A mesh offset reaches the flattened surface; an offset lever, if the sweep "
            "finds one, is reachable from fitting code."
        )
    if abs(t_in) <= LO and abs(t_out) <= LO:
        return "ABSORBED", (
            "The flatten puts a displaced input back on the same surface; a mesh offset "
            "cannot reach what the render reads."
        )
    if (t_in >= HI) != (t_out >= HI) or (abs(t_in) <= LO) != (abs(t_out) <= LO):
        return (
            "ASYMMETRIC",
            "Inward and outward offsets transmit differently; report both.",
        )
    return "PARTIAL", "Part of the offset survives; report T for each direction."


def mesh_axis(so: Path) -> tuple[float, float]:
    import tifffile

    xs, ys = [], []
    for d in sorted(glob.glob(str(so / MESH_SRC / "meshes" / "w1[23]*_spliced_*"))):
        x, y, z = (tifffile.imread(f"{d}/{c}.tif").astype(np.float64) for c in "xyz")
        m = ((x != 0) | (y != 0) | (z != 0)) & (z > 0) & np.isfinite(x) & np.isfinite(y)
        xs.append(x[m])
        ys.append(y[m])
    return float(np.concatenate(xs).mean()), float(np.concatenate(ys).mean())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--frac", type=float, default=0.125)
    ap.add_argument("--json", default=None)
    a = ap.parse_args()
    so = Path(a.spiral_out)

    missing = [x for x in (REF, IN, OUT) if not (so / x / FLAT / "x.tif").exists()]
    if missing:
        raise SystemExit(
            f"not flattened: {', '.join(missing)} -- refused, not reported."
        )
    shas = {(so / x / "VILLA_SHA").read_text().strip() for x in (REF, IN, OUT)}
    modes = {
        (so / x / "FLATTEN_MODE").read_text().strip()
        if (so / x / "FLATTEN_MODE").exists()
        else "unrecorded"
        for x in (IN, OUT)
    }
    print("DOES THE FLATTEN TRANSMIT A MESH OFFSET?\n")
    print(f"  provenance: {len(shas)} VILLA_SHA; arm flatten mode {sorted(modes)}")
    if len(shas) != 1 or modes != {"deterministic"}:
        print(
            "\nVERDICT: VOID -- not one tree, or an arm was not flattened deterministically."
        )
        return 1

    axis = mesh_axis(so)
    PA, mA = load_grid(str(so / REF / FLAT))
    Pin, mIn = load_grid(str(so / IN / FLAT))
    Pout, mOut = load_grid(str(so / OUT / FLAT))
    t = transmission(PA, mA, Pin, mIn, Pout, mOut, axis, DELTA, frac=a.frac)
    print(
        f"  mesh axis {axis[0]:.1f}, {axis[1]:.1f}; mesh offsets -{DELTA:g} / +{DELTA:g} vx\n"
    )
    print(
        f"  {'':>6}{'arm (outward normal)':>22}{'perfect transmission':>22}{'T':>8}{'in-plane':>10}"
    )
    print(
        f"  {'in':>6}{t['arm_in']:>+22.2f}{t['ref_in']:>+22.2f}{t['T_in']:>8.2f}{t['in_plane_in']:>10.2f}"
    )
    print(
        f"  {'out':>6}{t['arm_out']:>+22.2f}{t['ref_out']:>+22.2f}{t['T_out']:>8.2f}{t['in_plane_out']:>10.2f}"
    )
    v, read = verdict(t["T_in"], t["T_out"])
    print(f"\nVERDICT: {v}\n  {read}")
    print(
        "\n  This measures geometry only. It says nothing about ink: no arm was rendered,"
    )
    print(
        "  and whether fitting code CAN impose a uniform offset is a separate question."
    )
    if a.json:
        Path(a.json).write_text(
            json.dumps(t | {"verdict": v, "axis": axis}, indent=1) + "\n"
        )
        print(f"\nwrote {a.json}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
