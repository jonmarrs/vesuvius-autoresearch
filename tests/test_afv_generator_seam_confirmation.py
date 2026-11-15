"""scripts/afv_generator_seam_confirmation.py (finding 109's run): its cubes and their hashes, the registered decision
rule, the block layout, the runner, the smoke's evidence, and the registration's figures from their records."""

from __future__ import annotations

import json
import re
import statistics
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import afv_generator_block_seams as bs  # noqa: E402
import afv_generator_seam_confirmation as sc  # noqa: E402
import seed_heading_confirmation as shc  # noqa: E402

ROOT = sc.ROOT
REGISTRATION = (
    ROOT / "docs/preregistration/2026-11-09_afv_generator_seam_confirmation.md"
)
REGISTRATION_106 = ROOT / "docs/preregistration/2026-11-06_afv_generator_block_seams.md"
SMOKE = ROOT / "reports/evidence/afv_generator_seam_confirmation_smoke_2026-11-09.json"
DEV_108 = (
    ROOT / "reports/evidence/afv_generator_cross_block_duplicates_dev_2026-11-09.json"
)
RUNNER = ROOT / "repro/fibers/run_afv_generator_seam_confirmation.sh"


def flat(path: Path) -> str:
    return " ".join(path.read_text().split())


def pct(x: float) -> str:
    return f"{100 * x:+.1f}%"


def test_the_cubes_and_their_files_are_finding_103s_registered_ones():
    assert sc.CUBES == shc.CUBES and sc.DATA_SHA256 == shc.DATA_SHA256
    assert sc.BASE_MODEL_UNSEEN == shc.PRESENCE_HELD_OUT
    assert not set(sc.CUBES) & set(bs.HELD_OUT) and sc.SMOKE in bs.HELD_OUT
    sizes = [sc.size_of(c) for c in sc.CUBES]
    assert sizes.count(512) == 4 and sizes.count(256) == 6
    assert sum(c.startswith("s1_") for c in sc.CUBES) == 3


def test_a_file_that_is_not_the_registered_one_is_refused(tmp_path):
    p = tmp_path / "x.nml"
    p.write_text("not the NML")
    try:
        sc.registered(sc.CUBES[0], p, "nml")
    except SystemExit as e:
        assert "is not the registered nml" in str(e)
    else:
        raise AssertionError("an unregistered file was accepted")


def row(erl4: float, merges: int, dup: float) -> dict:
    return {
        "tol2": {"erl_merge_penalized": 10.0, "merges": merges},
        "tol4": {"erl_merge_penalized": erl4, "merges": merges},
        "duplicated_share": dup,
    }


def results(
    both=0.2,
    over_trim=0.05,
    merges=(10, 10),
    dups=(0.2, 0.05),
    problems=(),
    n_up=10,
    n_over=10,
):
    out = {}
    for i, c in enumerate(sc.CUBES):
        b = both if i < n_up else -0.01
        t = 30.0 * (1 + b) / (1 + (over_trim if i < n_over else -0.01))
        out[c] = {
            "identity_problems": list(problems),
            "rows": {"real/main": row(30.0, merges[0], dups[0]), "real/trim": row(t, merges[0], dups[0]),
                     "real/trim+dup": row(30.0 * (1 + b), merges[1], dups[1])},
        }  # fmt: skip
    return out


def test_the_decision_rule():
    d = lambda **k: sc.verdict(results(**k))["decision"]  # noqa: E731
    assert d() == "CONFIRMED"
    assert d(n_up=7) == "NOT_CONFIRMED" and d(n_up=8) == "CONFIRMED"  # P1: 8 of 10
    assert (
        d(merges=(20, 22)) == "NOT_CONFIRMED" and d(merges=(20, 21)) == "CONFIRMED"
    )  # P3: 1.05 x
    assert d(n_over=6) == "TRIM_ONLY" and d(n_over=7) == "CONFIRMED"  # P4: 7 of 10
    assert d(both=0.09) == "PARTIAL" and d(both=0.10) == "CONFIRMED"  # P2: median 0.10
    assert (
        d(dups=(0.2, 0.11)) == "PARTIAL" and d(dups=(0.2, 0.1)) == "CONFIRMED"
    )  # P5: 0.5 x
    # the rows apply in the table's order
    assert d(n_up=7, n_over=6, both=0.09) == "NOT_CONFIRMED"
    assert d(n_over=6, both=0.09) == "TRIM_ONLY"
    assert d(problems=["x"]) == "NO_VERDICT"
    r = results()
    del r[sc.CUBES[0]]
    assert sc.verdict(r)["decision"] == "NO_VERDICT"
    v = sc.verdict(results())
    assert v["P3_merges_tol2"] == [[100, 100], True] and v["P1_both_tol4_up"] == [
        10,
        True,
    ]


def test_the_registration_is_the_rule_and_names_its_inputs():
    t = flat(REGISTRATION)
    for rel in re.findall(
        r"`((?:scripts|docs|reports|repro|tests)/[^`]+)`", REGISTRATION.read_text()
    ):
        assert (ROOT / rel).exists(), rel
    assert (
        f"at least {sc.P1_UP} of 10 cubes" in t
        and f"at least {sc.P4_UP} of 10 cubes" in t
    )
    assert (
        f"at least {sc.P2_GAIN:.2f}" in t
        and f"at most {sc.P3_MERGES} times main's" in t
    )
    assert f"at most {sc.P5_DUP} times main's" in t
    for name in ("NO_VERDICT", "NOT_CONFIRMED", "TRIM_ONLY", "PARTIAL", "CONFIRMED"):
        assert f"`{name}`" in t
    assert "`BASE_MODEL_UNSEEN`" in t and f"`{sc.SMOKE}`" in t


def test_the_registration_s_earlier_figures_are_their_records():
    t = flat(REGISTRATION)
    d106 = json.loads(sc.RECORD_106.read_text())
    d108 = json.loads(sc.RECORD_108.read_text())
    g106 = [bs.gain(d106["cubes"][c]["rows"], "real", "tol4") for c in bs.HELD_OUT]
    assert f"by a median {pct(statistics.median(g106))} at τ = 4" in t
    assert (
        d108["verdict"]["P1_tol4_up"][0] == 8
        and f"{pct(d108['verdict']['P2_median_gain_tol4'][0])} more at τ = 4, on all eight"
        in t
    )
    both = [d108["cubes"][c]["rows"]["trim+dup"]["tol4"]["erl_merge_penalized"]
            / d106["cubes"][c]["rows"]["real/main"]["tol4"]["erl_merge_penalized"] - 1 for c in bs.HELD_OUT]  # fmt: skip
    main = sum(
        d106["cubes"][c]["rows"]["real/main"]["tol2"]["merges"] for c in bs.HELD_OUT
    )
    assert (
        f"{pct(statistics.median(both))} over main at τ = 4, with merges at τ = 2 {main} → {d108['verdict']['P3_merges_tol2'][0][1]}"
        in t
    )
    assert f"On Scroll 3 it was {statistics.median(both):.3f}" in t
    # finding 106's dev screen, as its registration states it
    assert "16 +0.183 / +0.386" in flat(REGISTRATION_106) and "+38.6%, on 8 of 8" in t
    rows = json.loads(DEV_108.read_text())["dev_screen"]["rows"].values()
    g = [
        r["E16P"]["tol4_erl_merge_penalized"] / r["E16"]["tol4_erl_merge_penalized"] - 1
        for r in rows
    ]
    assert f"{pct(statistics.median(g))}, on 8 of 8" in t and all(x > 0 for x in g)


def test_the_blocks_are_read_as_cli_generate_reads_them():
    def zone_blocks(origin, shape, block):
        return [((x, y, z), (block,) * 3) for z in range(0, shape[2], block) for y in range(0, shape[1], block)
                for x in range(0, shape[0], block)]  # fmt: skip

    cli = SimpleNamespace(BLOCK_MARGIN=32, zone_blocks=zone_blocks)
    ct = np.zeros((256,) * 3, np.uint8)
    seen: list[tuple] = []

    def field_of(arm: str, i: int, sl) -> int:
        seen.append((arm, i, sl))
        return i

    blocks = sc.blocks_of(cli, "real", ct, field_of)
    assert len(blocks) == 8
    lows = {tuple(int(v) for v in b[0]) for b in blocks}
    highs = {tuple(int(v) for v in b[1]) for b in blocks}
    assert lows == {(x, y, z) for x in (0, 96) for y in (0, 96) for z in (0, 96)}
    assert highs == {
        (x, y, z) for x in (160, 256) for y in (160, 256) for z in (160, 256)
    }
    assert [b[5]() for b in blocks] == list(range(8)) and all(
        b[4].shape == (160,) * 3 for b in blocks
    )
    (one,) = sc.blocks_of(cli, "one", ct, lambda arm, i, sl: (arm, sl))
    assert one[5]() == ("one", (slice(0, 256),) * 3) and one[4].shape == ct.shape
    assert sc.untrimmed([1, 2], 3, 4) == [1, 2]


def test_the_runner_parses_and_writes_the_record_once():
    subprocess.run(["bash", "-n", str(RUNNER)], check=True)
    text = RUNNER.read_text()
    assert (
        "reports/afv_generator_seam_confirmation.json" in text
        and "key=sc.size_of" in text
    )
    assert (
        "--patched-catalog" in text and 'if [ ! -f "$WORK/$CUBE/result.json" ]' in text
    )


def test_the_smoke_reproduced_findings_106_and_108():
    s = json.loads(SMOKE.read_text())
    assert s["cube"] == sc.SMOKE and s["identity_problems"] == []
    assert s["reproduces"] == {
        "one/main": True,
        "real/main": True,
        "real/trim": True,
        "real/trim+dup": True,
    }
    f106 = json.loads(sc.RECORD_106.read_text())["cubes"][sc.SMOKE]["rows"]
    f108 = json.loads(sc.RECORD_108.read_text())["cubes"][sc.SMOKE]["rows"]
    r = s["rows"]
    assert r["one/main"] == f106["one/main"] and r["real/main"] == f106["real/main"]
    assert (
        r["real/trim"] == f106["real/patched"]
        and r["real/trim+dup"] == f108["trim+dup"]
    )
