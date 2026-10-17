"""The suite draws with matplotlib's non-interactive Agg backend.

With a display (DISPLAY=:0 on the training workstation) matplotlib defaults to
TkAgg. A figure a test closes under TkAgg leaves its Tk interpreter to the
garbage collector. When a collection then runs on a worker thread, as it can
inside test_villa_modules' thread pools, Tcl tears the interpreter down from
the wrong thread and aborts the whole pytest process with SIGILL ("Tcl_AsyncDelete:
async handler deleted by the wrong thread"). That killed a full-suite run on
2026-10-16 at 91%, with no failing test to show for it.
"""

import subprocess
import sys

import matplotlib


def test_the_test_process_draws_with_agg():
    assert matplotlib.get_backend().lower() == "agg"


def test_subprocesses_draw_with_agg():
    child = subprocess.run(
        [sys.executable, "-c", "import matplotlib; print(matplotlib.get_backend())"],
        capture_output=True,
        text=True,
        check=True,
    )
    assert child.stdout.strip().lower() == "agg"
