"""A filing check must reject the wrong month and HTTP-200 non-form pages."""
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import pytest


SPEC = importlib.util.spec_from_file_location(
    "check_prize_form_rollover", Path(__file__).resolve().parents[1] / "scripts/check_prize_form_rollover.py"
)
rollover = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rollover)
URL = "https://docs.google.com/forms/d/e/test/viewform"
TITLE = "October 2026 Progress Prizes"


@pytest.mark.parametrize("status, final, response_form, accepting", [
    (200, URL, True, True),
    (200, URL.replace("viewform", "closedform"), True, False),
    (200, URL.replace("viewform", "closedform/?x=1#top"), True, False),
    (200, "https://accounts.google.com/signin", False, False),
    (200, URL, False, False),
    (503, URL, True, False),
])
def test_form_requires_a_response_form_on_an_open_page(monkeypatch, status, final, response_form, accepting):
    html = f"<title>{TITLE}</title>"
    if response_form:
        html += '<form action="https://docs.google.com/forms/d/e/test/formResponse"></form>'
    response = SimpleNamespace(status=status, geturl=lambda: final, read=lambda: html.encode())

    class Response:
        def __enter__(self):
            return response

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(rollover.urllib.request, "urlopen", lambda *a, **kw: Response())
    assert rollover.form(URL)["accepting_responses"] is accepting


@pytest.mark.parametrize("title, accepting, exit_code", [
    (TITLE, True, 0),
    ("November 2026 Progress Prizes", True, 1),
    (None, True, 1),
    (TITLE, False, 1),
])
def test_cli_requires_the_expected_month(monkeypatch, tmp_path, title, accepting, exit_code):
    output = tmp_path / "record.json"
    monkeypatch.setattr(rollover.sys, "argv", [
        "check_prize_form_rollover.py", "--form", URL, "--expected-title", TITLE, "--out", str(output)
    ])
    monkeypatch.setattr(rollover, "gh", lambda *args: "[]")
    monkeypatch.setattr(rollover, "form", lambda url: {
        "url": url, "http_status": 200, "final_url": url, "title": title, "accepting_responses": accepting
    })
    assert rollover.main() == exit_code
    record = json.loads(output.read_text())
    assert record["filing_form_title_matches"] is (title == TITLE)
    assert record["expected_form_title"] == TITLE
