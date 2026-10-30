"""NML serialization must not change the ground-truth graph or its score."""

import argparse
import hashlib
import json
import re

import numpy as np
import pytest

from vesuvius_autoresearch.fibers import bench_cli
from vesuvius_autoresearch.fibers.eval_trace import score_tracing
from vesuvius_autoresearch.fibers.skeleton_io import load_cube_skeleton, parse_nml

NML = """<things>
<parameters><scale x="1" y="2" z="3"/></parameters>
<thing id="7" name="fiber">
<nodes><node id="10" x="1" y="2" z="3"/>
<node id="20" x="6" y="2" z="3"/></nodes>
<edges><edge source="10" target="20"/></edges>
</thing></things>"""
THING = NML[NML.index("<thing id=") : NML.index("</thing>") + len("</thing>")]
PREFIXED_NML = re.sub(r"(<\/?)(\w+)", r"\1wk:\2", NML).replace(
    "<wk:things>", '<wk:things xmlns:wk="urn:webknossos:nml">'
)


def write_nml(tmp_path, text=NML):
    path = tmp_path / "annotation.nml"
    path.write_text(text, encoding="utf-8")
    return path


@pytest.mark.parametrize(
    "text",
    [
        NML.replace('id="7" name="fiber"', 'name="fiber" id="7"'),
        NML.replace('id="10" x="1" y="2" z="3"', 'z="3" y="2" x="1" id="10"'),
        NML.replace('source="10" target="20"', 'target="20" source="10"'),
        NML.replace('x="1" y="2" z="3"/>', 'z="3" x="1" y="2"/>'),
        NML.replace('"', "'"),
        NML.replace('x="1" y="2" z="3"', 'x="1.0" y="2.0" z="3.0"'),
        NML.replace('x="1" y="2" z="3"', 'x="1e0" y="2e0" z="3e0"'),
        NML.replace('source="10" target="20"/>', 'source="10" target="20"></edge>'),
        NML.replace("<things>", '<things xmlns="urn:webknossos:nml">'),
        PREFIXED_NML,
        NML.replace('x="1" y="2" z="3"', 'x="1"\n radius="1" y="2" z="3"'),
    ],
)
def test_equivalent_xml_preserves_graph_and_connectivity_score(tmp_path, text):
    path = write_nml(tmp_path, text)
    skeleton = parse_nml(path)
    assert len(skeleton) == 1
    assert skeleton.scale_um == (3.0, 2.0, 1.0)
    fiber = skeleton.fibers[0]
    assert fiber.id == 7 and fiber.name == "fiber"
    np.testing.assert_array_equal(fiber.node_ids, [10, 20])
    np.testing.assert_array_equal(fiber.coords, [[3, 2, 1], [3, 2, 6]])
    np.testing.assert_array_equal(fiber.edges, [[0, 1]])
    instances = np.zeros((8, 8, 8), np.int32)
    instances[3, 2, 1:7] = 1
    scores = score_tracing(skeleton, instances, tolerance=0).as_row()
    assert scores["coverage"] == 1.0
    assert scores["erl"] == 5.0
    assert scores["splits"] == scores["merges"] == 0


def test_fractional_nodes_keep_subvoxel_geometry_and_origin(tmp_path):
    text = NML.replace('x="1" y="2" z="3"', 'x="1.25" y="2.5" z="3.75"')
    skeleton = parse_nml(write_nml(tmp_path, text), origin_zyx=(3, 2, 1))
    np.testing.assert_array_equal(skeleton.fibers[0].coords[0], [0.75, 0.5, 0.25])
    assert skeleton.n_nodes == 2 and skeleton.n_edges == 1


def test_xml_entities_in_names_are_decoded(tmp_path):
    text = NML.replace('name="fiber"', 'name="fiber &amp; &#945;"')
    assert parse_nml(write_nml(tmp_path, text)).fibers[0].name == "fiber & α"


def test_source_hash_is_bound_to_the_bytes_parsed(tmp_path, monkeypatch):
    import xml.etree.ElementTree as ET

    path = write_nml(tmp_path)
    captured = path.read_bytes()
    original = ET.fromstring

    def rewrite_after_capture(source):
        path.write_text(NML.replace('x="6"', 'x="5"'))
        return original(source)

    monkeypatch.setattr(ET, "fromstring", rewrite_after_capture)
    skeleton = parse_nml(path)
    assert skeleton.fibers[0].coords[-1, -1] == 6.0
    assert skeleton.source_sha256 == hashlib.sha256(captured).hexdigest()
    assert skeleton.source_sha256 != hashlib.sha256(path.read_bytes()).hexdigest()


def test_commented_out_annotations_do_not_invent_graphs(tmp_path):
    text = NML.replace("</things>", f"<!--{THING}--></things>")
    # A commented copy has the same IDs: it is not another annotation.
    skeleton = parse_nml(write_nml(tmp_path, text))
    assert len(skeleton) == 1 and skeleton.n_nodes == 2 and skeleton.n_edges == 1


@pytest.mark.parametrize(
    "text, message",
    [
        (NML.replace("</things>", ""), "XML"),
        ("<html/>", "things"),
        (NML.replace('id="20"', 'id="10"'), "duplicate.*node"),
        (NML.replace("</things>", THING + "</things>"), "duplicate.*thing"),
        (
            NML.replace("</thing>", THING.replace('id="7"', 'id="8"') + "</thing>"),
            "nested thing",
        ),
        (NML.replace(' x="6"', ""), "node.*x"),
        (NML.replace('x="6"', 'x="NaN"'), "node.*x"),
        (NML.replace('x="6"', 'x="inf"'), "node.*x"),
        (NML.replace('x="6"', 'x="nonsense"'), "node.*x"),
        (NML.replace('id="20"', 'id="-1"'), "node.*id"),
        (NML.replace('id="20"', 'id="1.5"'), "node.*id"),
        (NML.replace('id="20"', 'id="9223372036854775808"'), "node.*id"),
        (NML.replace('source="10" ', ""), "edge.*source"),
        (NML.replace('source="10"', 'source="-1"'), "edge.*source"),
        (NML.replace('<scale x="1"', '<scale x="0"'), "scale.*x"),
        (NML.replace('<scale x="1"', '<scale x="NaN"'), "scale.*x"),
    ],
)
def test_malformed_or_ambiguous_graphs_fail_with_source_context(
    tmp_path, text, message
):
    path = write_nml(tmp_path, text)
    with pytest.raises(ValueError, match=message) as failure:
        parse_nml(path)
    assert path.name in str(failure.value)


@pytest.mark.parametrize(
    "origin", [(1, 2), (1, 2, 3, 4), (0, 0, float("nan")), (True, 0, 0)]
)
def test_invalid_origins_fail_before_creating_graphs(tmp_path, origin):
    with pytest.raises(ValueError, match="origin"):
        parse_nml(write_nml(tmp_path), origin_zyx=origin)


def test_localization_that_overflows_is_refused(tmp_path):
    path = write_nml(tmp_path, NML.replace('x="6"', 'x="1.7e308"'))
    with pytest.raises(ValueError, match="localized.*finite"):
        parse_nml(path, origin_zyx=(0, 0, -1.7e308))


def test_dangling_edges_are_visible_and_strict_mode_rejects_them(tmp_path):
    text = NML.replace("</edges>", '<edge source="20" target="999"/></edges>')
    path = write_nml(tmp_path, text)
    with pytest.warns(RuntimeWarning, match="1.*dangling"):
        skeleton = parse_nml(path)
    assert skeleton.n_edges == 1
    with pytest.raises(ValueError, match="dangling"):
        parse_nml(path, strict_edges=True)


def test_cube_loader_forwards_strict_graph_policy(tmp_path):
    path = tmp_path / "s1_00000_00000_00000_8.nml"
    path.write_text(NML.replace('target="20"', 'target="999"'))
    with pytest.raises(ValueError, match="dangling"):
        load_cube_skeleton(tmp_path, path.stem, strict_edges=True)


@pytest.fixture
def cube(tmp_path):
    import tifffile

    stem = "s1_00000_00000_00000_8"
    (tmp_path / f"{stem}.nml").write_text(NML)
    tifffile.imwrite(tmp_path / f"{stem}_image.tif", np.zeros((8, 8, 8), np.uint8))
    instances = tmp_path / "instances.npy"
    labels = np.zeros((8, 8, 8), np.int32)
    labels[3, 2, 1:7] = 1
    np.save(instances, labels)
    return tmp_path, stem, instances


def test_benchmark_records_the_parser_version_and_strict_policy(cube):
    from vesuvius_autoresearch.fibers.skeleton_io import NML_PARSER_VERSION

    root, stem, instances = cube
    output = root / "result.json"
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(root),
                "score",
                "--cube",
                stem,
                "--instances",
                str(instances),
                "--json-out",
                str(output),
                "--tolerance",
                "0",
                "--strict-nml",
            ]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert report["provenance"]["skeleton_parser"] == {
        "version": NML_PARSER_VERSION,
        "dangling_edges": "error",
    }
    assert report["rows"]["instances"]["erl"] == 5.0


@pytest.mark.parametrize("command_name", ["score", "floors", "trace"])
def test_strict_benchmark_refuses_partial_ground_truth_without_replacing_report(
    cube, command_name
):
    root, stem, instances = cube
    (root / f"{stem}.nml").write_text(NML.replace('target="20"', 'target="999"'))
    output = root / "result.json"
    output.write_bytes(b"previous complete report")
    extra = ["--instances", str(instances)] if command_name == "score" else []
    with pytest.raises(ValueError, match="dangling"):
        bench_cli.main(
            [
                "--data-dir",
                str(root),
                command_name,
                "--cube",
                stem,
                *extra,
                "--json-out",
                str(output),
                "--strict-nml",
            ]
        )
    assert output.read_bytes() == b"previous complete report"


@pytest.mark.parametrize("prior_policy", ["same", "legacy", "old_parser", "strict"])
def test_floor_refresh_only_preserves_rows_with_matching_import_provenance(
    cube, monkeypatch, prior_policy
):
    root, stem, instances = cube
    gt = load_cube_skeleton(root, stem)
    record = {"inference": {"fixture": "toy"}, "probability_sha256": "toy"}
    (root / f"{stem}_fiberprob.json").write_text(json.dumps(record))
    args = argparse.Namespace(tolerance=0.0, mask_threshold=0.5, strict_nml=False)
    provenance = bench_cli._measurement_provenance(root, stem, args, gt)
    if prior_policy == "legacy":
        provenance.pop("skeleton_parser")
    elif prior_policy == "old_parser":
        provenance["skeleton_parser"]["version"] = 1
    elif prior_policy == "strict":
        provenance["skeleton_parser"]["dangling_edges"] = "error"
    row = score_tracing(gt, np.load(instances), tolerance=0).as_row()
    output = root / "all.json"
    output.write_text(
        json.dumps(
            {
                "cubes": {
                    stem: {
                        "provenance": provenance,
                        "rows": {"tracer_strict_relink": row},
                    }
                }
            }
        )
    )
    monkeypatch.setattr(bench_cli, "CUBES", [stem])
    monkeypatch.setattr(bench_cli, "_fiber_prob", lambda *args: np.ones((8, 8, 8)))
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(root),
                "floors",
                "--all-cubes",
                "--tolerance",
                "0",
                "--json-out",
                str(output),
            ]
        )
        == 0
    )
    current = json.loads(output.read_text())["cubes"][stem]
    assert ("tracer_strict_relink" in current["rows"]) == (prior_policy == "same")


def test_score_report_does_not_rehash_changed_ground_truth_after_scoring(
    cube, monkeypatch
):
    from vesuvius_autoresearch.fibers import eval_trace

    root, stem, instances = cube
    nml = root / f"{stem}.nml"
    captured_hash = hashlib.sha256(nml.read_bytes()).hexdigest()
    original = eval_trace.score_tracing

    def rewrite(*args, **kwargs):
        result = original(*args, **kwargs)
        nml.write_text(NML.replace('x="6"', 'x="5"'))
        return result

    monkeypatch.setattr(eval_trace, "score_tracing", rewrite)
    output = root / "score.json"
    assert (
        bench_cli.main(
            [
                "--data-dir",
                str(root),
                "score",
                "--cube",
                stem,
                "--instances",
                str(instances),
                "--json-out",
                str(output),
                "--tolerance",
                "0",
            ]
        )
        == 0
    )
    report = json.loads(output.read_text())
    assert report["provenance"]["skeleton_sha256"] == captured_hash
    assert report["rows"]["instances"]["erl"] == 5.0
    assert captured_hash != hashlib.sha256(nml.read_bytes()).hexdigest()


def test_strict_all_cubes_refuses_a_later_bad_graph_before_any_inference(
    cube, monkeypatch
):
    import tifffile

    root, stem, _ = cube
    bad = "s1_00010_00000_00000_8"
    (root / f"{bad}.nml").write_text(NML.replace('target="20"', 'target="999"'))
    tifffile.imwrite(root / f"{bad}_image.tif", np.zeros((8, 8, 8), np.uint8))
    record = {"inference": {"fixture": "toy"}, "probability_sha256": "toy"}
    for name in (stem, bad):
        (root / f"{name}_fiberprob.json").write_text(json.dumps(record))
    inferred = []

    def infer(data_dir, cube_name, *args):
        inferred.append(cube_name)
        return np.ones((8, 8, 8))

    monkeypatch.setattr(bench_cli, "CUBES", [stem, bad])
    monkeypatch.setattr(bench_cli, "_fiber_prob", infer)
    output = root / "all.json"
    previous = json.dumps({"cubes": {}}).encode()
    output.write_bytes(previous)
    with pytest.raises(ValueError, match="dangling"):
        bench_cli.main(
            [
                "--data-dir",
                str(root),
                "floors",
                "--all-cubes",
                "--json-out",
                str(output),
                "--strict-nml",
            ]
        )
    assert inferred == []
    assert output.read_bytes() == previous
