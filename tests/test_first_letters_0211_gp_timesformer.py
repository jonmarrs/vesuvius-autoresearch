"""Finding 122: the pickle audit, the segment layout and windows, the comparison on finding 118's synthetic surface,
and the driver's safeguards (checksum, audit before any load, a wandb that sends nothing)."""

import importlib.util
import json
import os
import pickle
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
CONTROL = ROOT / "repro/first_letters/pherc0211_control"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


audit = _load("audit_pickle_under_test", CONTROL / "audit_pickle.py")
gp = _load("gp_timesformer_under_test", CONTROL / "gp_timesformer.py")
f118_tests = _load(
    "f118_tests_for_gp", ROOT / "tests/test_first_letters_0211_reader_control.py"
)
f120_tests = _load(
    "f120_tests_for_gp", ROOT / "tests/test_first_letters_0211_reader_v3.py"
)


# --- the pickle audit -------------------------------------------------------------------------------------------


def test_a_pickle_that_imports_os_system_is_refused(tmp_path):
    for protocol in (0, 2, 4):
        path = tmp_path / f"p{protocol}.pkl"
        path.write_bytes(pickle.dumps(os.system, protocol=protocol))
        result = audit.audit(path, set())
        assert not result["passes"], protocol
        assert result["outside_allowlist"] == ["posix.system"], protocol


def test_memoized_module_names_are_resolved_not_guessed():
    names, refused = audit.imported(
        pickle.dumps([os.path.join, os.path.exists], protocol=4)
    )
    assert names == {"posixpath.join": 1, "genericpath.exists": 1} and refused == []


def test_a_stack_global_whose_names_cannot_be_traced_is_refused():
    # PROTO 4, a string, then an empty tuple (not a string) and STACK_GLOBAL: the names are not two strings
    data = b"\x80\x04\x8c\x02os)\x93."
    names, refused = audit.imported(data)
    assert names == {} and refused and "STACK_GLOBAL" in refused[0]


def test_the_copyreg_extension_registry_is_refused():
    data = b"\x80\x02\x82\x01."  # PROTO 2, EXT1 1, STOP
    names, refused = audit.imported(data)
    assert refused == ["EXT1"]


def test_a_torch_state_dict_passes_with_nothing_allowed(tmp_path):
    torch = pytest.importorskip("torch")
    path = tmp_path / "w.pt"
    torch.save({"state_dict": {"w": torch.zeros(2, 3)}}, path)
    result = audit.audit(path, set())
    assert result["passes"], result
    assert audit.main(["--allow"]) == 2  # a flag without its name is a usage error
    assert audit.main([str(path)]) == 0


def test_a_named_class_is_admitted_only_when_allowed(tmp_path):
    torch = pytest.importorskip("torch")
    path = tmp_path / "opt.pt"
    model = torch.nn.Linear(2, 2)
    torch.save({"opt": torch.optim.AdamW(model.parameters())}, path)
    refused = audit.audit(path, set())
    assert (
        not refused["passes"]
        and "torch.optim.adamw.AdamW" in refused["outside_allowlist"]
    )
    allowed = audit.audit(path, {"torch.optim.adamw.AdamW"})
    assert "torch.optim.adamw.AdamW" not in allowed["outside_allowlist"]


# --- segments and windows ---------------------------------------------------------------------------------------


def test_the_windows_put_the_surface_where_the_model_was_trained_to_find_it():
    assert gp.WINDOWS == {"v9fwd": 18, "v9rev": 17}
    fwd, rev = gp.segment_layers("v9fwd"), gp.segment_layers("v9rev")
    assert list(fwd) == list(range(18, 44)) and list(fwd.values()) == list(
        range(18, 44)
    )
    assert list(rev) == list(range(17, 43)) and list(rev.values()) == list(
        range(48, 22, -1)
    )
    # 15 layers before the surface and 10 after it, in each order's own direction
    assert fwd[18 + 15] == gp.SURFACE and rev[17 + 15] == gp.SURFACE
    assert gp.READING == "v9rev" and gp.OTHER == "v9fwd"


def test_segments_writes_each_order_with_the_render_layers_it_names(tmp_path):
    import cv2
    import zarr

    data = np.stack([np.full((8, 12), k, np.uint8) for k in range(66)])
    render = zarr.open(str(tmp_path / "r.zarr"), mode="w")
    render.create_dataset("0", data=data, chunks=(66, 8, 12))
    written = gp.segments_cmd(tmp_path / "r.zarr", tmp_path / "segs")
    assert written["v9fwd"]["start_idx"] == 18 and written["v9rev"]["start_idx"] == 17
    for order in ("v9fwd", "v9rev"):
        files = sorted((tmp_path / "segs" / order / "layers").iterdir())
        assert len(files) == gp.IN_CHANS
        for number, source in gp.segment_layers(order).items():
            image = cv2.imread(
                str(tmp_path / "segs" / order / "layers" / f"{number:02d}.tif"), 0
            )
            assert int(image[0, 0]) == source
    assert (
        gp.main(["segments", str(tmp_path / "r.zarr"), str(tmp_path / "segs")]) == 2
    )  # written once


# --- the comparison ---------------------------------------------------------------------------------------------


def _write_gp_maps(
    root: Path, reverse_strength: float, forward_same: bool = False
) -> Path:
    """The model's predictions as its script writes them: padded PNGs of 0..255, the winner's strokes on the
    reversed order."""
    import cv2
    import tifffile

    strokes = tifffile.imread(root / "studio.tif").astype(float)
    rng = np.random.default_rng(4)
    maps = root / "gp_maps"
    maps.mkdir()
    h, w = strokes.shape
    for order, base in (
        ("v9rev", strokes),
        ("v9fwd", strokes if forward_same else np.roll(strokes, 37, axis=1)),
    ):
        p = np.clip(
            0.2
            + reverse_strength * 0.6 * base
            + 0.02 * rng.standard_normal(base.shape),
            0,
            1,
        )
        padded = np.zeros((h + 256 - h % 256, w + 256 - w % 256))
        padded[:h, :w] = p
        cv2.imwrite(
            str(gp.gp_file(maps, order)), np.round(padded * 255).astype(np.uint8)
        )
    return maps


def _args(root: Path, gp_maps: Path, v3_maps: Path) -> list[str]:
    args = f118_tests._write_inputs(root)
    args = args[: args.index("--image")]
    return [
        *args,
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
        "--image",
        str(root / "four.png"),
    ]


def test_a_model_that_draws_the_winners_strokes_clearly_is_closer(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    f120_tests._weaken_the_ensemble(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    argv = [*args[: args.index("--image")], "--gp-maps", str(gp_maps), "--v3-maps", str(v3_maps),
            "--image", str(tmp_path / "four.png")]  # fmt: skip
    out = tmp_path / "gp.json"
    assert gp.main(["compare", str(out), *argv]) == 0
    record = json.loads(out.read_text())
    assert record["verdict"] == "GP_CLOSER"
    assert record[gp.NAME]["r"] > record["ensemble"]["r"] + 0.10
    assert record["reading_side"] == "v9rev"
    described = record["described"]
    assert {
        "reader_v3",
        "forward_order_as_reading_side",
        "r_difference_bootstrap",
    } <= set(described)
    assert described["forward_order_as_reading_side"]["r"] < record[gp.NAME]["r"]
    assert (tmp_path / "four.png").exists()
    assert gp.main(["compare", str(out), *argv]) == 2  # measured once


def test_a_model_whose_other_order_carries_the_strokes_too_fails_its_controls(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0, forward_same=True)
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    out = tmp_path / "gp.json"
    assert gp.main(["compare", str(out), *argv]) == 0
    assert json.loads(out.read_text())["verdict"] == "GP_FAILS_CONTROLS"


def test_the_verdict_table_is_finding_120s_under_this_models_name():
    ens = f120_tests._reader(0.53, 0.30)
    assert gp.verdict(ens, f120_tests._reader(0.63, 0.35), 1.0) == "GP_CLOSER"
    assert gp.verdict(ens, f120_tests._reader(0.43, 0.40), 1.0) == "GP_FARTHER"
    assert gp.verdict(ens, f120_tests._reader(0.60, 0.33), 1.0) == "GP_NO_CLOSER"
    assert (
        gp.verdict(ens, f120_tests._reader(0.7, 0.4, wrong=0.36), 1.0)
        == "GP_FAILS_CONTROLS"
    )
    assert gp.verdict(None, None, 1.0) == "DOES_NOT_RUN"


def test_the_lines_are_the_registrations():
    text = (
        ROOT / "docs/preregistration/2026-11-16_first_letters_0211_gp_timesformer.md"
    ).read_text()
    assert "Δr at least +0.10 and Δoverlap at least +0.05 | `GP_CLOSER`" in text
    assert "Δr at most −0.10, or Δoverlap at most −0.05 | `GP_FARTHER`" in text
    assert "**The reading side is the reversed order, fixed now.**" in text
    assert "render layers 18 to 43 in the forward order (`start_idx` 18)" in text
    assert "layers 17 to 42 of the reversed order (`start_idx` 17)" in text


# --- the driver -------------------------------------------------------------------------------------------------


def test_the_driver_checks_and_audits_before_any_load_and_sends_nothing():
    path = CONTROL / "run_gp_timesformer.sh"
    assert os.access(path, os.X_OK)
    text = path.read_text()
    for word in ("aws s3 cp", "gh release", "curl", "--upload-file", "rsync ", "wget"):
        assert word not in text
    order = ["step checksum", "step audit", "step segments", "step infer_v9fwd infer v9fwd 18",
             "step infer_v9rev infer v9rev 17", "step compare"]  # fmt: skip
    positions = [text.index(s) for s in order]
    assert positions == sorted(positions)
    assert (
        "CK_SHA256=93f56e569e1f4c66b71112c41985b64445b5245ff1fb610e44f495c2a0aee36f"
        in text
    )
    assert 'PYTHONPATH="$HERE/gp_stub"' in text and "WANDB_MODE=disabled" in text
    assert "--stride 32 --batch_size 64" in text


def test_the_wandb_stub_does_nothing():
    stub = _load("wandb_stub_under_test", CONTROL / "gp_stub/wandb.py")
    assert (
        stub.init(project="x") is None
        and stub.log({"a": 1}) is None
        and stub.finish() is None
    )
    stub.Image(np.zeros((2, 2)), caption="x")
    source = (CONTROL / "gp_stub/wandb.py").read_text()
    assert (
        "import" not in source.split('"""')[-1]
    )  # nothing imported past the docstring


# --- the pickle audit: each opcode rule, on pickles built by hand ------------------------------------------------


def _string(op: str, text: str) -> bytes:
    raw = text.encode()
    return {
        "SHORT_BINUNICODE": b"\x8c" + bytes([len(raw)]) + raw,
        "BINUNICODE": b"X" + len(raw).to_bytes(4, "little") + raw,
        "BINUNICODE8": b"\x8d" + len(raw).to_bytes(8, "little") + raw,
        "UNICODE": b"V" + raw + b"\n",
        "SHORT_BINSTRING": b"U" + bytes([len(raw)]) + raw,
        "BINSTRING": b"T" + len(raw).to_bytes(4, "little") + raw,
        "STRING": b"S'" + raw + b"'\n",
    }[op]


def _proto4(*parts: bytes) -> bytes:
    return b"\x80\x04" + b"".join(parts) + b"."


def _named(module: str, name: str, op: str = "SHORT_BINUNICODE") -> bytes:
    return _string(op, module) + _string(op, name) + b"\x93"  # STACK_GLOBAL


@pytest.mark.parametrize("op", ["SHORT_BINUNICODE", "BINUNICODE", "BINUNICODE8", "UNICODE",
                                "SHORT_BINSTRING", "BINSTRING", "STRING"])  # fmt: skip
def test_stack_global_names_pushed_by_any_string_opcode_are_read(op):
    names, refused = audit.imported(_proto4(_named("posixpath", "join", op)))
    assert names == {"posixpath.join": 1} and refused == []


@pytest.mark.parametrize(
    ("put", "get"),
    [
        (b"\x94", b"h\x00"),  # MEMOIZE, BINGET
        (b"q\x00", b"h\x00"),  # BINPUT, BINGET
        (b"r\x00\x00\x00\x00", b"j\x00\x00\x00\x00"),  # LONG_BINPUT, LONG_BINGET
        (b"p0\n", b"g0\n"),  # PUT, GET
    ],
    ids=["memoize", "binput", "long_binput", "put"],
)
def test_a_module_name_fetched_back_from_the_memo_is_read_and_counted(put, get):
    data = _proto4(
        _string("SHORT_BINUNICODE", "posixpath"),
        put,
        _string("SHORT_BINUNICODE", "join") + b"\x93",
        get,
        _string("SHORT_BINUNICODE", "join") + b"\x93",
    )
    assert audit.imported(data) == ({"posixpath.join": 2}, [])


def test_two_strings_that_are_no_longer_on_top_name_nothing():
    # "os" and "system", then an empty tuple: STACK_GLOBAL would take the tuple, so no name is guessed
    names, refused = audit.imported(_proto4(_string("SHORT_BINUNICODE", "os"),
                                            _string("SHORT_BINUNICODE", "system"), b")\x93"))  # fmt: skip
    assert names == {} and refused


def test_a_memo_entry_that_is_not_a_string_breaks_the_pair():
    # memo 0 holds an empty tuple; fetched between the two names, it is not a module name
    data = _proto4(b")\x94", _string("SHORT_BINUNICODE", "os"), b"h\x00",
                   _string("SHORT_BINUNICODE", "system"), b"\x93")  # fmt: skip
    names, refused = audit.imported(data)
    assert names == {} and refused


def test_a_class_named_inline_by_inst_is_listed_and_refused(tmp_path):
    path = tmp_path / "inst.pkl"
    path.write_bytes(b"(ios\nsystem\n.")  # MARK, INST os system, STOP
    result = audit.audit(path, set())
    assert result["outside_allowlist"] == ["os.system"] and not result["passes"]


@pytest.mark.parametrize(
    ("op", "code"),
    [
        ("EXT1", b"\x82\x01"),
        ("EXT2", b"\x83\x01\x00"),
        ("EXT4", b"\x84\x01\x00\x00\x00"),
    ],
)
def test_every_copyreg_extension_opcode_refuses_the_file(tmp_path, capsys, op, code):
    path = tmp_path / f"{op}.pkl"
    path.write_bytes(b"\x80\x02" + code + b".")
    result = audit.audit(path, set())
    assert result["refused_opcodes"] == [op] and result["outside_allowlist"] == []
    assert not result["passes"]
    assert audit.main([str(path)]) == 1
    assert "REFUSED" in capsys.readouterr().err


@pytest.mark.parametrize(
    ("module", "name", "passes"),
    [
        ("torch", "FloatStorage", True),
        (
            "torch",
            "FloatStorage.__class__",
            False,
        ),  # an attribute reached through a storage class
        (
            "torch.serialization",
            "Storage",
            False,
        ),  # a module of torch, not torch itself
    ],
)
def test_only_a_storage_class_of_torch_itself_passes_as_storage(
    tmp_path, module, name, passes
):
    path = tmp_path / "global.pkl"
    path.write_bytes(b"\x80\x04c" + module.encode() + b"\n" + name.encode() + b"\n.")
    assert audit.audit(path, set())["passes"] is passes


def test_the_audit_takes_exactly_one_checkpoint(capsys):
    assert audit.main([]) == 2
    assert audit.main(["a.pt", "b.pt"]) == 2
    assert "usage: audit_pickle.py" in capsys.readouterr().err


@pytest.mark.xfail(
    strict=True,
    reason="audit_pickle reads a file up to its first STOP; a legacy (non-zip) torch file is several pickles, "
    "and torch.load unpickles the object after the first",
)
def test_a_legacy_checkpoint_is_audited_past_its_first_pickle(tmp_path):
    torch = pytest.importorskip("torch")
    path = tmp_path / "legacy.pt"
    payload = f120_tests._MakesADirectory(str(tmp_path / "made"))
    torch.save(
        {"w": torch.zeros(2), "x": payload}, path, _use_new_zipfile_serialization=False
    )
    assert not audit.audit(path, set())["passes"]


@pytest.mark.xfail(
    strict=True,
    reason="audit_pickle reads a file as a zip archive wherever Python's zipfile finds one, but torch.load only "
    "when the file starts with the zip signature: a pickle placed before an archive is loaded and never read",
)
def test_a_pickle_placed_before_a_zip_archive_is_audited(tmp_path):
    torch = pytest.importorskip("torch")
    import io

    archive = io.BytesIO()
    torch.save({"w": torch.zeros(2)}, archive)
    payload = f120_tests._MakesADirectory(str(tmp_path / "made"))
    path = tmp_path / "joined.pt"
    path.write_bytes(pickle.dumps(payload, protocol=2) + archive.getvalue())
    assert not audit.audit(path, set())["passes"]
