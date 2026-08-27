"""If a detector had signal on PHerc 1667, would `col_gutter_auc` see it?

PRE-REGISTERED. Committed before the run, decision rule included.

WHY. ScrollGT's column family reports every model and floor we have tried at
near-chance on `pherc1667_merged_columns`. That is ambiguous in a way that
matters, and nothing currently resolves it:

  * if the metric works, near-chance is a real finding -- our detectors do not
    transfer to PHerc 1667, consistent with the weak cross-scroll transfer
    measured elsewhere in this project;
  * if the metric cannot see signal that is there, the column family's published
    numbers are unsafe, and this project has already had one "everything reads at
    chance" headline reverse completely when the cause turned out to be our own
    registration bug.

The controls that exist are all NEGATIVE: a constant prediction scores exactly
0.5, a papyrus-mask prediction scores 0.5 because gutters are papyrus too, and
random noise shows the granularity of an 18-versus-17 AUC. The one positive
control, the geometry oracle at 1.0, is CIRCULAR: it is built from the same
column boxes the metric scores against, so of course it scores perfectly. There
is no independent evidence that a genuine, imperfect ink signal would register.

WHAT THIS DOES. Injects a column-concentrated signal of KNOWN strength into a
realistic background and measures what `col_gutter_auc` reports. That converts
"near-chance" from an ambiguous observation into a statement with a scale
attached: the weakest signal the metric can distinguish from noise.

This is the same power-calibration this project used on the locality statistic
in the winding work, where it showed a statistic saturating and inverted the
conclusion drawn from it. A metric's silence means nothing until you know what
it would take to make it speak.

DESIGN. The prediction is `base + amplitude * column_indicator + noise`:

  * `column_indicator` is 1 inside a scored text column and 0 elsewhere, taken
    from the target's own `columns.json`, so the injected signal is exactly the
    thing the metric looks for. This is the most favourable possible signal
    shape, which is the point: if the metric cannot see THIS at a given
    amplitude, it certainly cannot see a real detector's messier output.
  * noise is spatially smooth rather than white, because a real detector's errors
    are correlated over patches of papyrus, and white noise averages away inside
    a region of thousands of pixels while correlated noise does not. Using white
    noise here would flatter the metric badly.
  * everything is restricted to the target's valid mask.

DECISION RULE, fixed in advance. Let A* be the smallest injected amplitude, as a
fraction of the noise standard deviation, at which median `col_gutter_auc` across
seeds first exceeds 0.75:

  * If A* <= 0.5, the metric is sensitive: a signal at half the noise level is
    already detected, so near-chance from a real model means that model has
    little or no column-concentrated signal on this scroll. The published
    near-chance results stand as a finding about the models.
  * If A* >= 2.0, the metric is blunt: it needs a signal twice the noise before
    it responds, and near-chance is uninformative about the models. The column
    family's published numbers should carry that caveat.
  * Between those, report the number and draw no verdict.

The 0.75 threshold is chosen because the README already publishes ~0.58 as the
granularity floor from random noise at this n; 0.75 sits clear of that floor
without demanding near-perfection.

WHAT THIS CANNOT DO. It says nothing about whether the column registration is
correct. That is a separate question with its own evidence (three strips
independently recovering the same transform, tiling closure of 3 px over 30,097).
This asks only about the metric's power given the registration.

Run:
    CUDA_VISIBLE_DEVICES="" uv run python scripts/probe_column_metric_power.py
"""

import json
import os
import sys

os.environ.setdefault("CUDA_VISIBLE_DEVICES", "")

import numpy as np  # noqa: E402

_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(_REPO, "scripts"))

SCROLLGT = os.path.join(os.path.dirname(_REPO), "scrollgt")
TARGET = os.path.join(SCROLLGT, "data", "pherc1667_merged_columns")
OUT = os.path.join(_REPO, "reports", "column_metric_power.txt")

AMPLITUDES = [0.0, 0.125, 0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0]
NOISE_SIGMA_CELLS = 40.0  # smoothing length of the correlated background, in grid px
N_SEEDS = 5
SEED = 20260827
AUC_THRESHOLD = 0.75
SENSITIVE_AT = 0.5
BLUNT_AT = 2.0


def load_target():
    meta = json.load(open(os.path.join(TARGET, "meta.json")))
    cols = json.load(open(os.path.join(TARGET, "columns.json")))
    from PIL import Image

    valid = (
        np.array(Image.open(os.path.join(TARGET, "valid_mask.png")).convert("L")) > 0
    )
    return meta, cols, valid


def column_indicator(cols, shape):
    """1 inside a scored text column, 0 elsewhere. The metric's own target shape."""
    ind = np.zeros(shape, dtype=np.float32)
    entries = cols["columns"] if isinstance(cols, dict) else cols
    # The scorer keys on `transcription`, not `status`; `status` is the name it
    # gives that field internally. Reading the wrong key here would inject the
    # signal into nothing and produce a fake "blunt metric" verdict.
    for c in entries:
        if c.get("transcription") != "text":
            continue
        x0, x1 = int(c["gx0"]), int(c["gx1"])
        ind[:, max(x0, 0) : min(x1, shape[1])] = 1.0
    return ind


def correlated_noise(shape, rng, sigma=NOISE_SIGMA_CELLS):
    """Smooth noise: a real detector's errors are correlated over patches.

    White noise would average to nothing inside a region of thousands of pixels
    and would make the metric look far more sensitive than it is.
    """
    from scipy.ndimage import gaussian_filter

    f = rng.standard_normal(shape).astype(np.float32)
    f = gaussian_filter(f, sigma, mode="nearest")
    sd = float(f.std())
    return f / sd if sd > 0 else f


def score(pred, target_dir):
    sys.path.insert(0, os.path.join(SCROLLGT, "src"))
    from scrollgt.columns import score_columns

    tmp = os.path.join("/tmp", "colpower_pred.npy")
    np.save(tmp, pred.astype(np.float32))
    return score_columns(tmp, target_dir)


def main():
    meta, cols, valid = load_target()
    shape = tuple(meta["geometry"]["grid_shape"])
    if valid.shape != shape:
        from PIL import Image

        valid = (
            np.array(
                Image.open(os.path.join(TARGET, "valid_mask.png"))
                .convert("L")
                .resize((shape[1], shape[0]), Image.NEAREST)
            )
            > 0
        )
    ind = column_indicator(cols, shape)

    # The noise field depends only on the seed, not the amplitude. Building it
    # once per seed rather than once per (seed, amplitude) is a tenfold saving on
    # a 2061 x 30097 grid, and guarantees every amplitude sees the SAME
    # background, so the column is a clean sweep in amplitude rather than a sweep
    # in amplitude crossed with noise draw.
    noises = [
        correlated_noise(shape, np.random.default_rng(SEED + 97 * s))
        for s in range(N_SEEDS)
    ]

    rows = []
    for amp in AMPLITUDES:
        aucs = []
        for s in range(N_SEEDS):
            pred = 0.5 + 0.1 * (noises[s] + amp * ind)
            pred = np.clip(pred, 0.0, 1.0) * valid
            r = score(pred, TARGET)
            aucs.append(float(r["metrics"].get("col_gutter_auc", float("nan"))))
        rows.append(
            (amp, float(np.median(aucs)), float(np.min(aucs)), float(np.max(aucs)))
        )

    first = next((a for a, med, _, _ in rows if med > AUC_THRESHOLD), None)

    lines = [
        "If a detector had signal on PHerc 1667, would col_gutter_auc see it?",
        "",
        "Near-chance from a metric means nothing until you know what it would take to make",
        "it speak. The column family's controls are all negative -- constant 0.5, papyrus",
        "mask 0.5, random noise showing the 18-versus-17 granularity -- and its one positive",
        "control, the geometry oracle at 1.0, is built from the same boxes the metric scores",
        "against, so it cannot tell us whether an imperfect real signal would register.",
        "",
        "Injected here: a column-concentrated signal of known amplitude on a spatially",
        f"correlated background (smoothing {NOISE_SIGMA_CELLS:.0f} grid px, because a real",
        "detector's errors are correlated over patches and white noise would average away",
        "inside a region of thousands of pixels, flattering the metric).",
        "",
        f"  grid {shape[0]} x {shape[1]}, {int(ind.any(axis=0).sum())} px of text column",
        f"  {N_SEEDS} seeds per amplitude",
        "",
        "   amplitude (x noise sd)   col_gutter_auc   (min .. max over seeds)",
        "  " + "-" * 68,
    ]
    for amp, med, lo, hi in rows:
        lines.append(f"   {amp:20.3f}   {med:14.4f}   ({lo:.4f} .. {hi:.4f})")
    lines.append("")

    if first is None:
        lines.append(
            f"  ⚠ The metric never exceeds {AUC_THRESHOLD} anywhere in the swept range, up to"
            f" {AMPLITUDES[-1]}x the noise. It is BLUNT by the pre-registered rule, and"
        )
        lines.append(
            "  near-chance from a real model says nothing about that model. The column"
        )
        lines.append("  family's published numbers should carry that caveat.")
    elif first <= SENSITIVE_AT:
        lines.append(
            f"  The metric first exceeds {AUC_THRESHOLD} at amplitude {first}x the noise,"
            f" at or below the pre-registered {SENSITIVE_AT}x. It is SENSITIVE:"
        )
        lines.append(
            "  a signal at half the noise level is already detected, so near-chance from a"
        )
        lines.append(
            "  real model means that model has little column-concentrated signal on this"
        )
        lines.append(
            "  scroll. The published results stand as a finding about the models."
        )
    elif first >= BLUNT_AT:
        lines.append(
            f"  ⚠ The metric first exceeds {AUC_THRESHOLD} only at amplitude {first}x the"
            f" noise, at or above the pre-registered {BLUNT_AT}x. It is BLUNT: it needs a"
        )
        lines.append(
            "  signal twice the noise before it responds, so near-chance is uninformative"
        )
        lines.append("  about the models and the published numbers need that caveat.")
    else:
        lines.append(
            f"  The metric first exceeds {AUC_THRESHOLD} at amplitude {first}x the noise,"
            f" between the pre-registered {SENSITIVE_AT}x and {BLUNT_AT}x. No verdict:"
        )
        lines.append("  the number is reported and the question stays open.")
    lines.append("")
    lines.append(
        "This says nothing about whether the column registration is correct. That has its"
        " own evidence -- three figure strips independently recovering the same transform,"
        " tiling closure of 3 px over 30,097 -- and is a separate question. This asks only"
        " what the metric can see given that registration."
    )
    text = "\n".join(lines) + "\n"
    with open(OUT, "w") as fh:
        fh.write(text)
    print(text)


if __name__ == "__main__":
    main()
