"""villa's neural fiber volume tracer with its two hard-coded seeding scales set per micrometre.

villa's tracing/volume.py (ccb431818) seeds from the presence after smoothing it with a Gaussian of sigma 1 grid voxel
(`tile_dots`), and takes each seed's direction from a Hessian of sigma 1.5 (HESSIAN_SIGMA). Neither is a flag, and a
grid voxel's length in micrometres depends on the CT's pitch. `seeding_scaled` sets them on villa's module alone (scipy
itself is untouched) for the length of a `with` block; the patch refuses any smoothing call other than the one it
expects, so a change in villa's code fails loudly.

As a launcher, in villa's tracer environment (repro/fibers/setup_neural_tracer_env.sh):

    python scripts/neural_tracer_seeding.py --smoothing S [--hessian H] <villa volume arguments>

runs villa's own main() with the patch. Seeding runs in-process (--tile-workers 0, which villa counts among the
settings that only change speed): spawned workers would import villa's module unpatched. OUT/seeding.json records the
scales, and a resume at other scales is refused, as villa refuses other settings.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path

VILLA_SMOOTHING, VILLA_HESSIAN = 1.0, 1.5  # tracing/volume.py at ccb431818


class SmoothingScaled:
    """scipy.ndimage as villa's volume module sees it, with its presence smoothing (sigma 1.0) at sigma `scale`."""

    def __init__(self, ndimage, scale: float):
        self._nd, self.scale = ndimage, scale

    def __getattr__(self, name):
        return getattr(self._nd, name)

    def gaussian_filter(self, a, sigma, *args, **kw):
        if sigma != VILLA_SMOOTHING:
            raise ValueError(
                f"villa's volume.py smoothed at sigma {sigma}, not {VILLA_SMOOTHING}: its code changed"
            )
        return self._nd.gaussian_filter(a, self.scale, *args, **kw)


@contextlib.contextmanager
def seeding_scaled(vol, smoothing: float, hessian: float | None = None):
    """villa's volume module `vol` with its presence smoothing at sigma `smoothing` and, given, its Hessian at
    `hessian` (radius by scipy's truncate 4, as villa sets it)."""
    saved = (vol.ndimage, vol.HESSIAN_SIGMA, vol.HESSIAN_RADIUS, vol._KERNELS)
    try:
        vol.ndimage = SmoothingScaled(saved[0], smoothing)
        if hessian is not None:
            vol.HESSIAN_SIGMA, vol.HESSIAN_RADIUS = hessian, int(4 * hessian + 0.5)
            vol._KERNELS = vol._hessian_kernels()
        yield vol
    finally:
        vol.ndimage, vol.HESSIAN_SIGMA, vol.HESSIAN_RADIUS, vol._KERNELS = saved


def split_argv(argv: list[str]) -> tuple[float, float | None, list[str]]:
    """(smoothing, hessian, villa's arguments), with seeding forced in-process."""
    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument(
        "--smoothing",
        type=float,
        required=True,
        help="presence smoothing sigma, grid voxels",
    )
    ap.add_argument(
        "--hessian",
        type=float,
        help="Hessian sigma, grid voxels (default: villa's 1.5)",
    )
    ns, rest = ap.parse_known_args(argv)
    # argparse expands an unambiguous abbreviation (--tile-work 4), which the
    # checks below would not see.
    for a in rest:
        name = a.split("=", 1)[0]
        if "--tile-workers".startswith(name) and len("--tile-") < len(name) < len(
            "--tile-workers"
        ):
            raise SystemExit(f"{a}: spell out --tile-workers, so it can be checked")
    workers = [rest[i + 1] for i, a in enumerate(rest[:-1]) if a == "--tile-workers"]
    workers += [a.split("=", 1)[1] for a in rest if a.startswith("--tile-workers=")]
    if any(w != "0" for w in workers):
        raise SystemExit(
            "--tile-workers must be 0: spawned workers would seed with villa's unpatched module"
        )
    if not workers:
        rest = [*rest, "--tile-workers", "0"]
    return ns.smoothing, ns.hessian, rest


def record_seeding(out: Path, smoothing: float, hessian: float | None = None) -> None:
    """OUT/seeding.json, beside villa's run.json; a resume must use the same scales."""
    rec = {
        "presence_smoothing_sigma": smoothing,
        "hessian_sigma": VILLA_HESSIAN if hessian is None else hessian,
        "villa_default": VILLA_SMOOTHING,
        "villa_default_hessian": VILLA_HESSIAN,
        "launcher": "scripts/neural_tracer_seeding.py",
    }
    path = Path(out) / "seeding.json"
    if not path.exists() and (Path(out) / "run.json").exists():
        raise SystemExit(
            f"{out} holds a run started without this launcher: its seeding scales are not recorded"
        )
    if path.exists():
        old = json.loads(path.read_text())
        if old != rec:
            raise SystemExit(f"{path} records other seeding scales: {old}, not {rec}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(rec, indent=1) + "\n")


def main(argv: list[str] | None = None) -> int:
    smoothing, hessian, rest = split_argv(sys.argv[1:] if argv is None else argv)
    from vesuvius.neural_tracing.tracers.fibers.tracing import volume as vol

    ap = argparse.ArgumentParser(add_help=False)
    ap.add_argument("--out", required=True)
    record_seeding(Path(ap.parse_known_args(rest)[0].out), smoothing, hessian)
    with seeding_scaled(vol, smoothing, hessian):
        return vol.main(rest) or 0


if __name__ == "__main__":
    sys.exit(main())
