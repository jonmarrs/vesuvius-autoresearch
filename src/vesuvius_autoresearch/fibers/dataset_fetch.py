"""Deterministic, preflighted acquisition plans for the fiber-skeletons dataset."""

import re
from collections import defaultdict
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path

from vesuvius_autoresearch.fibers.benchmark_artifacts import validate_paths

MAX_LISTING_BYTES = 2 * 1024**2
_ANNOTATION = re.compile(
    r"fibers_(s[0-9]+)a?_([0-9]+)z_([0-9]+)y_([0-9]+)x_([0-9]+)_v([0-9]+)\.nml"
)


def validate_cube(cube):
    if cube is not None and not re.fullmatch(
        r"s[0-9]+_[0-9]+_[0-9]+_[0-9]+_[0-9]+", cube
    ):
        raise ValueError("cube must be a stem such as s1_00497_01497_03997_256")


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.names = set()

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.names.update(value for key, value in attrs if key == "href" and value)


@dataclass(frozen=True)
class Download:
    relative_url: str
    destination: Path


@dataclass(frozen=True)
class FetchPlan:
    downloads: tuple[Download, ...]

    @classmethod
    def create(cls, listing, data_dir, cube=None):
        """Choose the highest numeric version per cube, independent of HTML order.

        ``s1a`` remains the dataset's alias for ``s1``. Distinct names tying for
        the selected version are ambiguous; do not guess which annotation wins.
        Only flat, recognized filenames are eligible remote sources.
        """
        validate_cube(cube)
        parser = _Links()
        parser.feed(listing)
        parser.close()
        candidates = defaultdict(lambda: defaultdict(set))
        for name in parser.names:
            match = _ANNOTATION.fullmatch(name)
            if not match:
                continue
            scroll, z, y, x, size, version = match.groups()
            stem = f"{scroll}_{z}_{y}_{x}_{size}"
            if cube is None or cube == stem:
                candidates[stem][int(version)].add(name)
        if not candidates:
            raise ValueError(
                f"cube not found in dataset: {cube}"
                if cube
                else "no recognized cube annotations in dataset listing"
            )
        downloads = []
        for stem, versions in sorted(candidates.items()):
            latest = max(versions)
            names = sorted(versions[latest])
            if len(names) != 1:
                raise ValueError(
                    f"ambiguous annotations for {stem} version {latest}: {', '.join(names)}"
                )
            downloads.extend(
                Download(source, Path(data_dir) / target)
                for source, target in (
                    (f"nml/{names[0]}", f"{stem}.nml"),
                    (f"imagesTr/{stem}_0000.tif", f"{stem}_image.tif"),
                    (f"labelsTr/{stem}.tif", f"{stem}_semantic.tif"),
                )
            )
        plan = cls(tuple(downloads))
        plan.validate()
        return plan

    def validate(self):
        validate_paths(
            [(entry.destination, "dataset download") for entry in self.downloads], []
        )
