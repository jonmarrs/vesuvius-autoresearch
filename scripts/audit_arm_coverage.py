"""Which scored arms on disk does no analysis actually use?

**Two corrections in one day came from the same root cause**, and neither was
caught by a failing test -- the numbers simply changed when someone looked:

* `anchor10cov` ran on current villa, a local prefix list did not mention it, and
  three fits were silently filed into the pinned tier
  (`reports/geometry_ink_correlation_corpus.md`, amended).
* `curbase_s4..s9` sat on disk for six days while the noise floor was estimated
  from `s1..s3`, quoting a CV half the real one
  (`reports/six_unused_seeds_double_the_current_floor.md`).

Before those, a survey that listed only `outer_*` missed 16 of 56 arms, and the
missing ones held both halves of an answer then being chased by hand.

The shared shape is **data on disk exceeding what the analysis used, silently**.
A test cannot catch it, because nothing is wrong with the code -- the sample is
just smaller than it could be. So this reports rather than asserts, and is meant
to be READ when starting a study, and run in CI to keep the orphan list honest.

Two failure directions, both worth knowing:

* **ORPHAN** -- scored, on disk, named by no analysis script. Either it is a
  deliberate one-off (a determinism repeat, a probe) or it is a replicate someone
  forgot. The audit cannot tell those apart; a human must, which is the point.
* **PHANTOM** -- named by a script but absent from disk. A typo, or an arm that
  was deleted; either way an analysis is silently running on fewer fits than its
  author believes, exactly as `measure_noise_floor.py`'s `if t in D` did.

Usage:  audit_arm_coverage.py [--spiral-out DIR] [--json OUT] [--fail-on-phantom]
"""

import argparse
import ast
import glob
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
# Where an arm may legitimately be claimed. Reports count: an arm discussed in a
# report is accounted for even if no script hardcodes it.
SEARCH_GLOBS = ("scripts/*.py", "docs/preregistration/*.md", "reports/*.md")
SELF = Path(__file__).name

# Families that are one-offs BY CONSTRUCTION, not forgotten replicates. Each needs
# a reason, because this list is how a real orphan gets hidden.
EXPECTED_ONE_OFF = {
    "dup_": "duplicate-coverage study arms, scored once by design",
    "probe_": "one-shot probes, not replicates",
    "render_": "render-only repeats sharing another arm's meshes",
    "seedarm_": "knob probes on existing meshes, no fit of their own",
    "curbase_s1rr": "a rerender of curbase_s1; no fit, so no satisfaction",
}


ARM_TAG = re.compile(
    r"^(?:baseline01|seed0[2-6]|gap133(?:s[2-6])?|boot090s[1-3]|rand090s[1-3]"
    r"|strip090s[1-3]|nosame_s[1-3]|nosamecur_s[1-3]|curbase_s\d+(?:rr)?"
    r"|anchor10cov_(?:pilot|s\d+))$"
)


def arm_tags_in_code(source: str) -> set[str]:
    """Arm tags appearing as real string CONSTANTS in Python source.

    Parsed from the AST, never grepped. The grep version produced 18 hits and
    every one was a false positive: group labels ("curbase_d8c5f488a"), bare
    prefixes ("nosame_"), locals ("seed_area_cv"), and -- the instructive case --
    `anchor10cov_s1`, which appears ONLY inside comments explaining why that arm
    deliberately does not exist. A guard that is wrong 18 times out of 18 is one
    people learn to ignore, which is how the blind spot it checks for survived.

    So: string constants only, module/function/class docstrings excluded, and the
    literal must look like a COMPLETE arm tag rather than a family or a prefix.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return set()
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(
            node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)
        ):
            d = ast.get_docstring(node, clean=False)
            if d is not None:
                docstrings.add(d)
    return {
        n.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Constant)
        and isinstance(n.value, str)
        and n.value not in docstrings
        and ARM_TAG.match(n.value)
    }


def arms_on_disk(spiral_out: str) -> list[str]:
    out = []
    for p in glob.glob(f"{spiral_out}/*/ink_metric/metrics.json"):
        out.append(Path(p).parent.parent.name)
    return sorted(set(out))


def tag_of(arm: str) -> str:
    """Directory name -> the tag analyses refer to (`outer_` is a dir convention)."""
    return arm[len("outer_") :] if arm.startswith("outer_") else arm


def searchable_files() -> dict[Path, str]:
    """Every file an arm may legitimately be claimed in, -> its text.

    This module is skipped: it names arms in its own docstring, and counting that
    as a reference would let it excuse every orphan it is supposed to report.
    """
    files = [f for g in SEARCH_GLOBS for f in REPO.glob(g) if f.name != SELF]
    return {f: f.read_text(errors="ignore") for f in files}


def audit(spiral_out: str) -> dict:
    disk = arms_on_disk(spiral_out)
    tags = {tag_of(a): a for a in disk}
    texts = searchable_files()

    named: dict[str, list[str]] = {t: [] for t in tags}
    for f, txt in texts.items():
        for t in tags:
            # word-ish boundary so `seed02` does not match inside `seed020`
            if re.search(rf"(?<![A-Za-z0-9_]){re.escape(t)}(?![A-Za-z0-9_])", txt):
                named[t].append(str(f.relative_to(REPO)))

    orphans, expected, used = [], [], []
    for t, files in sorted(named.items()):
        why = next(
            (v for k, v in EXPECTED_ONE_OFF.items() if t.startswith(k) or t == k), None
        )
        row = {"tag": t, "dir": tags[t], "referenced_by": files, "note": why}
        if files:
            used.append(row)
        elif why:
            expected.append(row)
        else:
            orphans.append(row)

    # PHANTOMS: tags a script names that have no scored directory. See
    # arm_tags_in_code() for why this is an AST walk and not a grep.
    phantom = []
    cand: set[str] = set()
    for f, txt in texts.items():
        if f.suffix == ".py":
            cand |= arm_tags_in_code(txt)
    for s in sorted(cand - set(tags)):
        phantom.append(s)

    return {
        "on_disk": len(disk),
        "used": used,
        "expected_one_off": expected,
        "orphans": orphans,
        "phantoms": phantom,
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--spiral-out", default="/home/jon/openclaw-workspace/Neo-VM/spiral_out"
    )
    ap.add_argument("--json", default=None)
    ap.add_argument(
        "--fail-on-phantom",
        action="store_true",
        help="exit 1 if a script names an arm that is not on disk",
    )
    a = ap.parse_args()

    r = audit(a.spiral_out)
    print(f"{r['on_disk']} scored arms on disk\n")
    print(f"  used by an analysis or report : {len(r['used'])}")
    print(f"  expected one-offs             : {len(r['expected_one_off'])}")
    print(f"  ORPHANS (scored, never named) : {len(r['orphans'])}")
    print(f"  PHANTOMS (named, not on disk) : {len(r['phantoms'])}")

    if r["orphans"]:
        print("\nORPHANS -- scored but named by nothing. Each is either a deliberate")
        print("one-off (add it to EXPECTED_ONE_OFF with a reason) or a replicate that")
        print("an analysis should be using:")
        for o in r["orphans"]:
            print(f"    {o['tag']:<24} {o['dir']}")
    if r["phantoms"]:
        print(
            "\nPHANTOMS -- named by a script, no scored directory. An analysis may be"
        )
        print("silently running on fewer fits than its author believes:")
        for p in r["phantoms"]:
            print(f"    {p}")

    if a.json:
        Path(a.json).write_text(json.dumps(r, indent=1) + "\n")
        print(f"\nwrote {a.json}")
    return 1 if (a.fail_on_phantom and r["phantoms"]) else 0


if __name__ == "__main__":
    sys.exit(main())
