"""The tier table is load-bearing: a misfiled arm silently corrupts a correlation.

These tests exist because that already happened. `anchor10cov` ran on current
villa, `correlate_geometry_ink.py` carried its own prefix tuple that did not
mention it, and the `else "pinned"` default absorbed three current-tier fits into
the pinned tier -- moving r from -0.121 to -0.008 and widening the guard bound
the project reports. Nothing failed; the number just changed.
"""

import re
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

from arm_tiers import TIERS, UnknownArm, classify, tier_of  # noqa: E402


@pytest.mark.parametrize(
    "tag,tier",
    [
        ("baseline01", "pinned"),
        ("seed02", "pinned"),
        ("seed06", "pinned"),
        ("gap133", "pinned"),
        ("gap133s6", "pinned"),
        ("boot090s1", "pinned"),
        ("rand090s3", "pinned"),
        ("nosame_s1", "pinned"),
        ("strip090s2", "pinned"),
        ("curbase_s1", "current"),
        ("curbase_s9", "current"),
        ("nosamecur_s3", "current"),
        ("anchor10cov_pilot", "current"),
        ("anchor10cov_s2", "current"),
        ("anchor10cov_s3", "current"),
    ],
)
def test_known_arms_resolve(tag, tier):
    assert tier_of(tag) == tier


def test_the_regression_anchor10cov_is_current_not_pinned():
    """THE bug. Its registration says 'Current villa, 30,000 steps', and its ink
    (2.72-2.95M) sits with curbase (2.90M), not with pinned baseline01 (1.79M)."""
    for s in ("anchor10cov_pilot", "anchor10cov_s2", "anchor10cov_s3"):
        assert tier_of(s) == "current"


def test_nosame_and_nosamecur_are_not_confused():
    """Adjacent names, opposite tiers -- longest-prefix matching must hold, and
    a plain `startswith('nosame')` rule would put both in pinned."""
    assert tier_of("nosame_s1") == "pinned"
    assert tier_of("nosamecur_s1") == "current"


def test_unknown_arm_raises_rather_than_defaulting():
    """The defect was a silent default, not a wrong prefix."""
    with pytest.raises(UnknownArm):
        tier_of("some_unregistered_arm_s1")


def test_classify_raises_on_any_unknown_member():
    with pytest.raises(UnknownArm):
        classify(["baseline01", "definitely_not_registered"])


def test_noise_floor_groups_agree_with_the_tier_table():
    """The two encodings of the same fact must not diverge again."""
    import measure_noise_floor as nf

    for tier, groups in nf.TIERS.items():
        for group, arms in groups.items():
            for arm in arms:
                assert tier_of(arm) == tier, f"{group}/{arm} disagrees"


def test_correlation_script_uses_the_shared_table():
    """It must not reintroduce a local prefix tuple."""
    import correlate_geometry_ink as cgi

    assert cgi.tier_of is tier_of
    src = (
        Path(__file__).resolve().parents[1] / "scripts" / "correlate_geometry_ink.py"
    ).read_text()
    # Match the ASSIGNMENT, not the word: the file explains in a comment why the
    # old tuple was removed, and a bare substring test flags its own postmortem.
    assert not re.search(r"^\s*CURRENT_TREE_PREFIXES\s*=", src, re.M), (
        "a local tier list came back; tier membership belongs in arm_tiers.py"
    )


def test_every_tier_name_is_known():
    assert set(TIERS) == {"pinned", "current", "upstream"}


def test_upstream_fits_are_their_own_tier():
    """Fitted on 75c79ac5f (2026-09-24); pooling them with `current` before the
    registered comparison would assume its answer."""
    assert tier_of("upfit_s1") == "upstream"


# --- the table against the record of what ran ---------------------------------
# repro/spiral_fits/ holds a copy of each arm's fit driver. A driver exports the
# arm's run tag and runs fit_spiral.py from one villa tree, so it is the
# evidence a human classifying an arm in _RULES is meant to have read.
_DRIVERS = Path(__file__).resolve().parents[1] / "repro" / "spiral_fits"
_SCRIPTS = Path(__file__).resolve().parents[1] / "scripts"
_TREE_TIER = {
    "villa-spiral": "pinned",
    "villa-spiral-current": "current",
    "villa-spiral-upstream": "upstream",
}
# Driver tags deliberately left out of the table (smoke and exploratory runs),
# so any analysis that scores one raises. Held exact: a parsing slip that turns
# a real tag into an unknown one must not pass as "unclassified".
_UNCLASSIFIED = {
    "densespace0", "margin0", "minspace0", "smoke01", "smoke_absw0", "smoke_absw5",
    "smoke_anchor10", "smoke_anchor20", "smoke_anchor35", "smoke_current",
    "smoke_nosamewind",
}  # fmt: skip
# Arms the analyses group by tier whose driver was never copied here. The
# extension's preregistration specifies them as fit_nosamecur_s1.sh with only
# the seed (4, 5, 6) and the tag changed. Vendor them and empty this set.
_NOT_VENDORED = {"nosamecur_s4", "nosamecur_s5", "nosamecur_s6"}


def _drivers() -> dict[str, tuple[str, str]]:
    """{run tag: (driver file, villa tree name)} for every vendored driver that
    sets a tag. A tag built from $SEED (fit_upfit.sh) is kept as a pattern."""
    out: dict[str, tuple[str, str]] = {}
    for f in sorted(_DRIVERS.glob("*.sh")):
        text = f.read_text()
        tags = re.findall(r"^export FIT_SPIRAL_RUN_TAG=(\S+)$", text, re.M)
        if not tags:
            continue
        (tag,) = tags
        env = dict(re.findall(r"^([A-Z_]+)=(\S+)$", text, re.M))
        # every line that decides what runs: the import path, the directory and
        # the interpreter; they must name one tree
        lines = re.findall(r"^(?:export PYTHONPATH=|cd |exec ).*$", text, re.M)
        assert any(ln.startswith("cd ") for ln in lines), f"{f.name}: no cd"
        trees = set()
        for ln in lines:
            ln = re.sub(
                r"\$\{?(\w+)\}?", lambda m, env=env: env.get(m.group(1), m.group(0)), ln
            )
            trees |= set(re.findall(r"/(villa-spiral[\w-]*)(?:/|\s|$)", ln))
        assert len(trees) == 1, f"{f.name}: runs from {sorted(trees)}"
        assert tag not in out, f"{tag} is set by both {out[tag][0]} and {f.name}"
        out[tag] = (f.name, trees.pop())
    return out


def _covers(template: str, tag: str) -> bool:
    return re.fullmatch(re.escape(template).replace(r"\$SEED", r"\d+"), tag) is not None


def test_the_table_agrees_with_the_tree_each_vendored_driver_fits_with():
    drivers = _drivers()
    unclassified = set()
    for tag, (name, tree) in drivers.items():
        try:
            tier = tier_of(tag.replace("$SEED", "1"))
        except UnknownArm:
            unclassified.add(tag)
            continue
        assert _TREE_TIER[tree] == tier, (
            f"{name} ({tag}) runs from {tree}, table says {tier}"
        )
    assert unclassified == _UNCLASSIFIED, sorted(unclassified ^ _UNCLASSIFIED)


def test_every_rule_in_the_table_has_a_vendored_driver():
    import arm_tiers

    tags = [t.replace("$SEED", "1") for t in _drivers()]
    for prefix, tier in arm_tiers._RULES:
        backing = [t for t in tags if t.startswith(prefix) and tier_of(t) == tier]
        assert backing, f"rule {prefix!r} -> {tier} has no vendored driver"


def _assigned(module: str, name: str):
    """The value assigned to `name` in scripts/<module>.py, evaluated with only
    tuple, list and range, without importing the script: some of these scripts
    import packages that live only on the owner's machine."""
    import ast

    tree = ast.parse((_SCRIPTS / f"{module}.py").read_text())
    for node in tree.body:
        targets = (
            node.targets
            if isinstance(node, ast.Assign)
            else [getattr(node, "target", None)]
        )
        if any(isinstance(t, ast.Name) and t.id == name for t in targets):
            code = compile(ast.Expression(node.value), f"{module}.{name}", "eval")
            return eval(
                code, {"__builtins__": {"tuple": tuple, "list": list, "range": range}}
            )
    raise AssertionError(f"{module}.{name} not found")


def _tier_groups() -> list[tuple[str, str, set[str]]]:
    """Every arm group a script declares by tier: (where, tier, arms)."""
    import measure_noise_floor as nf
    import soft_count_study as sc

    out = [
        (f"measure_noise_floor/{g}", t, set(a))
        for t, gs in nf.TIERS.items()
        for g, a in gs.items()
    ]
    out += [(f"soft_count_study/{g}", t, set(a))
            for t, gs in (("pinned", sc.PINNED), ("current", sc.CURRENT)) for g, a in gs.items()]  # fmt: skip
    studies = _assigned("survey_manipulation_effects", "STUDIES")
    out += [
        (f"survey_manipulation_effects/{k}", t, set(c) | set(x))
        for k, (c, x, t) in studies.items()
    ]
    layouts = _assigned("seed_as_shared_nuisance", "LAYOUTS")
    out += [(f"seed_as_shared_nuisance/{g}", k.split()[0].rstrip(","), set(a))
            for k, gs in layouts.items() for g, a in gs.items()]  # fmt: skip
    arms = _assigned("analyse_spiralcheck_pinned_replication", "ARMS")
    assert len(arms) == 24  # its DF is len(ARMS) - 6 - 1 = 17
    out.append(("analyse_spiralcheck_pinned_replication/ARMS", "pinned", set(arms)))
    return out


def test_every_tier_group_a_script_declares_agrees_with_the_table():
    """These are other encodings of the same fact; each must say what the table says."""
    groups = _tier_groups()
    assert {where.split("/")[0] for where, _, _ in groups} == {
        "measure_noise_floor", "soft_count_study", "survey_manipulation_effects",
        "seed_as_shared_nuisance", "analyse_spiralcheck_pinned_replication",
    }  # fmt: skip
    for where, tier, arms in groups:
        assert tier in TIERS, f"{where}: {tier!r}"
        for arm in arms:
            assert tier_of(arm) == tier, f"{where}/{arm}: table says {tier_of(arm)}"


def test_every_grouped_arm_has_a_vendored_driver_or_is_a_recorded_gap():
    drivers = list(_drivers())
    grouped = set().union(*(arms for _, _, arms in _tier_groups()))
    missing = {a for a in grouped if not any(_covers(d, a) for d in drivers)}
    assert missing == _NOT_VENDORED, sorted(missing ^ _NOT_VENDORED)
    readme = (_DRIVERS / "README.md").read_text()
    for arm in sorted(_NOT_VENDORED):
        assert f"`{arm}`" in readme, f"{arm} is not listed as unvendored in the README"


def test_a_seeded_driver_covers_its_seeds():
    assert _covers("upfit_s$SEED", "upfit_s3") and not _covers(
        "upfit_s$SEED", "upfit_s"
    )
    assert not _covers("curbase_s1", "curbase_s10")
