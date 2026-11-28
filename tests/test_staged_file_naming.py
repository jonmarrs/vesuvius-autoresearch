"""``staged_file`` names its staging sibling after the output, and short enough for any valid name.

#579 renamed every staged file ``.staged-*``. The leftover checks that look for ``.{stem}-*`` beside an output
then matched nothing, and 20 tests in five files stopped checking cleanup. A full-length stem, the name before
#579, breaks a 239-character artifact stem (errno 36): the prefix keeps the stem's first 64 characters.
"""

import pytest

from vesuvius_autoresearch.core import new_artifacts


def test_a_failed_publication_leaves_nothing_beside_the_output(tmp_path):
    output = tmp_path / "export.pt"
    with pytest.raises(RuntimeError, match="interrupted"):
        with new_artifacts.staged_file(output, suffix=".pt") as staging:
            assert staging.parent == tmp_path
            assert staging.name.startswith(".export-") and staging.suffix == ".pt"
            staging.write_bytes(b"partial checkpoint")
            raise RuntimeError("interrupted")
    assert not list(tmp_path.iterdir())


def test_the_longest_valid_name_still_stages(tmp_path):
    output = tmp_path / ("r" * 250 + ".json")  # 255 bytes, the filesystem's limit
    with new_artifacts.staged_file(output, suffix=".json") as staging:
        assert staging.name.startswith(
            "." + "r" * new_artifacts.STAGING_STEM_LIMIT + "-"
        )
        assert len(staging.name.encode()) < 255
        staging.write_text("{}")
    assert [p.name for p in tmp_path.iterdir()] == [output.name]
    assert output.read_text() == "{}"
