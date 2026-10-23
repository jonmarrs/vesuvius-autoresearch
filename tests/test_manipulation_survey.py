"""The manipulation survey's verdicts and its report's table are its numbers.

`scripts/survey_manipulation_effects.py` labelled each null "null, bounds X%",
X being the design MDE. The MDE is what a design could reliably see; what a
null's data rule out is its 95% CI, which for the pinned nulls is much wider
([-18.4%, +16.7%] beside an 11.8% MDE). #192 and #195 corrected the documents
that quoted the MDE as the bound; the survey's own label is corrected here, and
read back from each row's recorded p and effect.

`reports/no_lever_has_improved_reading.md` typed its table from the JSON, and
nothing read it back.
"""

import json
from pathlib import Path

from scripts.survey_manipulation_effects import ALPHA, STUDIES, verdict

_REPO = Path(__file__).resolve().parent.parent
_SURVEY = json.loads(
    (_REPO / "reports" / "manipulation_effects_survey.json").read_text()
)
_REPORT = _REPO / "reports" / "no_lever_has_improved_reading.md"


def _plain(cell):
    """A table cell as written before any struck-through old value."""
    cell = cell.split("~~")[0]
    return cell.replace("*", "").replace("−", "-").strip()


def test_every_verdict_is_the_rule_on_its_recorded_numbers():
    assert set(_SURVEY) == set(STUDIES)
    for name, row in _SURVEY.items():
        assert row["verdict"] == verdict(row), name
        # a null is never labelled with its MDE as a bound
        assert "bound" not in row["verdict"], name
    assert verdict({"p": ALPHA, "rel": 0.5}) == "null"
    assert verdict({"p": ALPHA / 2, "rel": 0.01}) == "IMPROVED"
    assert verdict({"p": ALPHA / 2, "rel": -0.01}) == "HARMED"


def test_the_report_table_is_the_survey():
    rows = {}
    for line in _REPORT.read_text().splitlines():
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) == 7 and _plain(cells[0]).replace("→", "->") in _SURVEY:
            rows[_plain(cells[0]).replace("→", "->")] = cells
    assert set(rows) == set(_SURVEY)
    for name, cells in rows.items():
        row = _SURVEY[name]
        ctl, trt, _ = STUDIES[name]
        assert _plain(cells[1]) == f"{len(ctl)}v{len(trt)}", name
        assert _plain(cells[2]) == f"{row['rel']:+.2%}", name
        assert _plain(cells[3]) == f"{row['p']:.3f}", name
        assert _plain(cells[4]) == f"[{row['lo']:+.1%}, {row['hi']:+.1%}]", name
        assert _plain(cells[5]) == f"{row['mde']:.1%}", name
        assert _plain(cells[6]) == row["verdict"], name


def test_the_largest_gain_a_null_admits_is_the_noted_one():
    nulls = [r for r in _SURVEY.values() if r["verdict"] == "null"]
    top = max(nulls, key=lambda r: r["hi"])
    assert top is _SURVEY["patch bootstrap"]
    flat = " ".join(_REPORT.read_text().split())
    assert (
        f"The largest gain any of them admits is +{top['hi']:.1%}, the top of patch "
        f"bootstrap's [−{-top['lo']:.1%}, +{top['hi']:.1%}]" in flat
    )
