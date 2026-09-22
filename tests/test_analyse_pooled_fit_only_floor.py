"""The pooled-floor rule, tested before any arm of the study scored.

Two properties carry the study: a CV never appears without its interval, and
the failure branch refuses to pool arms from different instruments. Both are
structural answers to things that went wrong earlier this week.
"""

import json
import re
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
SCRIPT = REPO / "scripts" / "analyse_pooled_fit_only_floor.py"
sys.path.insert(0, str(REPO / "scripts"))
from analyse_pooled_fit_only_floor import GROUPS, STOCK, ci  # noqa: E402

SHA = "be09a85035059fd83471b1632b5898c62f2c65b1"
IMG = "sha256:deadbeef"


def _arm(root: Path, name: str, val: float, sha: str = SHA, img: str = IMG) -> None:
    d = root / name / "ink_metric"
    d.mkdir(parents=True)
    (d / "metrics.json").write_text(json.dumps({"summary": {"total_fg_pixels": val}}))
    (root / name / "VILLA_SHA").write_text(sha + "\n")
    (root / name / "RENDER_IMAGE").write_text(
        f"image=vc-render:local\nimage_id={img}\n"
    )


def _tree(root: Path, spread: float = 0.05, **over) -> Path:
    base = {"curbase": 3_000_000, "nosamecur": 2_900_000, "anchor10cov": 2_850_000}
    for g, arms in GROUPS.items():
        for k, a in enumerate(arms):
            _arm(
                root,
                a,
                base[g] * (1 + spread * (k - len(arms) / 2) / len(arms)),
                **over,
            )
    for g, arms in STOCK.items():
        for k, a in enumerate(arms):
            _arm(root, a, base[g] * (1 + 0.06 * (k - len(arms) / 2) / len(arms)))
    return root


def run(root: Path):
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--spiral-out", str(root)],
        capture_output=True,
        text=True,
    )


def test_partial_sample_is_refused(tmp_path):
    _tree(tmp_path)
    (tmp_path / "detfit_an3" / "ink_metric" / "metrics.json").unlink()
    r = run(tmp_path)
    assert r.returncode != 0 and "refused" in (r.stdout + r.stderr)


def test_mixed_villa_sha_refuses_to_pool(tmp_path):
    """THE failure branch: a floor pooled across instruments is not a floor."""
    _tree(tmp_path)
    (tmp_path / "detfit_an1" / "VILLA_SHA").write_text("0123456789abcdef\n")
    r = run(tmp_path)
    assert r.returncode == 1
    assert "NOT POOLED" in r.stdout
    assert "POOLED fit-only CV" not in r.stdout, (
        "voided study must not also emit a figure"
    )


def test_mixed_image_id_refuses_to_pool(tmp_path):
    _tree(tmp_path)
    (tmp_path / "detfit_ns2" / "RENDER_IMAGE").write_text("image_id=sha256:other\n")
    r = run(tmp_path)
    assert r.returncode == 1 and "NOT POOLED" in r.stdout


def test_no_cv_is_printed_without_its_interval(tmp_path):
    r = run(_tree(tmp_path))
    assert r.returncode == 0, r.stderr
    for line in r.stdout.splitlines():
        if "CV" in line and re.search(r"\b0\.\d{4}\b", line) and "table" not in line:
            if line.strip().startswith(
                ("group", "curbase", "nosamecur", "anchor10cov")
            ):
                continue  # the per-group table, labelled as such
            assert "95% CI" in line and "df=" in line, f"bare CV: {line!r}"


def test_thresholds_match_the_registration():
    src = SCRIPT.read_text()
    assert "LO, HI = 0.055, 0.075" in src
    assert "PRED_LO, PRED_HI = 0.040, 0.075" in src


def test_interval_is_chi_square_at_df11():
    lo, hi = ci(0.06, 11)
    assert 0.041 < lo < 0.043 and 0.099 < hi < 0.104
    assert 2.3 < hi / lo < 2.5


def test_the_twelve_arms_give_df_9_not_11(tmp_path):
    """Twelve arms in three groups leave 12 - 3 = 9 degrees of freedom. The
    registration said df=11 (a 2.4x interval); at df=9 it is 2.65x. The script
    derives df from the groups, so pin what it derives rather than a typed df."""
    assert sum(len(v) for v in GROUPS.values()) - len(GROUPS) == 9
    r = run(_tree(tmp_path))
    pooled = next(ln for ln in r.stdout.splitlines() if "POOLED fit-only CV" in ln)
    assert "df=9" in pooled, pooled
    lo, hi = ci(0.06, 9)
    assert 2.6 < hi / lo < 2.7
