import pytest

from vesuvius_autoresearch.detector import cli


def test_assert_auc_passes_at_target():
    cli.assert_auc({"pixel_auc": 0.711}, target=0.70)  # must not raise


def test_assert_auc_fails_below_target():
    with pytest.raises(AssertionError, match="0.70"):
        cli.assert_auc({"pixel_auc": 0.56}, target=0.70)


def test_main_parses_subcommands():
    assert cli.main(["--help-check"]) == 0  # no-op path returns 0
