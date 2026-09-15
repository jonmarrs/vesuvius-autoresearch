"""Assert the ink scorer resolved to ONE model revision across a study.

`get_ink_metrics.py` calls `snapshot_download(repo_id='scrollprize/ink-coverage-32um')`
with **no `revision=`**, so it follows the repo's `main` -- a moving reference, the
same class of hazard as rendering from `origin/main`. Nothing fails loudly if the
weights change mid-study; the ink numbers simply stop being comparable, and the
cause would be invisible in every log.

As of 2026-09-14 the cache holds exactly one revision, downloaded 2026-08-31, a
week before the first arm fitted, so every measurement in this project shares it.
This check keeps that true rather than assuming it stays true.

  ./.venv/bin/python scripts/check_scorer_weights_pinned.py
  ... --expect d79c5860674fddd53370a59ee92f229c9b9de88c
"""

import argparse
import sys
from pathlib import Path

REPO_DIR = "models--scrollprize--ink-coverage-32um"
CACHES = (Path.home() / ".cache/huggingface/hub",)
KNOWN = "d79c5860674fddd53370a59ee92f229c9b9de88c"


def revisions(cache: Path) -> list[str]:
    snaps = cache / REPO_DIR / "snapshots"
    return sorted(p.name for p in snaps.iterdir()) if snaps.is_dir() else []


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--expect", default=KNOWN)
    ap.add_argument("--cache", default=None)
    args = ap.parse_args()

    caches = [Path(args.cache)] if args.cache else list(CACHES)
    found: list[str] = []
    for c in caches:
        revs = revisions(c)
        if revs:
            print(f"{c / REPO_DIR}: {len(revs)} revision(s)")
            for r in revs:
                print(f"  {r}")
            found += revs

    if not found:
        print(
            "scorer model not cached anywhere known; nothing scored yet, or a "
            "different HF_HOME is in use."
        )
        return 2
    if len(set(found)) > 1:
        print(
            "\nFAIL: more than one revision has been downloaded. Arms scored "
            "before and after the change are NOT comparable. Identify which arms "
            "used which before using any of them together."
        )
        return 1
    if found[0] != args.expect:
        print(
            f"\nFAIL: revision is {found[0]}, expected {args.expect}. The upstream "
            "model moved and this cache followed it; earlier measurements used "
            "different weights."
        )
        return 1
    print(f"\nPASS: one revision, {found[0]}, matching the expected pin.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
