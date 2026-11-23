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


def _zip_of(path: Path, data: bytes, name: str = "archive/data.pkl") -> None:
    """A zip the torch reader will open, with ``data`` as the named record."""
    _write_named(
        path,
        [("archive/version", b"3\n"), ("archive/byteorder", b"little"), (name, data)],
    )


def test_a_pickle_that_imports_os_system_is_refused(tmp_path):
    for protocol in (0, 2, 4):
        path = tmp_path / f"p{protocol}.pt"
        _zip_of(path, pickle.dumps(os.system, protocol=protocol))
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
    # The loader is handed the copy that was checksummed and audited, not $CK.
    assert 'cp -- "$CK" "$CK_COPY"' in text
    assert "echo '$CK_SHA256  $CK_COPY'" in text
    assert '"$CK_COPY"' in text.split("step audit", 1)[1]
    assert '--model_path "$CK_COPY"' in text
    assert text.index('cp -- "$CK" "$CK_COPY"') < text.index("step checksum")


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
    path = tmp_path / "inst.pt"
    _zip_of(path, b"(ios\nsystem\n.")  # MARK, INST os system, STOP
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
    path = tmp_path / f"{op}.pt"
    _zip_of(path, b"\x80\x02" + code + b".")
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
    path = tmp_path / "global.pt"
    _zip_of(path, b"\x80\x04c" + module.encode() + b"\n" + name.encode() + b"\n.")
    assert audit.audit(path, set())["passes"] is passes


def test_the_audit_takes_exactly_one_checkpoint(capsys):
    assert audit.main([]) == 2
    assert audit.main(["a.pt", "b.pt"]) == 2
    assert "usage: audit_pickle.py" in capsys.readouterr().err


def _write_tar(path: Path, members: list[tuple[str, bytes]]) -> None:
    import io
    import tarfile

    with tarfile.open(path, "w:", format=tarfile.PAX_FORMAT) as archive:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def _stored_zip(members: list[tuple[str, bytes]]) -> bytes:
    """A stored zip whose central directory lists members in ``members`` order."""
    import struct
    import zipfile as zipfmt

    def local(name: str, data: bytes) -> bytes:
        raw = name.encode()
        crc = zipfmt.crc32(data) & 0xFFFFFFFF
        header = struct.pack(
            "<IHHHHHIIIHH",
            0x04034B50,
            20,
            0,
            0,
            0,
            0,
            crc,
            len(data),
            len(data),
            len(raw),
            0,
        )
        return header + raw + data

    def central(name: str, data: bytes, offset: int) -> bytes:
        raw = name.encode()
        crc = zipfmt.crc32(data) & 0xFFFFFFFF
        header = struct.pack(
            "<IHHHHHHIIIHHHHHII",
            0x02014B50,
            20,
            20,
            0,
            0,
            0,
            0,
            crc,
            len(data),
            len(data),
            len(raw),
            0,
            0,
            0,
            0,
            0,
            offset,
        )
        return header + raw

    parts: list[bytes] = []
    metas = []
    offset = 0
    for name, data in members:
        chunk = local(name, data)
        metas.append((name, data, offset))
        parts.append(chunk)
        offset += len(chunk)
    directory = b"".join(central(name, data, at) for name, data, at in metas)
    end = struct.pack(
        "<IHHHHIIH", 0x06054B50, 0, 0, len(metas), len(metas), len(directory), offset, 0
    )
    return b"".join(parts) + directory + end


def _touch(marker: Path) -> bytes:
    class Touch:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    return pickle.dumps(Touch(), protocol=2)


def _torch_records() -> list[tuple[str, bytes]]:
    return [("archive/version", b"3\n"), ("archive/byteorder", b"little")]


def _write_named(path: Path, members: list[tuple[str, bytes]]) -> None:
    import io
    import warnings
    import zipfile

    buf = io.BytesIO()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", UserWarning)
        with zipfile.ZipFile(buf, "w") as archive:
            for name, data in members:
                archive.writestr(name, data)
    path.write_bytes(buf.getvalue())


@pytest.mark.parametrize("name", ["archive/DATA.PKL", "archive/data.PKL"])
def test_a_pkl_suffix_in_another_case_is_the_pickle_torch_runs(tmp_path, name):
    """miniz matches the suffix without regard to case; a case-sensitive scan does not."""
    torch = pytest.importorskip("torch")
    path = tmp_path / "case.pt"
    # version is first, so a scan of only the first member never sees the pickle.
    _write_named(
        path,
        _torch_records() + [(name, pickle.dumps(os.system, protocol=2))],
    )
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "posix.system" in result["outside_allowlist"]
    assert torch.load(path, weights_only=False) is os.system


def test_a_later_pickle_member_is_audited_not_only_data_pkl(tmp_path):
    """A benign ``data.pkl`` followed by another pickle must not pass on its own."""
    path = tmp_path / "later.pt"
    _write_named(
        path,
        [("archive/data.pkl", pickle.dumps({"ok": 1}, protocol=2))]
        + _torch_records()
        + [("archive/weights.pkl", pickle.dumps(os.system, protocol=2))],
    )
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "posix.system" in result["outside_allowlist"]
    # Record names are what torch's reader uses, without the archive/ prefix.
    assert "weights.pkl" in result["pickles"]
    assert "data.pkl" in result["pickles"]


@pytest.mark.parametrize(
    ("order", "stored", "executes"),
    [("EEB", True, True), ("EBB", True, False), ("EBEB", False, True)],
)
def test_duplicate_data_pkl_members_are_refused(tmp_path, order, stored, executes):
    """zipfile.read returns the last copy. torch.load can execute an earlier one.

    Stored EEB and a ZipFile-written EBEB are the orders where torch 2.9.1 does
    that. EBB is refused as a duplicate even when both readers currently agree
    on the benign last copy.
    """
    torch = pytest.importorskip("torch")
    import zipfile

    marker = tmp_path / "ran"
    path = tmp_path / f"{order}.pt"
    evil = _touch(marker)
    benign = pickle.dumps({"ok": 1}, protocol=2)
    copies = [(evil if item == "E" else benign) for item in order]
    if stored:
        path.write_bytes(
            _stored_zip(
                [("archive/data.pkl", data) for data in copies] + _torch_records()
            )
        )
    else:
        # ZipFile's data-descriptor flag makes torch 2.9.1 execute the third
        # copy of a four-copy member. The other records are what torch.save writes.
        import io

        saved = io.BytesIO()
        torch.save({"w": torch.zeros(1)}, saved)
        with zipfile.ZipFile(io.BytesIO(saved.getvalue())) as archive:
            others = [
                (info.filename, archive.read(info))
                for info in archive.infolist()
                if not info.filename.casefold().endswith(".pkl")
            ]
        _write_named(path, [("archive/data.pkl", data) for data in copies] + others)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["refused_opcodes"] == ["duplicate member"]
    with zipfile.ZipFile(path) as archive:
        assert archive.read("archive/data.pkl") == benign
    torch.load(path, weights_only=False)
    assert marker.exists() is executes
    marker.unlink(missing_ok=True)


def test_an_appended_second_zip_is_refused(tmp_path):
    """zipfile reads the second archive. A shifted central directory is refused."""
    torch = pytest.importorskip("torch")
    import struct
    import zipfile

    marker = tmp_path / "ran"
    path = tmp_path / "appended.pt"
    evil = _touch(marker)
    benign = pickle.dumps({"ok": 1}, protocol=2)
    first = _stored_zip([("archive/data.pkl", evil)] + _torch_records())
    second = _stored_zip([("archive/data.pkl", benign)] + _torch_records())
    path.write_bytes(first + second)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["message"] == audit.SHIFTED_ZIP
    with zipfile.ZipFile(path) as archive:
        assert archive.read("archive/data.pkl") == benign
        eocd = path.read_bytes().rfind(b"PK\x05\x06")
        recorded = struct.unpack_from("<I", path.read_bytes(), eocd + 16)[0]
        assert archive.start_dir != recorded
    with pytest.raises(RuntimeError):
        torch.load(path, weights_only=False)
    assert not marker.exists()


def test_bytes_after_the_archive_are_refused(tmp_path):
    path = tmp_path / "tail.pt"
    benign = pickle.dumps({"ok": 1}, protocol=2)
    path.write_bytes(
        _stored_zip([("archive/data.pkl", benign)] + _torch_records()) + b"TRAILER"
    )
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["message"] == audit.SHIFTED_ZIP


def test_a_missing_checkpoint_and_a_url_are_refused(tmp_path):
    checkpoints = importlib.import_module("vesuvius_autoresearch.core.checkpoint_tools")
    missing = tmp_path / "gone.pt"
    with pytest.raises(ValueError, match="refusing a missing checkpoint"):
        checkpoints.require_zip_checkpoint(missing)
    with pytest.raises(ValueError, match="refusing a missing checkpoint"):
        checkpoints.load_checkpoint(missing, weights_only=True)
    for url in ("https://example.invalid/w.pt", "s3://bucket/w.pt"):
        with pytest.raises(ValueError, match="refusing a checkpoint URL"):
            checkpoints.require_zip_checkpoint(url)


def test_infer_resenc_refuses_a_non_zip_and_loads_a_zip(tmp_path):
    """The script's torch.load wrapper is the gate. Importing the file also trains.

    Only the prefix that installs the wrapper is executed, so the dataset read
    at the bottom of the script does not run.
    """
    torch = pytest.importorskip("torch")
    path = ROOT / "repro" / "gp_winner" / "infer_resenc.py"
    source = path.read_text()
    prefix = source[: source.index("\nPIL.Image.MAX_IMAGE_PIXELS")]
    namespace: dict = {"__name__": "infer_resenc_under_test"}
    exec(prefix, namespace)  # noqa: S102 - the wrapper under test, not the training script
    original = namespace["_original_load"]
    torch.load = original
    try:
        marker = tmp_path / "ran"
        legacy = tmp_path / "legacy.pt"
        legacy.write_bytes(_touch(marker))
        with pytest.raises(ValueError, match="convert it offline to zip"):
            namespace["_load_no_weights_only"](str(legacy), weights_only=True)
        assert not marker.exists()
        good = tmp_path / "good.pt"
        torch.save({"w": torch.zeros(1)}, good)
        loaded = namespace["_load_no_weights_only"](str(good), map_location="cpu")
        assert tuple(loaded["w"].shape) == (1,)
        with pytest.raises(ValueError, match="refusing a missing checkpoint"):
            namespace["_require_zip"](tmp_path / "gone.pt")
        with pytest.raises(ValueError, match="refusing a checkpoint URL"):
            namespace["_require_zip"]("https://example.invalid/w.pt")
    finally:
        torch.load = original


@pytest.mark.parametrize(
    "payload",
    [b"PK\x03\x04", b"PK\x03\x04truncated", b"PK\x03\x04" + pickle.dumps({"w": 1})],
)
def test_a_file_that_only_starts_with_the_zip_signature_is_refused(tmp_path, payload):
    path = tmp_path / "broken.pt"
    path.write_bytes(payload)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["message"] == audit.NON_ZIP_CHECKPOINT
    assert audit.main([str(path)]) == 1


def test_a_malicious_zip_is_refused_at_the_weights_only_false_sites(tmp_path):
    """A valid torch zip whose pickle is os.system never reaches the unpickler."""
    torch = pytest.importorskip("torch")
    marker = tmp_path / "ran"

    class Touch:
        def __reduce__(self):
            return (os.system, (f"touch {marker}",))

    evil = tmp_path / "evil.pt"
    torch.save(Touch(), evil)
    checkpoints = importlib.import_module("vesuvius_autoresearch.core.checkpoint_tools")
    with pytest.raises(ValueError, match="posix.system"):
        checkpoints.load_checkpoint(evil, weights_only=False)
    assert not marker.exists()

    infer_mod = importlib.import_module("vesuvius_autoresearch.detector.infer")
    config_mod = importlib.import_module("vesuvius_autoresearch.detector.config")
    with pytest.raises(ValueError, match="posix.system"):
        infer_mod.infer(
            config_mod.DetectorConfig(data_root=str(tmp_path)),
            str(evil),
            "frag",
        )
    assert not marker.exists()

    # The fiber loader builds the network from plans, then audits the zip.
    semantic = importlib.import_module("vesuvius_autoresearch.fibers.semantic")
    bundle = tmp_path / "bundle"
    (bundle / "fold_0").mkdir(parents=True)
    (bundle / "plans.json").write_text(
        '{"configurations":{"3d_fullres":{"patch_size":[4,4,4],'
        '"normalization_schemes":["ZScoreNormalization"],'
        '"use_mask_for_norm":[false],'
        '"architecture":{"network_class_name":"test.Network",'
        '"arch_kwargs":{"strides":[[1,1,1]]}}}}}'
    )
    import json

    labels = {name: index for index, name in semantic.LABELS.items()}
    (bundle / "dataset.json").write_text(
        json.dumps({"channel_names": {"0": "CT"}, "labels": labels})
    )

    class BundleNetwork(torch.nn.Module):
        def __init__(self, **kwargs):
            super().__init__()
            self.encoder = torch.nn.Linear(1, 1)

    original_import = semantic._import_by_path
    semantic._import_by_path = lambda name: BundleNetwork
    torch.save(Touch(), bundle / "fold_0" / "checkpoint_final.pth")
    try:
        with pytest.raises(ValueError, match="posix.system"):
            semantic.load_model(bundle, device="cpu")
    finally:
        semantic._import_by_path = original_import
    assert not marker.exists()

    path = ROOT / "repro" / "gp_winner" / "infer_resenc.py"
    source = path.read_text()
    prefix = source[: source.index("\nPIL.Image.MAX_IMAGE_PIXELS")]
    namespace: dict = {"__name__": "infer_resenc_malicious"}
    exec(prefix, namespace)  # noqa: S102 - the wrapper under test
    torch.load = namespace["_original_load"]
    try:
        with pytest.raises(ValueError, match="posix.system"):
            namespace["_load_no_weights_only"](str(evil))
    finally:
        torch.load = namespace["_original_load"]
    assert not marker.exists()


def _legacy_prefix() -> bytes:
    """The three pickles a legacy torch.load finishes before the object."""
    torch = pytest.importorskip("torch")
    from torch.serialization import MAGIC_NUMBER, PROTOCOL_VERSION

    return b"".join(
        pickle.dumps(value, protocol=0)
        for value in (
            MAGIC_NUMBER,
            PROTOCOL_VERSION,
            {"protocol_version": PROTOCOL_VERSION},
        )
    )


def _stopless(module: str, name: str, arg: str) -> bytes:
    """A protocol-0 call with no STOP."""
    text = f"c{module}\n{name}\n(S'{arg}'\ntR"
    assert "\x00" not in text
    return text.encode()


def _assert_non_zip_refused(path: Path) -> None:
    """The audit and both loaders refuse ``path`` and name the offline conversion."""
    import io

    checkpoints = importlib.import_module("vesuvius_autoresearch.core.checkpoint_tools")
    NON_ZIP_CHECKPOINT = checkpoints.NON_ZIP_CHECKPOINT
    load_checkpoint = checkpoints.load_checkpoint

    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["message"] == NON_ZIP_CHECKPOINT
    assert "not a zip checkpoint" in result["refused_opcodes"]
    assert audit.main([str(path)]) == 1
    blob = path.read_bytes()
    with pytest.raises(ValueError, match="convert it offline to zip"):
        load_checkpoint(path, weights_only=False)
    with pytest.raises(ValueError, match="convert it offline to zip"):
        load_checkpoint(io.BytesIO(blob), weights_only=False)


def test_a_legacy_checkpoint_is_refused_by_path_and_bytesio(tmp_path, capsys):
    torch = pytest.importorskip("torch")
    path = tmp_path / "legacy.pt"
    torch.save({"w": torch.zeros(2)}, path, _use_new_zipfile_serialization=False)
    _assert_non_zip_refused(path)
    assert "convert it offline to zip" in capsys.readouterr().err


def test_a_tar_checkpoint_is_refused_by_path_and_bytesio(tmp_path):
    path = tmp_path / "legacy.tar"
    _write_tar(path, [("pickle", pickle.dumps({"w": 1}, protocol=2))])
    _assert_non_zip_refused(path)


def test_a_magic_pickle_then_a_stopless_import_is_refused(tmp_path):
    torch = pytest.importorskip("torch")
    from torch.serialization import MAGIC_NUMBER

    marker = tmp_path / "ran"
    path = tmp_path / "magic.pkl"
    path.write_bytes(
        pickle.dumps(MAGIC_NUMBER, protocol=0)
        + _stopless("os", "system", f"touch {marker}")
    )
    _assert_non_zip_refused(path)
    assert not marker.exists()


def test_a_legacy_header_then_a_stopless_makedirs_is_refused(tmp_path):
    pytest.importorskip("torch")
    marker = tmp_path / "made"
    path = tmp_path / "shaped.pkl"
    path.write_bytes(_legacy_prefix() + _stopless("os", "makedirs", str(marker)))
    _assert_non_zip_refused(path)
    assert not marker.exists()


def _bytestring_tar(path: Path, length: int, evil: bytes) -> None:
    """A tar whose first header is a BINBYTES8 of ``length`` bytes, then ``evil``."""
    import struct
    import tarfile

    plain = path.with_name(path.name + ".plain")
    _write_tar(plain, [("pickle", pickle.dumps(0, protocol=2))])
    blob = bytearray(plain.read_bytes())
    header = blob[:512]
    header[:9] = b"\x8e" + struct.pack("<Q", length)
    header[148:156] = b"        "
    header[148:156] = f"{sum(header):06o}\0 ".encode()
    blob[:512] = header
    if len(blob) > 9 + length:
        raise AssertionError("the tar is longer than the bytestring")
    path.write_bytes(bytes(blob) + b"\x00" * (9 + length - len(blob)) + evil)
    assert tarfile.is_tarfile(path)


@pytest.mark.parametrize("length", [1024 * 1024 + 4096, 4 * 1024 * 1024])
def test_a_long_bytestring_hides_an_import_past_the_tar(tmp_path, length):
    marker = tmp_path / "ran"
    path = tmp_path / "long.tar"
    _bytestring_tar(path, length, _stopless("os", "system", f"touch {marker}"))
    _assert_non_zip_refused(path)
    assert not marker.exists()


def test_a_frame_that_extends_past_its_stop_hides_the_next_pickle(tmp_path):
    torch = pytest.importorskip("torch")
    import struct

    from torch.serialization import MAGIC_NUMBER

    marker = tmp_path / "framed"
    magic = pickle.dumps(MAGIC_NUMBER, protocol=0)
    inner = magic + b"".join(pickle.dumps(0, protocol=0) for _ in range(4))
    path = tmp_path / "framed.pkl"
    path.write_bytes(
        b"\x80\x04\x95"
        + struct.pack("<Q", len(inner))
        + inner
        + _stopless("os", "system", f"touch {marker}")
    )
    _assert_non_zip_refused(path)
    assert not marker.exists()


def test_zip_tensor_checkpoints_still_load(tmp_path):
    torch = pytest.importorskip("torch")
    import io

    load_checkpoint = importlib.import_module(
        "vesuvius_autoresearch.core.checkpoint_tools"
    ).load_checkpoint

    for n in range(256):
        path = tmp_path / f"{n}.pt"
        torch.save(torch.zeros(n), path)
        assert audit.audit(path, set())["passes"] is True
        loaded = load_checkpoint(path, map_location="cpu", weights_only=True)
        assert tuple(loaded.shape) == (n,)
        again = load_checkpoint(
            io.BytesIO(path.read_bytes()), map_location="cpu", weights_only=True
        )
        assert tuple(again.shape) == (n,)


def test_the_pinned_gp_checkpoint_still_loads():
    pytest.importorskip("torch")
    path = ROOT / "villa/ink-detection/timesformer_weights.ckpt"
    if not path.is_file():
        pytest.skip("the pinned Grand Prize checkpoint is not in this checkout")
    # weights_only=False: that checkpoint carries defaultdict, AdamW and
    # CosineAnnealingLR. The audit allows those and still runs first.
    checkpoints = importlib.import_module("vesuvius_autoresearch.core.checkpoint_tools")
    loaded = checkpoints.load_checkpoint(
        path,
        map_location="cpu",
        weights_only=False,
        allow=checkpoints.CHECKPOINT_CLASS_ALLOW,
    )
    assert isinstance(loaded, dict) and loaded


# --- the segments, the prediction reader and the comparison's other branches ------------------------------------


@pytest.mark.parametrize(
    ("layers", "dtype", "message"),
    [(65, np.uint8, "65 layers, not 66"), (66, np.uint16, "uint16, not 8-bit")],
)
def test_segments_refuse_a_render_of_another_depth_or_type(
    tmp_path, layers, dtype, message
):
    import zarr

    render = zarr.open(str(tmp_path / "r.zarr"), mode="w")
    render.create_dataset(
        "0", data=np.zeros((layers, 8, 12), dtype), chunks=(layers, 8, 12)
    )
    with pytest.raises(SystemExit, match=message):
        gp.segments_cmd(tmp_path / "r.zarr", tmp_path / "segs")


def test_a_prediction_that_cannot_be_read_or_is_smaller_than_the_render_is_refused(
    tmp_path,
):
    import cv2

    unreadable = tmp_path / "unreadable.png"
    unreadable.write_bytes(b"not an image")
    with pytest.raises(SystemExit, match="cannot read"):
        gp.read_gp(unreadable, (8, 8))
    for shape in ((4, 16), (16, 4)):  # short in one dimension only
        small = tmp_path / f"small_{shape[0]}.png"
        cv2.imwrite(str(small), np.zeros(shape, np.uint8))
        with pytest.raises(SystemExit, match="smaller than the render"):
            gp.read_gp(small, (8, 8))


def _gp_maps_copying_reader_v3(root: Path, v3_maps: Path) -> Path:
    """The model's predictions holding Reader V3's own pixels: standardised, the two readers are then one map."""
    import cv2

    maps = root / "gp_maps"
    maps.mkdir()
    for order, tag in ((gp.READING, "_reverse"), (gp.OTHER, "")):
        raw = cv2.imread(
            str(v3_maps / f"v9_66__reader_v3__L66s26{tag}.tif"), cv2.IMREAD_UNCHANGED
        )
        padded = np.zeros(
            (
                raw.shape[0] + 256 - raw.shape[0] % 256,
                raw.shape[1] + 256 - raw.shape[1] % 256,
            )
        )
        padded[: raw.shape[0], : raw.shape[1]] = raw
        cv2.imwrite(str(gp.gp_file(maps, order)), padded.astype(np.uint8))
    return maps


def _compare_with_alignment(tmp_path, monkeypatch, shift, aligned, name="gp.json"):
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _gp_maps_copying_reader_v3(tmp_path, v3_maps)
    monkeypatch.setattr(
        gp.f118,
        "alignment",
        lambda layers, ct: {"shift_pixels": list(shift), "aligned": aligned},
    )
    out = tmp_path / name
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    assert gp.main(["compare", str(out), *argv]) == 0
    return json.loads(out.read_text())


@pytest.mark.parametrize("shift", [(16, 0), (-16, 0), (0, -16)])
def test_a_shift_at_the_edge_of_the_search_does_not_run(tmp_path, monkeypatch, shift):
    record = _compare_with_alignment(tmp_path, monkeypatch, shift, aligned=False)
    assert record["verdict"] == "DOES_NOT_RUN" and "ensemble" not in record


@pytest.mark.parametrize(
    ("shift", "aligned", "applied"),
    [((0, -1), True, [0, 0]), ((0, -8), False, [0, -8])],
)
def test_the_shift_moves_this_model_and_reader_v3_alike(
    tmp_path, monkeypatch, shift, aligned, applied
):
    record = _compare_with_alignment(tmp_path, monkeypatch, shift, aligned)
    assert record["shift_applied_pixels"] == applied
    # the two maps hold the same pixels, so moved alike they give the same numbers
    ours, v3 = record[gp.NAME], record["described"]["reader_v3"]
    for key in ("r", "control_wrong_side", "overlap"):
        assert ours[key] == pytest.approx(v3[key], abs=2e-4), key


@pytest.mark.parametrize("order", [gp.READING, gp.OTHER])
def test_a_constant_prediction_does_not_run_and_reader_v3_is_still_described(
    tmp_path, order
):
    import cv2

    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    flat = cv2.imread(str(gp.gp_file(gp_maps, order)), cv2.IMREAD_GRAYSCALE)
    cv2.imwrite(str(gp.gp_file(gp_maps, order)), np.full_like(flat, 128))
    out = tmp_path / "gp.json"
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    assert gp.main(["compare", str(out), *argv]) == 0
    record = json.loads(out.read_text())
    assert record[gp.NAME] is None and record["verdict"] == "DOES_NOT_RUN"
    assert set(record["described"]) == {"reader_v3"} and record["ensemble"] is not None


def test_an_unreadable_mask_stops_the_comparison(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    (tmp_path / "mask.png").write_bytes(b"not an image")
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    with pytest.raises(SystemExit, match="cannot read"):
        gp.main(["compare", str(tmp_path / "gp.json"), *argv])


def test_a_winners_cell_exactly_at_the_ink_line_is_ink(tmp_path):
    import tifffile

    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    # the strokes at exactly 0.5 and nothing else: every 4-pixel block of the map is one cell's value
    studio = tmp_path / "studio.tif"
    tifffile.imwrite(
        studio, np.where(tifffile.imread(studio) >= 0.3, 0.5, 0.0).astype(np.float32)
    )
    out = tmp_path / "gp.json"
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    assert gp.main(["compare", str(out), *argv]) == 0
    record = json.loads(out.read_text())
    assert 0 < record["winner_ink_cells"] < record["cells"]
    assert record[gp.NAME]["overlap"] is not None


def test_a_cell_share_exactly_at_the_line_is_measured(tmp_path, monkeypatch):
    args = f118_tests._write_inputs(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    assert gp.main(["compare", str(tmp_path / "first.json"), *argv]) == 0
    first = json.loads((tmp_path / "first.json").read_text())
    monkeypatch.setattr(gp.f118, "MIN_CELL_SHARE", first["cells"] / first["mask_cells"])
    assert gp.main(["compare", str(tmp_path / "again.json"), *argv]) == 0
    again = json.loads((tmp_path / "again.json").read_text())
    assert again["ensemble"] == first["ensemble"] and again[gp.NAME] == first[gp.NAME]


def test_the_described_comparisons_point_the_right_way(tmp_path):
    args = f118_tests._write_inputs(tmp_path)
    f120_tests._weaken_the_ensemble(tmp_path)
    v3_maps = f120_tests._write_v3_maps(tmp_path, 0.5)
    gp_maps = _write_gp_maps(tmp_path, 1.0)
    out = tmp_path / "gp.json"
    argv = [
        *args[: args.index("--image")],
        "--gp-maps",
        str(gp_maps),
        "--v3-maps",
        str(v3_maps),
    ]
    assert gp.main(["compare", str(out), *argv]) == 0
    described = json.loads(out.read_text())["described"]
    # this model draws the strokes far more clearly than the weakened ensemble: its r minus the ensemble's is positive
    assert described["r_difference_bootstrap"]["low"] > 0
    # Reader V3 carries the same strokes cleanly; the weakened ensemble carries them under noise
    assert described["gp_r_with_reader_v3"] > described["gp_r_with_ensemble"]
