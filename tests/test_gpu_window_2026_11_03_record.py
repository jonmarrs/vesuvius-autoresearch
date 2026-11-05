"""The 2026-11-03 GPU window's wrapper and its log, committed as evidence, say what findings 103 and 104 say about the
run: the loop was stopped, both registered chains ran from the registration commit and finished, and the loop was
restarted. Each report's trace window is its chain's start and end in the log."""

from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LOG = (ROOT / "reports/evidence/gpu_window_2026-11-03_wrapper.txt").read_text()
SCRIPT = (
    ROOT / "reports/evidence/gpu_window_2026-11-03_wrapper_script.txt"
).read_text()
REPORTS = {
    name: " ".join((ROOT / f"reports/{name}.md").read_text().split())
    for name in ("seed_heading_confirmation", "neural_tracer_refit_retry")
}
REGISTRATION = "f7145c5dac7e16250b986a4d51e9039fd111e68f"


def chains():
    """(start line, end time) of each chain, in log order."""
    starts = re.findall(
        r"^(CHAIN_START .*?)\s+(\d{4}-\d\d-\d\dT\d\d:\d\d):\d\d", LOG, re.M
    )
    ends = re.findall(r"^CHAIN_COMPLETE\s+(\d{4}-\d\d-\d\dT\d\d:\d\d):\d\d", LOG, re.M)
    assert len(starts) == len(ends) == 2
    return [(line, start, end) for (line, start), end in zip(starts, ends, strict=True)]


def test_the_wrapper_stopped_the_loop_ran_both_chains_and_restarted_it():
    assert f"REG={REGISTRATION}" in SCRIPT
    for step in ("stop.sh rc=0", "loop_control status rc=1", "seed-heading confirmation chain rc=0",
                 "refit-retry pilot chain rc=0", "start.sh rc=0", "WRAPPER_DONE"):  # fmt: skip
        assert step in LOG, step
    assert LOG.index("stop.sh rc=0") < LOG.index("CHAIN_START") < LOG.rindex("CHAIN_COMPLETE") < LOG.index("start.sh rc=0")  # fmt: skip


def test_each_report_states_its_chain_s_window_commit_and_villa():
    (seed_line, seed_start, seed_end), (refit_line, refit_start, refit_end) = chains()
    assert REGISTRATION[:8] in seed_line and "villa 39a8cf3a1" in seed_line
    assert REGISTRATION[:8] in refit_line and "villa ccb431818" in refit_line
    for name, start, end in (("seed_heading_confirmation", seed_start, seed_end),
                             ("neural_tracer_refit_retry", refit_start, refit_end)):  # fmt: skip
        day, t0 = start.split("T")
        t1 = end.split("T")[1]
        assert (
            f"Traced {day} {t0}–{t1} PST with the autoresearch loop stopped"
            in REPORTS[name]
        )
    assert "Villa `39a8cf3a`" in REPORTS["seed_heading_confirmation"]
    assert "Villa `ccb431818`" in REPORTS["neural_tracer_refit_retry"]


def test_both_reports_point_at_the_record():
    for text in REPORTS.values():
        assert "`reports/evidence/gpu_window_2026-11-03_wrapper_script.txt`" in text
        assert "its log `reports/evidence/gpu_window_2026-11-03_wrapper.txt`" in text
