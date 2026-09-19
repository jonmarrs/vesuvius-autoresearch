"""Which code tier each fit belongs to. ONE definition, imported by everything.

Fits come in two **non-comparable** tiers: pinned villa-spiral `6847063f` and
current villa. Current recovers ~67.6% more ink through a byte-identical scorer
(`reports/corpus_is_on_superseded_code.md`), so mixing them manufactures a spread
that is the code change rather than a relationship.

**This module exists because the knowledge was duplicated and drifted.**
`correlate_geometry_ink.py` carried `CURRENT_TREE_PREFIXES = ("curbase_",
"nosamecur_")` while `measure_noise_floor.py` carried explicit groups that listed
`anchor10cov` under CURRENT. When the anchor study ran, nobody updated the prefix
tuple, so `tier_of("anchor10cov_s3")` returned "pinned" and three current-tier
fits were pooled into the pinned correlation -- stretching its ink range from
1.45-1.83M to 1.45-2.95M and moving r from -0.121 to -0.008.

The script's own comment had recorded the identical failure once before: "Before
this split the script silently reported 27 fits ... an artefact." It was back at
27 fits. A defect that recurs after being fixed is a defect in the STRUCTURE, so
the fix is structural: one table, and no silent default.

**Unknown arms raise.** The original bug was not a wrong prefix, it was an
unrecognised arm quietly inheriting a tier. A new arm must be classified here, by
a human who knows which tree it ran on, before any analysis will score it. That
is deliberately a small chore in exchange for making this class of error loud.
"""

# Prefix -> tier. Longest match wins, so a specific arm can override a family.
# Every entry needs a reason a reader can check, because the cost of a wrong
# entry is a silently corrupted correlation, not a crash.
_RULES: tuple[tuple[str, str], ...] = (
    # --- pinned villa-spiral 6847063f -------------------------------------
    ("baseline01", "pinned"),  # the six original baselines
    ("seed0", "pinned"),
    ("gap133", "pinned"),  # gap-expander arms, all pinned
    ("boot090", "pinned"),  # patch bootstrap, pinned per its registration
    ("rand090", "pinned"),  # its area-matched control
    ("strip090", "pinned"),  # stripmatch follow-up
    ("nosame_", "pinned"),  # same-winding ablation, pinned
    # --- current villa ----------------------------------------------------
    ("curbase_", "current"),  # current-code baselines, s1..s9
    ("nosamecur_", "current"),  # same-winding ablation repeated on current
    # docs/preregistration/2026-09-12_anchor_ablation.md: "Current villa,
    # 30,000 steps". THIS is the entry whose absence caused the drift.
    ("anchor10cov", "current"),
)

TIERS = ("pinned", "current")


class UnknownArm(KeyError):
    """Raised for an arm no rule claims. Classify it in _RULES, do not guess."""


def tier_of(tag: str) -> str:
    """Tier for `tag`, or raise. There is deliberately NO default."""
    best, best_tier = "", None
    for prefix, tier in _RULES:
        if tag.startswith(prefix) and len(prefix) > len(best):
            best, best_tier = prefix, tier
    if best_tier is None:
        raise UnknownArm(
            f"arm {tag!r} is not classified into a code tier. Add it to "
            f"scripts/arm_tiers.py:_RULES with the tree it ran on -- do NOT let "
            f"it default, which is the bug this module exists to prevent."
        )
    return best_tier


def classify(tags):
    """Split an iterable of tags into {tier: [tags]}, raising on any unknown."""
    out: dict[str, list[str]] = {t: [] for t in TIERS}
    for t in tags:
        out[tier_of(t)].append(t)
    return out
