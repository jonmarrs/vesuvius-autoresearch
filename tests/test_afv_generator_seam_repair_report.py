"""reports/afv_generator_seam_repair.md (finding 140): every figure from reports/afv_generator_seam_repair.json, the
record the runner's verdict step wrote once, and the registration's predictions."""

from __future__ import annotations

import importlib.util
import json
import statistics
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location(
    "afv_generator_seam_repair", ROOT / "scripts/afv_generator_seam_repair.py"
)
assert _spec and _spec.loader
sr = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sr)

RECORD = ROOT / "reports/afv_generator_seam_repair.json"
REPORT = ROOT / "reports/afv_generator_seam_repair.md"
REGISTRATION = ROOT / "docs/preregistration/2026-11-27_afv_generator_seam_repair.md"
ARMS = ("main", "trim", "repaired")


def flat(path: Path = REPORT) -> str:
    return " ".join(path.read_text().split())


def record() -> dict:
    return json.loads(RECORD.read_text())


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%".replace("-", "−")


def gain(rows, arm, base, tol="tol4") -> float:
    return (
        rows[arm][tol]["erl_merge_penalized"] / rows[base][tol]["erl_merge_penalized"]
        - 1
    )


def cube_line(cube: str, r: dict) -> str:
    rows = r["rows"]
    e = " | ".join(str(rows[a]["tol4"]["erl_merge_penalized"]) for a in ARMS)
    merges = " → ".join(str(rows[a]["tol2"]["merges"]) for a in ARMS)
    dup = " → ".join(f"{rows[a]['duplicated_share']:.3f}" for a in ARMS)
    lost = " → ".join(str(rows[a]["crossings"]["lost"]) for a in ARMS)
    cov = rows["repaired"]["tol4"]["coverage"] / rows["main"]["tol4"]["coverage"] - 1
    return (f"| `{cube}` | {r['block']} | {e} | {pct(gain(rows, 'repaired', 'main'))} | "
            f"{pct(gain(rows, 'repaired', 'main', 'tol2'))} | {pct(gain(rows, 'repaired', 'trim'))} | {merges} | "
            f"{dup} | {lost} | {pct(cov)} |")  # fmt: skip


def totals(cubes: dict) -> dict:
    R = [c["rows"] for c in cubes.values()]
    med = statistics.median

    def by(f):
        return " | ".join(f(a) for a in ARMS)

    return {
        "crossings": by(lambda a: " / ".join(str(sum(r[a]["crossings"][k] for r in R)) for k in ("whole", "broken", "lost"))),  # noqa: E501
        "merges2": by(lambda a: str(sum(r[a]["tol2"]["merges"] for r in R))),
        "merges4": by(lambda a: str(sum(r[a]["tol4"]["merges"] for r in R))),
        "dup": by(lambda a: f"{med(r[a]['duplicated_share'] for r in R):.3f}"),
        "written": by(lambda a: f"{sum(r[a]['written'] for r in R):,}"),
        "length": by(lambda a: f"{round(sum(r[a]['length'] for r in R)):,}"),
        "cov4": by(lambda a: f"{med(r[a]['tol4']['coverage'] for r in R):.4f}"),
        "cov2": by(lambda a: f"{med(r[a]['tol2']['coverage'] for r in R):.4f}"),
        "prec4": by(lambda a: f"{med(r[a]['tol4']['precision'] for r in R):.4f}"),
        "splits4": by(lambda a: f"{sum(r[a]['tol4']['splits'] for r in R):,}"),
    }  # fmt: skip


TOTAL_LABELS = {
    "crossings": "face crossings whole / broken / lost",
    "merges2": "merges, τ = 2, summed",
    "merges4": "merges, τ = 4, summed",
    "dup": "written length beside a same-family copy, median",
    "written": "fibers written, summed",
    "length": "written length, voxels, summed",
    "cov4": "coverage, τ = 4, median",
    "cov2": "coverage, τ = 2, median",
    "prec4": "precision, τ = 4, median",
    "splits4": "splits, τ = 4, summed",
}


def spread(cubes: dict, arm: str, base: str, tol: str) -> str:
    g = [gain(c["rows"], arm, base, tol) for c in cubes.values()]
    return f"{pct(statistics.median(g))} ({pct(min(g))} to {pct(max(g))})"


def kept_share(cubes: dict) -> list[float]:
    out = []
    for c in cubes.values():
        r = c["rows"]
        main, trim, rep = (r[a]["tol4"]["erl_merge_penalized"] for a in ARMS)
        out.append((rep - main) / (trim - main))
    return out


def predictions(d: dict) -> list[tuple[str, str, bool]]:
    s3, all18 = d["scroll3"], {**d["cubes"]["scroll3"], **d["cubes"]["confirm"]}
    up18 = sum(gain(c["rows"], "repaired", "main") > 0 for c in all18.values())
    cov = {a: statistics.median(c["rows"][a]["tol4"]["coverage"] / c["rows"]["main"]["tol4"]["coverage"] - 1
                                for c in all18.values()) for a in ("trim", "repaired")}  # fmt: skip
    return [
        ("P1", f"{s3['up_tol4']} of 8, median {pct(s3['median_gain_tol4'])}",
         s3["up_tol4"] >= 7 and s3["median_gain_tol4"] >= 0.08),
        ("P2", f"{s3['lost_crossings']['repaired']}", s3["lost_crossings"]["repaired"] <= 190),
        ("P3", f"{s3['duplicated_share_median']['repaired']:.3f}", s3["duplicated_share_median"]["repaired"] <= 0.15),
        ("P4", f"{up18} of 18", up18 >= 15),
        ("P5", f"{pct(cov['repaired'])} against the trim's {pct(cov['trim'])}", cov["repaired"] > cov["trim"]),
    ]  # fmt: skip


def test_the_verdict_is_the_registered_rule_applied_to_the_record():
    d, t = record(), flat()
    assert d["problems"] == [] and d["missing"] == []
    assert d["verdict"] == sr.verdict(d["scroll3"]) == "REPAIR_KEEPS_THE_GAIN"
    assert d["scroll3"] == sr.summary(d["cubes"]["scroll3"])
    assert d["confirm"] == sr.summary(d["cubes"]["confirm"])
    assert set(d["cubes"]["scroll3"]) == set(sr.SETS["scroll3"][0])
    assert set(d["cubes"]["confirm"]) == set(sr.SETS["confirm"][0])
    assert f"**Decision `{d['verdict']}`.**" in t
    for s in d["cubes"].values():
        for r in s.values():
            assert r["reproduced"] and r["problems"] == []
            assert r["sha256"]["repaired_stitch"].startswith("62eddc21")
            assert r["sha256"]["old_first"].startswith("c9ab1700")
            assert r["sha256"]["old_zone"].startswith("362b78b1")
    assert "sha256 `62eddc21…`" in t


def test_the_per_cube_tables_are_the_record():
    d, t = record()["cubes"], flat()
    for s in ("scroll3", "confirm"):
        for c, r in d[s].items():
            assert cube_line(c, r) in t, c


def test_the_totals_are_the_record():
    d, t = record()["cubes"], flat()
    for s, head in (
        ("scroll3", "**Over the eight Scroll-3 cubes**"),
        ("confirm", "**Over the ten Scroll-1 and -5 cubes**"),
    ):  # noqa: E501
        part = t.split(head, 1)[1].split("**", 1)[0]
        for key, value in totals(d[s]).items():
            assert f"| {TOTAL_LABELS[key]} | {value} |" in part, (s, key)


def test_the_gain_spreads_and_kept_share_are_the_record():
    d, t = record()["cubes"], flat()
    for s, n in (("scroll3", 8), ("confirm", 10)):
        line = (f"| {n} | {spread(d[s], 'trim', 'main', 'tol4')} | {spread(d[s], 'repaired', 'main', 'tol4')} | "
                f"{spread(d[s], 'repaired', 'main', 'tol2')} | {spread(d[s], 'repaired', 'trim', 'tol4')} | "
                f"{statistics.median(kept_share(d[s])):.2f} |")  # fmt: skip
        assert line in t, s


def test_what_it_shows_is_the_record():
    d, t = record(), flat()
    s3, cf = d["cubes"]["scroll3"], d["cubes"]["confirm"]
    all18 = {**s3, **cf}

    def lost(cubes, arm):
        return sum(c["rows"][arm]["crossings"]["lost"] for c in cubes.values())

    extra = [lost(s, "trim") - lost(s, "main") for s in (s3, cf)]
    assert f"lost {extra[0]} more face crossings than main on Scroll 3" in t
    assert f"and {extra[1]} more on Scrolls 1 and 5" in t
    rep = [lost(s, "repaired") - lost(s, "main") for s in (s3, cf)]
    assert f"The repair loses {rep[0]} and {rep[1]} more." in t
    per = [
        c["rows"]["repaired"]["crossings"]["lost"]
        - c["rows"]["main"]["crossings"]["lost"]
        for c in all18.values()
    ]
    assert max(per) == 3 and sum(p < 0 for p in per) == 3 and min(per) == -1
    assert "at most 3 crossings more than main, and 1 fewer on three cubes" in t
    whole = {
        a: sum(c["rows"][a]["crossings"]["whole"] for c in s3.values()) for a in ARMS
    }
    assert (
        f"{whole['repaired']} of 1,304 on Scroll 3 (main {whole['main']}, trim {whole['trim']})"
        in t
    )
    for s in (s3, cf):
        w = {
            a: sum(c["rows"][a]["crossings"]["whole"] for c in s.values()) for a in ARMS
        }
        assert w["repaired"] == max(w.values())
    cov = {a: [c["rows"][a]["tol4"]["coverage"] / c["rows"]["main"]["tol4"]["coverage"] - 1 for c in all18.values()]
           for a in ("trim", "repaired")}  # fmt: skip
    assert (
        0.006 < max(abs(x) for x in cov["repaired"]) < 0.007
        and "to within 0.7% on all eighteen cubes" in t
    )
    assert f"(median {pct(statistics.median(cov['repaired']))})" in t
    assert all(x < 0 for x in cov["trim"])
    assert (
        f"below main on all eighteen (median {pct(statistics.median(cov['trim']))})"
        in t
    )
    below = [
        sum(gain(c["rows"], "repaired", "trim") < 0 for c in s.values())
        for s in (s3, cf)
    ]
    assert f"below the trim on {below[0]} of 8 and {below[1]} of 10 cubes" in t
    sp = {a: sum(c["rows"][a]["tol4"]["splits"] for c in s3.values()) for a in ARMS}
    assert f"({sp['main']:,} → {sp['repaired']:,})" in t
    assert (
        0.2 < 1 - sp["repaired"] / sp["main"] < 0.3
        and 0.45 < 1 - sp["trim"] / sp["main"] < 0.55
    )
    merges = {a: sum(c["rows"][a]["tol2"]["merges"] for c in s3.values()) for a in ARMS}
    assert (
        f"({merges['repaired']} against {merges['main']} at τ = 2 on Scroll 3; the trim had {merges['trim']})"
        in t
    )


def test_the_strategy_paragraph_is_the_record():
    d = record()
    t = (
        flat(ROOT / "docs/RESEARCH_STRATEGY.md")
        .split("[Finding 140]", 1)[1]
        .split("- [Finding", 1)[0]
    )
    s3, cf = d["scroll3"], d["confirm"]
    assert (
        f"rose over main on {s3['up_tol4']} of 8 cubes, by a median {pct(s3['median_gain_tol4'])}"
        in t
    )
    assert (
        f"(the posted trim: {pct(statistics.median(gain(c['rows'], 'trim', 'main') for c in d['cubes']['scroll3'].values()))})"
        in t
    )  # noqa: E501
    assert (
        f"with {s3['lost_crossings']['repaired']} face crossings lost against main's {s3['lost_crossings']['main']}"
        in t
    )  # noqa: E501
    assert f"(the posted trim: {s3['lost_crossings']['trim']})" in t
    assert f"`{d['verdict']}`" in t
    assert (
        f"the gain was {cf['up_tol4']} of 10, median {pct(cf['median_gain_tol4'])}" in t
    )
    kept = [
        statistics.median(kept_share(d["cubes"][s])) for s in ("scroll3", "confirm")
    ]
    assert f"a median {kept[0]:.2f} and {kept[1]:.2f} of the trim's gain" in t
    assert (
        f"(written-twice share {s3['duplicated_share_median']['repaired']:.3f} on Scroll 3"
        in t
    )


def test_the_predictions_table_is_the_registration_applied_to_the_record():
    reg, t = flat(REGISTRATION), flat()
    for claim in ("up on at least 7, median gain at least +8%", "at most 190 with the repair",
                  "at most 0.15 (main 0.246, trim 0.104)", "up over main on at least 15",
                  "falls less with the repair than with the trim"):  # fmt: skip
        assert claim in reg, claim
    for name, measured, held in predictions(record()):
        assert f"| {name} " in t
        assert f"| {measured} | {'yes' if held else 'no'} |" in t, name
    assert [held for *_, held in predictions(record())] == [
        True,
        True,
        False,
        True,
        True,
    ]
