"""scripts/afv_generator_cross_block_duplicates.py (finding 108's run): the catalogue gate, the patch it tests, the
registered decision rule, and the registration's figures from its evidence."""

from __future__ import annotations

import copy
import hashlib
import json
import statistics
import subprocess
import sys
import types
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_cross_block_duplicates as xd  # noqa: E402
import afv_generator_default_zone as dz  # noqa: E402

VILLA = Path("/home/jon/openclaw-workspace/Neo-VM/projects/villa")
PATCHED = (
    Path("/home/jon/openclaw-workspace/Neo-VM/projects/villa-wt-afv-seam-c3d9")
    / xd.CATALOG
)
MAIN = "7e6b82164d014ed485aa027011f31070923fc0a9"
REGISTRATION = (
    xd.ROOT / "docs/preregistration/2026-11-09_afv_generator_cross_block_duplicates.md"
)
EVIDENCE = (
    xd.ROOT
    / "reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json"
)


def flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def patch_lines(sign: str, name: str) -> list[str]:
    out, current = [], None
    for line in xd.PATCH.read_text().splitlines():
        if line.startswith("diff --git"):
            current = line.rsplit("/", 1)[1]
        elif (
            current == name and line.startswith(sign) and not line.startswith(sign * 3)
        ):
            out.append(line[1:])
    return out


def test_the_gate_s_strings_are_the_patch_s_catalogue_lines():
    added, removed = patch_lines("+", "catalog.py"), patch_lines("-", "catalog.py")
    assert xd.CALL.splitlines() == [
        line
        for line in added
        if "cross_block_duplicate(sp,lp)" in line or "ov.MAX_P90" in line
    ]
    assert xd.COMMENT[0].splitlines() == [
        line
        for line in added
        if line.strip().startswith("# Other") or "only the two tests" in line
    ]
    assert removed == xd.COMMENT[1].splitlines()
    assert "def cross_block_duplicate(a, b):" in added
    assert (
        sum(
            1
            for line in patch_lines("+", "test_stitch.py")
            if line.startswith("def test_")
        )
        == 2
    )


def test_the_catalogue_gate_accepts_the_patch_and_nothing_more(tmp_path):
    if not (VILLA / ".git").exists() or not PATCHED.exists():
        pytest.skip("the villa clone or the patched worktree is not on this machine")
    assert xd.catalog_problems(VILLA, MAIN, PATCHED) == []
    text = PATCHED.read_text()
    for mutant in (text.replace("GAP_CAP = 30.", "GAP_CAP = 31."), text.replace(xd.CALL, ""),
                   text.replace("match['contained'] == 'B'", "match['contained'] == 'A'") + "\n"):  # fmt: skip
        p = tmp_path / "catalog.py"
        p.write_text(mutant)
        assert xd.catalog_problems(VILLA, MAIN, p), mutant[:40]


def row(erl4: float, merges: int, dup: float) -> dict:
    return {
        "tol2": {"erl_merge_penalized": 10.0, "merges": merges},
        "tol4": {"erl_merge_penalized": erl4, "merges": merges},
        "duplicated_share": dup,
    }


def results(gains4, merges=(10, 10), dups=(0.10, 0.05), problems=()):
    return {
        c: {
            "identity_problems": list(problems),
            "rows": {
                "trim": row(30.0, merges[0], dups[0]),
                "trim+dup": row(30.0 * (1 + g), merges[1], dups[1]),
            },
        }
        for c, g in zip(bs.HELD_OUT, gains4, strict=True)
    }


def test_the_decision_rule():
    up = [0.05] * 8
    assert xd.verdict(results(up))["decision"] == "SUPPORTED"
    assert (
        xd.verdict(results([0.05] * 5 + [-0.01] * 3))["decision"] == "NOT_SUPPORTED"
    )  # P1: 5 of 8
    assert (
        xd.verdict(results([0.05] * 6 + [-0.01] * 2))["decision"] == "SUPPORTED"
    )  # 6 of 8 holds
    assert (
        xd.verdict(results(up, merges=(10, 11)))["decision"] == "NOT_SUPPORTED"
    )  # P3: 1.10 x
    assert (
        xd.verdict(results(up, merges=(20, 21)))["decision"] == "SUPPORTED"
    )  # 1.05 x holds
    assert xd.verdict(results([0.02] * 8))["decision"] == "PARTIAL"  # P2: median 0.02
    assert (
        xd.verdict(results(up, dups=(0.10, 0.08)))["decision"] == "PARTIAL"
    )  # P4: 0.8 x
    assert xd.verdict(results(up, problems=["x"]))["decision"] == "NO_VERDICT"
    v = xd.verdict(results(up))
    assert v["P1_tol4_up"] == [8, True] and v["P3_merges_tol2"] == [[80, 80], True]


def test_the_registration_is_the_rule_and_names_its_inputs():
    t = flat(REGISTRATION)
    assert "`scripts/afv_generator_cross_block_duplicates.py`" in t
    assert (
        "`repro/fibers/villa_fiber_generator_cross_block_duplicates_c3d9da6fe.patch`"
        in t
    )
    assert (
        "higher with the change on at least 6 of 8 cubes" in t and "at least 0.03" in t
    )
    assert "at most 1.05 times the trim's" in t and "at most 0.7 times the trim's" in t
    assert f"`{xd.DIAGNOSED}`" in t and xd.DIAGNOSED in bs.HELD_OUT
    for name in ("NO_VERDICT", "NOT_SUPPORTED", "PARTIAL", "SUPPORTED"):
        assert f"`{name}`" in t


def test_the_registration_s_figures_are_its_evidence():
    e, t = json.loads(EVIDENCE.read_text()), flat(REGISTRATION)
    rows = e["dev_screen"]["rows"]
    assert len(rows) == 8 and not set(rows) & set(bs.HELD_OUT)
    assert all(
        r["E16P"] | {"loose_suppressed": 0} == r["E16L"] | {"loose_suppressed": 0}
        for r in rows.values()
    )
    for tol, tau in (("tol4", "4"), ("tol2", "2")):
        g = [
            r["E16P"][f"{tol}_erl_merge_penalized"]
            / r["E16"][f"{tol}_erl_merge_penalized"]
            - 1
            for r in rows.values()
        ]
        assert all(x > 0 for x in g)
        assert (
            f"{pct(statistics.median(g))} at τ = {tau} ({pct(min(g))} to {pct(max(g))})"
            in t
        )
    for tol, tau in (("tol2", "2"), ("tol4", "4")):
        m = [sum(r[v][f"{tol}_merges"] for r in rows.values()) for v in ("E16", "E16P")]
        assert f"{m[0]} → {m[1]} at τ = {tau}" in t
    d = [
        statistics.median(r[v]["dup_share"] for r in rows.values())
        for v in ("E16", "E16P")
    ]
    assert f"The median duplicated share fell {d[0]:.3f} → {d[1]:.3f}" in t
    x = {
        k: [sum(r[v][f"x_{k}"] for r in rows.values()) for v in ("E16", "E16P")]
        for k in ("whole", "broken", "lost")
    }
    assert (f"whole ones rose {x['whole'][0]} → {x['whole'][1]}, broken fell {x['broken'][0]} → {x['broken'][1]} and "
            f"lost fell {x['lost'][0]} → {x['lost'][1]}") in t  # fmt: skip
    z = e["zone_residue"]
    band = z["where"]["patched"]["by_face_distance"]
    assert (
        f"{100 * sum(b['share_of_all_dup'] for b in band[:4]):.1f}% of the doubled length lies within 32 voxels"
        in t
    )
    assert (
        f"Beyond 32 voxels the share is {z['where']['patched']['far_from_faces']['dup_share']}"
        in t
    )
    inner = [b["dup_share_in_bin"] for b in band[:3]]
    assert (
        f"{100 * min(inner):.0f}–{100 * max(inner):.0f}% of the length is doubled" in t
    )
    w = z["why_kept"]["patched"]
    assert f"{w['pairs']} pairs share at least 4 voxels" in t
    verdicts = w["strict_duplicate_verdict"]
    bbox = verdicts["short's bbox not inside long's"]
    assert (
        f"fails {verdicts['median > 0.20']} pairs" in t
        and f"the bounding box fails {bbox}" in t
    )
    assert (
        f"classifies {w['compare_kind']['duplicate']} of the pairs as duplicates and {w['compare_kind']['overlap']}"
        in t
    )
    k = z["what"]["patched"]
    assert (
        f"{100 * k['share_running_along_the_face']:.0f}% of them run along the face"
        in t
    )
    assert (
        f"a median {k['nearest_other_distance_p10_25_50_75_90'][2]:.2f} voxel away" in t
    )


def test_the_runner_parses_and_writes_the_record_once():
    runner = xd.ROOT / "repro/fibers/run_afv_generator_cross_block_duplicates.sh"
    subprocess.run(["bash", "-n", str(runner)], check=True)
    text = runner.read_text()
    assert (
        "reports/afv_generator_cross_block_duplicates.json" in text
        and "--patched-catalog" in text
    )


@pytest.mark.parametrize(
    "r, decision",
    [
        (results([0.028] * 8), "PARTIAL"),  # P2: a median under 0.03
        # P2 is the median (0.02), not the mean (0.0875)
        (results([0.02] * 5 + [0.2] * 3), "PARTIAL"),
        (results([0.05] * 8, merges=(100, 107)), "NOT_SUPPORTED"),  # P3: 1.07 x
        (results([0.05] * 8, dups=(0.10, 0.072)), "PARTIAL"),  # P4: 0.72 x
        (results([0.05] * 8, dups=(0.5, 0.35)), "SUPPORTED"),  # exactly 0.7 x holds
        # P1: an ERLpen that did not move is not higher, so 5 of 8
        (results([0.05] * 5 + [0.0] * 3), "NOT_SUPPORTED"),
        # the table's rows in order: a P1 or P3 miss outranks a P2 or P4 miss, and a failed gate outranks both
        (results([0.01] * 5 + [-0.01] * 3), "NOT_SUPPORTED"),
        (results([0.05] * 8, merges=(10, 11), dups=(0.10, 0.08)), "NOT_SUPPORTED"),
        (results([0.01] * 5 + [-0.01] * 3, problems=["x"]), "NO_VERDICT"),
    ],
)
def test_the_decision_rule_at_its_bars_and_in_the_table_s_order(r, decision):
    assert xd.verdict(r)["decision"] == decision


def test_one_cube_s_failed_gate_means_no_verdict():
    """The registration: "Gate, per cube; any failure means no verdict"."""
    r = results([0.05] * 8)
    r[bs.HELD_OUT[5]]["identity_problems"] = ["a module differs"]
    assert xd.verdict(r)["decision"] == "NO_VERDICT"


def test_the_verdict_step_writes_the_record_once_with_the_zone(tmp_path, monkeypatch):
    work, out = tmp_path / "work", tmp_path / "record.json"
    work.mkdir()
    r = results([0.05] * 8)
    for c, x in r.items():
        (work / f"{c}.json").write_text(json.dumps(x))
    (work / "zone.json").write_text(json.dumps({"zone": 1024}))
    argv = [Path(xd.__file__).name, "verdict", "--work", str(work), "--out", str(out)]
    monkeypatch.setattr(sys, "argv", argv)
    xd.main()
    first = out.read_text()
    record = {"verdict": xd.verdict(r), "cubes": r, "zone": {"zone": 1024}}
    assert first == json.dumps(record, indent=1) + "\n"
    assert record["verdict"]["decision"] == "SUPPORTED"
    worse = results([-0.05] * 8)[bs.HELD_OUT[0]]
    (work / f"{bs.HELD_OUT[0]}.json").write_text(json.dumps(worse))
    with pytest.raises(SystemExit, match="written once"):
        xd.main()
    assert out.read_text() == first


def test_run_and_zone_stitch_both_arms_unless_a_smoke_names_one(monkeypatch):
    """The launcher passes no --variants: the registered run is the default, and one arm alone is a smoke."""
    got: list = []
    monkeypatch.setattr(xd, "run", got.append)
    monkeypatch.setattr(xd, "zone", got.append)
    common = ["--work", "w", "--pr", "p", "--villa", "v", "--main", "m"]
    common += ["--patched-stitch", "s", "--patched-catalog", "c"]
    run = ["run", "--cube", "x", "--fields", "f"]
    for argv in (run, ["zone", "--zone-work", "z"], [*run, "--variants", "trim"]):
        monkeypatch.setattr(sys, "argv", [Path(xd.__file__).name, *argv, *common])
        xd.main()
    assert [a.variants for a in got] == [xd.VARIANTS, xd.VARIANTS, ("trim",)]
    runner = xd.ROOT / "repro/fibers/run_afv_generator_cross_block_duplicates.sh"
    assert "--variants" not in runner.read_text()


CATALOG_NAME = Path(xd.CATALOG).name
GATE = {
    "missing": "the patched catalog.py has no cross_block_duplicate, call or comment where the patch puts them",
    "more": "the patched catalog.py changes more than cross_block_duplicate and its call",
    "function": "the patched catalog.py's cross_block_duplicate is not the patch's",
}


def catalogue_texts() -> tuple[str, str]:
    """villa main's catalog.py and the patched one, as far as the patch shows them: its hunks' lines, in order."""
    main: list[str] = []
    patched: list[str] = []
    current = None
    for text in xd.PATCH.read_text().splitlines():
        if text.startswith("diff --git"):
            current = text.rsplit("/", 1)[1]
        elif current != CATALOG_NAME or text.startswith(("+++", "---", "index ")):
            continue
        elif text.startswith("@@"):
            main.append("# ...")
            patched.append("# ...")
        else:
            if not text.startswith("+"):
                main.append(text[1:])
            if not text.startswith("-"):
                patched.append(text[1:])
    return "\n".join(main) + "\n", "\n".join(patched) + "\n"


@pytest.fixture
def villa_main(tmp_path):
    """A stand-in villa clone whose commit REV holds villa main's catalog.py; a later commit changes it."""
    villa = tmp_path / "villa"
    target = villa / xd.CATALOG
    target.parent.mkdir(parents=True)
    main, patched = catalogue_texts()
    git = ["git", "-C", str(villa), "-c", "user.name=t", "-c", "user.email=t@t"]
    subprocess.run(["git", "init", "-q", str(villa)], check=True)
    for text in (main, main + "# a later commit\n"):
        target.write_text(text)
        subprocess.run([*git, "add", "."], check=True)
        subprocess.run([*git, "commit", "-qm", "m"], check=True)
    rev = subprocess.run([*git, "rev-parse", "HEAD~1"], capture_output=True, check=True, text=True).stdout.strip()  # fmt: skip
    return villa, rev, patched


def test_the_catalogue_gate_on_a_stand_in_villa_accepts_the_patch_and_names_what_else_changed(
    tmp_path, villa_main
):
    """`catalog_problems` without the owner's villa clone (the test above needs it): gate check 2."""
    villa, rev, patched = villa_main
    p = tmp_path / CATALOG_NAME

    def problems(text: str) -> list[str]:
        p.write_text(text)
        return xd.catalog_problems(villa, rev, p)

    assert xd.CALL in patched and xd.COMMENT[0] in patched
    assert problems(patched) == []  # against REV, not the clone's HEAD
    other = patched.replace("CREATE TABLE IF NOT EXISTS meta", "CREATE TABLE meta")
    assert other != patched and problems(other) == [GATE["more"]]
    looser = patched.replace("match['contained'] == 'B'", "match['contained'] == 'A'")
    assert looser != patched and problems(looser) == [GATE["function"]]
    assert problems(patched.replace(xd.CALL, "")) == [GATE["missing"]]
    assert problems(patched.replace(xd.CALL, xd.CALL * 2)) == [GATE["missing"]]
    # villa main's comment left as it was
    assert problems(patched.replace(*xd.COMMENT)) == [GATE["missing"]]
    assert problems(catalogue_texts()[0]) == [GATE["missing"]]


def line(a, b):
    return np.array([a, b], float)


def scan(side: int) -> np.ndarray:
    return np.random.default_rng(4).integers(0, 256, (side,) * 3).astype(np.uint8)


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def watched():
    return types.SimpleNamespace(trim=[], blocks=[], black=[], fed=[], catalogs=[], cleaned=[], thresholds=[],
                                 gates=[])  # fmt: skip


# What the patch does, in a stand-in for the patched catalog.py: of two blocks' copies of a fiber, the first is kept.
PATCHED_CATALOG = """import numpy as np

from . import overlap as ov


class Catalog:
    @staticmethod
    def keep(fibers):
        kept = []
        for f in fibers:
            if not any(
                g["family"] == f["family"]
                and g["block"] != f["block"]
                and np.linalg.norm(g["points"][:, None] - f["points"][None], axis=2).min() <= ov.MAX_P90
                for g in kept
            ):
                kept.append(f)
        return kept
"""


def stand_ins(tmp_path, monkeypatch, seen, margin, ct, fibers_xyz, fail):
    """Stand-ins for zarr, ScrollGT and the #1934 head's generator, recording into SEEN. FIBERS_XYZ gives, per block
    index, the block's crop origin and its splines as (family, absolute x, y, z points); a block's field holds its
    index. FAIL names gate checks to break. Returns the stitch.py and catalog.py to pass, and the stitch module."""
    stitch_file, catalog_file = tmp_path / "stitch_patched", tmp_path / f"patched_{CATALOG_NAME}"  # fmt: skip
    stitch_file.write_text("# the amended stitch.py\n")
    catalog_file.write_text(PATCHED_CATALOG)

    def trim(traces, low, high, reach_low, reach_high):
        seen.trim.append([tuple(int(v) for v in x) for x in (low, high, reach_low, reach_high)])  # fmt: skip
        return list(traces)

    def catalog_problems(*a):
        seen.gates.append(a)
        return ["the catalogue differs"] if "catalog" in fail else []

    monkeypatch.setattr(bs, "load", lambda pr, patched: (trim, 16.0))
    monkeypatch.setattr(bs, "identity", lambda *a: ["a module differs"] if "identity" in fail else [])  # fmt: skip
    monkeypatch.setattr(xd, "catalog_problems", catalog_problems)

    class MainCatalog:
        keep = staticmethod(list)

    stitch = types.SimpleNamespace(Catalog=MainCatalog)

    class Stitcher:
        def __init__(self, scratch):
            # as villa's Stitcher: its module's own name, read when a Stitcher is built
            self.catalog, self.fibers = stitch.Catalog, []
            seen.catalogs.append("main" if self.catalog is MainCatalog else "patched")

        def add_block(self, name, low_xyz, size_xyz, traces, core):
            seen.blocks.append((name, low_xyz, size_xyz, [[int(v) for v in c] for c in core]))  # fmt: skip
            self.fibers += [{"points": q[:, ::-1] + low_xyz, "family": "VH".index(f), "block": name}
                            for f, q in traces]  # fmt: skip

        def stitched(self):
            return self.catalog.keep(self.fibers)

        def close(self):
            pass

    stitch.Stitcher = Stitcher

    class ExteriorBlack:
        def __init__(self, low, high):
            seen.black.append((tuple(int(v) for v in low), tuple(int(v) for v in high)))

        def add(self, block, low):
            seen.fed.append((np.array(block), tuple(int(v) for v in low)))

    def clean(traces, max_join_angle, min_length, black, black_distance):
        seen.cleaned.append((max_join_angle, min_length, type(black).__name__, black_distance))  # fmt: skip
        return traces

    def extract_splines(field, threshold):
        seen.thresholds.append(threshold)
        low, splines = fibers_xyz.get(int(field.flat[0]), ((0, 0, 0), []))
        return [(f, (q - low)[:, ::-1]) for f, q in splines]

    def score_tracing(skel, labels, tolerance):
        assert skel == "skeleton"
        row = {"erl_merge_penalized": float(np.count_nonzero(labels)), "merges": int(labels.max()),
               "tolerance": tolerance}  # fmt: skip
        return types.SimpleNamespace(as_row=lambda: row)

    def zone_blocks(
        origin, size, block
    ):  # the #1934 head's, as finding 107's smoke copies it
        axes = [[(o + a, min(block, n - a)) for a in range(0, n, block)] for o, n in zip(origin, size, strict=True)]  # fmt: skip
        return [([x, y, z], [sx, sy, sz]) for z, sz in axes[2] for y, sy in axes[1] for x, sx in axes[0]]  # fmt: skip

    cli = types.SimpleNamespace(zone_blocks=zone_blocks, BLOCK_MARGIN=margin)
    overlap = types.SimpleNamespace(MAX_P90=3.0)
    package = "vesuvius.afv_spline_generator"
    modules = {
        "zarr": types.SimpleNamespace(open=lambda path, mode: ct),
        "scrollgt": types.ModuleType("scrollgt"),
        "scrollgt.fibers": types.ModuleType("scrollgt.fibers"),
        "scrollgt.fibers.eval_trace": types.SimpleNamespace(score_tracing=score_tracing),
        "scrollgt.fibers.target": types.SimpleNamespace(load_fiber_target=lambda path: ("skeleton", None, None)),
        "vesuvius": types.ModuleType("vesuvius"),
        package: types.SimpleNamespace(cli=cli),
        f"{package}.cli": cli,
        f"{package}.cleanup": types.SimpleNamespace(ExteriorBlack=ExteriorBlack, clean=clean),
        f"{package}.splines": types.SimpleNamespace(extract_splines=extract_splines, threshold_to_u8=lambda t: t),
        f"{package}.extend": types.SimpleNamespace(stitch=stitch, overlap=overlap),
        f"{package}.extend.stitch": stitch,
        f"{package}.extend.overlap": overlap,
        f"{package}.extend.catalog": types.SimpleNamespace(Catalog=MainCatalog),
    }  # fmt: skip
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    return stitch_file, catalog_file, stitch


def tolerance_rows(voxels: int, instances: int) -> dict:
    return {f"tol{t}": {"erl_merge_penalized": float(voxels), "merges": instances, "tolerance": float(t)}
            for t in (2, 4)}  # fmt: skip


# run() on a 16³ stand-in cube: 8 blocks of 8 read with a margin of 2, so block 0 reads x in [0, 10) and block 1
# x in [6, 16). Both fit one H fiber, 0.5 voxel apart in y; block 0 also fits a V fiber. The cube run as one block
# has the H fiber alone, from x 2 to 14: it crosses the face x = 8 once.
CUBE = "tiny_16"
RUN_FIBERS = {
    0: ((0, 0, 0), [("H", line([2, 4, 4], [9, 4, 4])), ("V", line([2, 8, 2], [8, 8, 2]))]),
    1: ((6, 0, 0), [("H", line([7, 4.5, 4], [14, 4.5, 4]))]),
}  # fmt: skip
RUN_ROWS = {
    # 15 samples of each copy, 7 within 1.5 voxels of the other; the V fiber's 13 beside nothing: 14 of 43
    "trim": tolerance_rows(20, 3) | {"written": 3, "length": 20.0, "duplicated_share": 0.3256,
                                     "crossings": {"whole": 0, "broken": 1, "lost": 0}},
    "trim+dup": tolerance_rows(15, 2) | {"written": 2, "length": 13.0, "duplicated_share": 0.0,
                                         "crossings": {"whole": 0, "broken": 1, "lost": 0}},
}  # fmt: skip
GATE_106 = (
    "finding 106's record of this cube has identity problems or another model revision"
)


def run_small(tmp_path, monkeypatch, seen, variants=xd.VARIANTS, fail=()):
    """xd.run on the stand-in cube; FAIL names gate checks to break. The cube's result, or None if none is written."""
    monkeypatch.setattr(bs, "CROSSING_WINDOW", 5.0)
    files = stand_ins(tmp_path, monkeypatch, seen, 2, scan(16), RUN_FIBERS, fail)
    fields = tmp_path / "fields" / CUBE
    fields.mkdir(parents=True)
    for i in range(8):
        np.save(fields / f"prob_real_{i}.npy", np.full((2, 2, 2), i, np.uint8))
    np.savez(fields / "one_main_fibers.npz", points=line([2, 4, 4], [14, 4, 4]), offsets=np.array([0, 2]),
             family=np.array([1]))  # fmt: skip
    arms = xd.VARIANTS[::-1] if "row" in fail else xd.VARIANTS
    f106 = {
        "identity_problems": ["a module differs"] if "f106 identity" in fail else [],
        "settings": {"revision": "0" * 40 if "f106 revision" in fail else bs.REVISION},
        "rows": {"real/patched": RUN_ROWS[arms[0]], "real/main": RUN_ROWS[arms[1]]},
    }
    (tmp_path / "f106.json").write_text(json.dumps({"cubes": {CUBE: f106}}))
    monkeypatch.setattr(xd, "RECORD_106", tmp_path / "f106.json")
    args = types.SimpleNamespace(cube=CUBE, fields=tmp_path / "fields", work=tmp_path / "work", pr=tmp_path,
                                 villa=tmp_path / "villa", main="7e6b82164", patched_stitch=files[0],
                                 patched_catalog=files[1], variants=tuple(variants))  # fmt: skip
    xd.run(args)
    assert (
        files[2].Catalog.__name__ == "MainCatalog"
    )  # the module's own catalogue is put back
    out = args.work / f"{CUBE}.json"
    return json.loads(out.read_text()) if out.exists() else None


def test_the_run_stitches_a_cube_from_its_cached_fields_with_the_trim_and_with_the_change(
    tmp_path, monkeypatch
):
    """The registration's two arms: both trimmed with the read box the cube, `trim+dup` alone with the patched
    catalogue; each block from its own field, scored as finding 106 scored."""
    seen = watched()
    out = run_small(tmp_path, monkeypatch, seen)
    assert out["identity_problems"] == [] and out["rows"] == RUN_ROWS
    assert (out["cube"], out["size"], out["block"], out["cut_end"]) == (
        CUBE,
        16,
        8,
        16.0,
    )
    stitch_file, catalog_file = tmp_path / "stitch_patched", tmp_path / f"patched_{CATALOG_NAME}"  # fmt: skip
    assert out["patched_stitch_sha256"] == digest(stitch_file) != digest(catalog_file)
    assert out["patched_catalog_sha256"] == digest(catalog_file)
    assert out["villa_main"] == "7e6b82164"
    assert seen.gates == [(tmp_path / "villa", "7e6b82164", catalog_file)]
    assert seen.catalogs == ["main", "patched"]  # trim, then trim+dup
    # every block of both arms is trimmed, the read box the whole cube; block 1's crop is z, y, x
    assert len(seen.trim) == 16
    assert all(t[2:] == [(0, 0, 0), (16, 16, 16)] for t in seen.trim)
    assert seen.trim[1][:2] == [(0, 0, 6), (10, 10, 16)]
    assert seen.blocks[1] == (
        "block-1",
        [6, 0, 0],
        [10, 10, 10],
        [[8, 0, 0], [16, 8, 8]],
    )
    assert seen.black == [((0, 0, 0), (16, 16, 16))] * 2 and len(seen.fed) == 16
    assert seen.fed[1][1] == (6, 0, 0)
    assert np.array_equal(seen.fed[1][0], scan(16)[0:10, 0:10, 6:16])
    assert seen.thresholds == [60.0] * 16
    assert seen.cleaned == [(45.0, 100.0, "ExteriorBlack", 16.0)] * 2


@pytest.mark.parametrize(
    "fail, problem",
    [
        ("identity", "a module differs"),
        ("catalog", "the catalogue differs"),
        ("f106 identity", GATE_106),
        ("f106 revision", GATE_106),
        ("row", "the trim arm does not reproduce finding 106's real/patched row"),
    ],
)
def test_a_cube_s_failed_gate_check_is_recorded_and_means_no_verdict(
    tmp_path, monkeypatch, fail, problem
):
    """The registration's four gate checks, per cube: a failure is written with the cube's result."""
    out = run_small(tmp_path, monkeypatch, watched(), fail=(fail,))
    assert out["identity_problems"] == [problem]
    r = results([0.05] * 8)
    assert xd.verdict(r)["decision"] == "SUPPORTED"
    r[bs.HELD_OUT[2]]["identity_problems"] = out["identity_problems"]
    assert xd.verdict(r)["decision"] == "NO_VERDICT"


# zone() on finding 107's zone shrunk to SIZE 8, ZONE 16, BLOCK 8, MARGIN 2: the scan is 20³, the cube [6, 14) on
# each axis, block 0 reads x in [0, 12) and block 1 x in [8, 20). Both fit one H fiber inside the cube; block 0 also
# fits a V fiber outside it.
SMALL = {"SIZE": 8, "ZONE": 16, "BLOCK": 8, "MARGIN": 2, "PAD": 6, "SIDE": 20}
ZONE_FIBERS = {
    0: ((0, 0, 0), [("H", line([7, 8, 8], [11, 8, 8])), ("V", line([1, 1, 1], [5, 1, 1]))]),
    1: ((8, 0, 0), [("H", line([9, 8.5, 8], [13, 8.5, 8]))]),
}  # fmt: skip
ZONE_ROWS = {
    # 9 samples of each copy, 7 within 1.5 voxels of the other: 14 of the zone's 27 and of the cube's 18
    "trim": {"zone": {"written": 3, "length": 12.0, "duplicated_share": 0.5185},
             "cube": {"written_inside": 2, "duplicated_share": 0.7778} | tolerance_rows(7, 3)},
    "trim+dup": {"zone": {"written": 2, "length": 8.0, "duplicated_share": 0.0},
                 "cube": {"written_inside": 1, "duplicated_share": 0.0} | tolerance_rows(5, 1)},
}  # fmt: skip


def zone_small(tmp_path, monkeypatch, seen, variants=xd.VARIANTS, fail=()):
    """xd.zone on the shrunk zone; FAIL names gate checks to break. The zone's result, or None if none is written."""
    for name, value in SMALL.items():
        monkeypatch.setattr(dz, name, value)
    files = stand_ins(
        tmp_path, monkeypatch, seen, SMALL["MARGIN"], None, ZONE_FIBERS, fail
    )
    zone_work = tmp_path / "zone"
    zone_work.mkdir()
    np.save(zone_work / "context.npy", scan(SMALL["SIDE"]))
    for i in range(8):
        np.save(zone_work / f"prob_block_{i}.npy", np.full((2, 2, 2), i, np.uint8))
    arms = xd.VARIANTS[::-1] if "row" in fail else xd.VARIANTS
    f107 = {
        "context_sha256": "0" * 64
        if "scan" in fail
        else digest(zone_work / "context.npy"),
        "rows": {"patched": ZONE_ROWS[arms[0]], "main": ZONE_ROWS[arms[1]]},
    }
    (tmp_path / "f107.json").write_text(json.dumps({"result": f107}))
    monkeypatch.setattr(xd, "RECORD_107", tmp_path / "f107.json")
    args = types.SimpleNamespace(zone_work=zone_work, work=tmp_path / "work", pr=tmp_path, villa=tmp_path / "villa",
                                 main="7e6b82164", patched_stitch=files[0], patched_catalog=files[1],
                                 variants=tuple(variants))  # fmt: skip
    xd.zone(args)
    assert files[2].Catalog.__name__ == "MainCatalog"
    out = args.work / "zone.json"
    return json.loads(out.read_text()) if out.exists() else None


def test_the_zone_is_stitched_from_finding_107s_fields_with_the_trim_and_with_the_change(
    tmp_path, monkeypatch
):
    seen = watched()
    out = zone_small(tmp_path, monkeypatch, seen)
    assert out["identity_problems"] == [] and out["rows"] == ZONE_ROWS
    assert (out["cube"], out["zone"], out["block"]) == (dz.CUBE, 16, 8)
    assert seen.catalogs == ["main", "patched"]
    # the read box is the zone and its margin, the whole scan; block 1's crop is z, y, x
    assert len(seen.trim) == 16
    assert all(t[2:] == [(0, 0, 0), (20, 20, 20)] for t in seen.trim)
    assert seen.trim[1][:2] == [(0, 0, 8), (12, 12, 20)]
    assert seen.blocks[1] == (
        "block-1",
        [8, 0, 0],
        [12, 12, 12],
        [[10, 2, 2], [18, 10, 10]],
    )
    assert seen.black == [((0, 0, 0), (20, 20, 20))] * 2
    assert np.array_equal(seen.fed[1][0], scan(20)[0:12, 0:12, 8:20])


@pytest.mark.parametrize(
    "fail, problem",
    [
        ("identity", "a module differs"),
        ("catalog", "the catalogue differs"),
        ("scan", "the zone's scan is not finding 107's"),
        ("row", "the trim arm does not reproduce finding 107's patched row"),
    ],
)
def test_the_zone_s_failed_gate_check_is_recorded(tmp_path, monkeypatch, fail, problem):
    out = zone_small(tmp_path, monkeypatch, watched(), fail=(fail,))
    assert out["identity_problems"] == [problem]


@pytest.mark.parametrize("small", [run_small, zone_small])
def test_a_smoke_of_one_arm_writes_no_result(tmp_path, monkeypatch, small):
    """The registration's smoke ran `--variants trim`: it sees nothing of the change and leaves no result behind."""
    seen = watched()
    assert small(tmp_path, monkeypatch, seen, variants=("trim",)) is None
    assert seen.catalogs == ["main"] and not (tmp_path / "work").exists()
