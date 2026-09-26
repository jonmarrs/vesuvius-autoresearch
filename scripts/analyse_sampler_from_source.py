"""Does vc_render_tifxyz built from villa source score differently from the published one?

Implements `docs/preregistration/2026-09-25_sampler_from_source.md`. **Written, with its tests,
before any arm was rendered.**

Every render in this repo samples the ink volume with the vc_render_tifxyz in villa's PUBLISHED
runtime image (:edge == :main == sha256:bad516f6..., built 2026-05-13). A user who builds
volume-cartographer from source today gets a different binary. Here ONE flat surface
(`detfit_up1`'s own `w120-129_flat`, reused, never re-solved) is sampled by:

* `smp_pub`   -- the published sampler (image vc-render:local), which must reproduce detfit_up1;
* `smp_src_a`, `smp_src_b` -- the sampler built from villa 75c79ac5f (vc-render:sampler-75c79ac5f).

Nothing else differs: same flat surface (byte-checked), same Python stage, same trim binary,
same scorer.
"""

import argparse
import json
import statistics as st
import sys
from pathlib import Path

SPIRAL_OUT = Path("/home/jon/openclaw-workspace/Neo-VM/spiral_out")
REF = "detfit_up1"
PUB, SRC = ("smp_pub",), ("smp_src_a", "smp_src_b")
SAMPLER_SHA = "75c79ac5f506d4b9a89bcfbef8e8c0f2f0c3acb3"
INK = "total_fg_pixels"
REPRO_TOL = 1e-4  # 0.01%
INERT = 0.005  # 0.5%


def read_arm(work: Path) -> dict:
    ink = json.loads((work / "ink_metric" / "metrics.json").read_text())["summary"][INK]
    sampler = work / "SAMPLER"
    return {
        "ink": float(ink),
        "sampler": sampler.read_text().strip() if sampler.exists() else "published",
        "flat_md5": (work / "FLAT_MD5").read_text().strip()
        if (work / "FLAT_MD5").exists()
        else None,
        "reuse_engaged": (work / "REUSE_OK").exists(),
    }


def rel(a: float, b: float) -> float:
    return a / b - 1.0


def decide(arms: dict[str, dict], ref_ink: float, ref_flat_md5: str) -> dict:
    missing = [a for a in PUB + SRC if a not in arms]
    if missing:
        raise ValueError(f"partial sample refused: missing {missing}")
    fails = []
    for a in PUB + SRC:
        r = arms[a]
        if not r["reuse_engaged"]:
            fails.append(f"{a}: reuse-flatten did not engage")
        if r["flat_md5"] != ref_flat_md5:
            fails.append(f"{a}: flat surface differs from {REF}'s")
    if arms["smp_pub"]["sampler"] != "published":
        fails.append("smp_pub: not the published sampler")
    for a in SRC:
        if not arms[a]["sampler"].startswith(SAMPLER_SHA):
            fails.append(
                f"{a}: sampler {arms[a]['sampler']!r} is not source {SAMPLER_SHA[:9]}"
            )
    if fails:
        return {"verdict": "INVALID", "failed_gates": fails}
    pub_repro = rel(arms["smp_pub"]["ink"], ref_ink)
    src_repro = rel(arms["smp_src_b"]["ink"], arms["smp_src_a"]["ink"])
    out = {"published_reproducibility": pub_repro, "source_reproducibility": src_repro}
    if abs(pub_repro) > REPRO_TOL:
        return {**out, "verdict": "INVALID", "failed_gates": [
            f"re-sampling the same flat with the same sampler moved ink {pub_repro:+.4%}: "
            "the reuse path is not reproducing, so no sampler comparison is attributable"]}  # fmt: skip
    src = st.mean([arms[a]["ink"] for a in SRC])
    effect = rel(src, arms["smp_pub"]["ink"])
    out.update(
        {"effect": effect, "source_mean": src, "published": arms["smp_pub"]["ink"]}
    )
    floor = abs(src_repro)
    if floor > REPRO_TOL:
        out["source_deterministic"] = False
        out["verdict"] = (
            "SAMPLER CHANGES INK (source sampler nondeterministic)"
            if abs(effect) > max(INERT, 3 * floor)
            else "NOT RESOLVED (source sampler nondeterministic)"
        )
        return out
    out["source_deterministic"] = True
    out["verdict"] = (
        "SAMPLER INERT (within 0.5%)" if abs(effect) < INERT else "SAMPLER CHANGES INK"
    )
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--spiral-out", type=Path, default=SPIRAL_OUT)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    arms = {a: read_arm(args.spiral_out / a) for a in PUB + SRC}
    ref = args.spiral_out / REF
    ref_ink = json.loads((ref / "ink_metric" / "metrics.json").read_text())["summary"][
        INK
    ]
    ref_md5 = (args.spiral_out / "smp_pub" / "REF_FLAT_MD5").read_text().strip()
    res = decide(arms, float(ref_ink), ref_md5)
    res["per_arm"] = {**{a: arms[a]["ink"] for a in PUB + SRC}, REF: float(ref_ink)}
    args.out.write_text(json.dumps(res, indent=2) + "\n")
    print(res["verdict"])
    for k in ("effect", "published_reproducibility", "source_reproducibility"):
        if k in res:
            print(f"  {k}: {res[k]:+.4%}")
    for f in res.get("failed_gates", []):
        print("  GATE FAILED:", f)
    return 0


if __name__ == "__main__":
    sys.exit(main())
