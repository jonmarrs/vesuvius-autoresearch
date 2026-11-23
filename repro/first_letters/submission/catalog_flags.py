"""How many open-data volumes the PHerc. 343 recipe's orientation rule turns the wrong way, from the catalog's flags.

make_submission_image.py (Nieuwlaar/pherc343-first-letters at e8370f1f) flips the image left-right when theta grows
along the columns and top-bottom when z grows down the rows. That holds in PHerc. 343's frame, where z runs bottom
to top and the coordinates are right-handed. band_index.orientation gives the general rule: z running top to bottom
reverses both senses, and left-handed coordinates reverse the sense of theta. So, per volume, from the catalog's
`z_direction_is_top_to_bottom` (ttb) and `left_handed_coordinates` (lh):

  ttb false, lh false   the recipe's rule holds (PHerc. 343; checked on its published image)
  ttb true,  lh false   both flips wrong: the image is turned by 180 degrees (checked on PHerc. 211's winner surface,
                        Nieuwlaar/pherc343-first-letters#2)
  ttb false, lh true    the left-right flip wrong: the image is mirrored left to right (derived, not checked on data)
  ttb true,  lh true    the top-bottom flip wrong: the image is mirrored top to bottom (derived, not checked on data)
  either flag null      unknown

Reads the catalog's metadata.json (gzipped or not; the bucket keeps it under metadata/history/<stamp>/) and writes
the counts. It reads no CT and no segment.

usage: catalog_flags.py METADATA_JSON OUT.json [--source TEXT]
"""

from __future__ import annotations

import argparse
import gzip
import json
import sys
from collections import Counter
from pathlib import Path

CASES = {
    (False, False): "rule_holds",
    (True, False): "turned_180",
    (False, True): "mirrored_left_right",
    (True, True): "mirrored_top_bottom",
}


def case(top_to_bottom, left_handed) -> str:
    """What the recipe's rule does on a volume with these flags."""
    if not isinstance(top_to_bottom, bool) or not isinstance(left_handed, bool):
        return "unknown"
    return CASES[(top_to_bottom, left_handed)]


def load(path: Path) -> dict:
    raw = path.read_bytes()
    if raw[:2] == b"\x1f\x8b":
        raw = gzip.decompress(raw)
    return json.loads(raw)


def count(catalog: dict) -> dict:
    """Each volume's case, counted over volumes and listed by sample."""
    volumes: Counter = Counter()
    samples: dict[str, set[str]] = {}
    for sample_id, sample in sorted(catalog["samples"].items()):
        for volume_id, volume in sorted((sample.get("volumes") or {}).items()):
            props = volume.get("properties") or {}
            name = case(
                props.get("z_direction_is_top_to_bottom"),
                props.get("left_handed_coordinates"),
            )
            volumes[name] += 1
            samples.setdefault(name, set()).add(sample_id)
    known = sum(n for name, n in volumes.items() if name != "unknown")
    wrong = known - volumes["rule_holds"]
    return {
        "volumes": sum(volumes.values()),
        "volumes_by_case": {
            name: volumes[name] for name in [*CASES.values(), "unknown"]
        },
        "volumes_with_both_flags": known,
        "volumes_the_rule_turns_wrong": wrong,
        "share_of_known_turned_wrong": round(wrong / known, 4) if known else None,
        "samples_by_case": {
            name: sorted(samples.get(name, ())) for name in [*CASES.values(), "unknown"]
        },
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("catalog", type=Path)
    ap.add_argument("out", type=Path)
    ap.add_argument(
        "--source", default=None, help="where the catalog came from, recorded as given"
    )
    args = ap.parse_args(argv)
    record = {"source": args.source, **count(load(args.catalog))}
    args.out.write_text(json.dumps(record, indent=2) + "\n")
    print(
        json.dumps(
            {
                k: record[k]
                for k in ("volumes", "volumes_by_case", "share_of_known_turned_wrong")
            }
        )
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
