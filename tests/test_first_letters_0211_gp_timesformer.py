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


def test_a_legacy_checkpoint_is_audited_past_its_first_pickle(tmp_path):
    torch = pytest.importorskip("torch")
    path = tmp_path / "legacy.pt"
    made = tmp_path / "made"
    payload = f120_tests._MakesADirectory(str(made))
    torch.save(
        {"w": torch.zeros(2), "x": payload}, path, _use_new_zipfile_serialization=False
    )
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert any(name.endswith("makedirs") for name in result["outside_allowlist"])
    assert not made.exists()


def test_a_legacy_checkpoint_of_tensors_passes(tmp_path):
    torch = pytest.importorskip("torch")
    path = tmp_path / "legacy.pt"
    torch.save({"w": torch.zeros(2)}, path, _use_new_zipfile_serialization=False)
    result = audit.audit(path, set())
    assert result["passes"] is True
    assert "torch._utils._rebuild_tensor_v2" in result["pickles"][path.name]


def test_a_pickle_placed_before_a_zip_archive_is_audited(tmp_path):
    torch = pytest.importorskip("torch")
    import io

    archive = io.BytesIO()
    torch.save({"w": torch.zeros(2)}, archive)
    made = tmp_path / "made"
    payload = f120_tests._MakesADirectory(str(made))
    path = tmp_path / "joined.pt"
    path.write_bytes(pickle.dumps(payload, protocol=2) + archive.getvalue())
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert any(name.endswith("makedirs") for name in result["outside_allowlist"])
    assert not made.exists()


def _write_tar(path: Path, members: list[tuple[str, bytes]]) -> None:
    import io
    import tarfile

    with tarfile.open(path, "w:", format=tarfile.PAX_FORMAT) as archive:
        for name, data in members:
            info = tarfile.TarInfo(name)
            info.size = len(data)
            archive.addfile(info, io.BytesIO(data))


def test_a_malicious_tar_legacy_checkpoint_is_refused(tmp_path):
    # torch.load tries a tar before the concatenated legacy pickles, and unpickles
    # the member. A header that parses as a few harmless opcodes used to end the
    # audit early (passes=True); a member named "pickle" used to raise.
    payload = pickle.dumps(os.system, protocol=2)
    for name in ("storages", "pickle"):
        path = tmp_path / f"{name}.pt"
        _write_tar(path, [(name, payload)])
        result = audit.audit(path, set())
        assert result["passes"] is False, name
        assert "posix.system" in result["outside_allowlist"], name
        assert audit.main([str(path)]) == 1


def test_a_benign_tar_checkpoint_passes(tmp_path):
    path = tmp_path / "benign.pt"
    _write_tar(
        path,
        [
            ("pickle", pickle.dumps({"w": 1}, protocol=2)),
            ("storages", pickle.dumps(0, protocol=2)),
        ],
    )
    result = audit.audit(path, set())
    assert result["passes"] is True, result
    assert result["outside_allowlist"] == [] and result["refused_opcodes"] == []
    # Bytes after a tar pickle are not the legacy storage tail: torch.load reads
    # another pickle there. A member that does not end on STOP is refused.
    tail = tmp_path / "tail.pt"
    _write_tar(
        tail,
        [("storages", pickle.dumps({"w": 1}, protocol=2) + b"\x00\x00")],
    )
    refused = audit.audit(tail, set())
    assert refused["passes"] is False
    assert "unreadable pickle" in refused["refused_opcodes"]


def test_a_truncated_pickle_fails_closed(tmp_path):
    # PROTO, then a string opcode whose length runs past the buffer. The opcodes
    # already read name nothing; the unread tail must not be dropped as storage.
    path = tmp_path / "cut.pkl"
    path.write_bytes(b"\x80\x04\x8c\x05os" + pickle.dumps(os.system, protocol=2))
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "unreadable pickle" in result["refused_opcodes"]
    assert audit.main([str(path)]) == 1

    # A failure on the first byte is the same refusal, not a traceback.
    blank = tmp_path / "blank.pkl"
    blank.write_bytes(b"\xff\xff")
    refused = audit.audit(blank, set())
    assert refused["passes"] is False
    assert "unreadable pickle" in refused["refused_opcodes"]


def test_an_empty_checkpoint_does_not_pass(tmp_path):
    path = tmp_path / "empty.pt"
    path.write_bytes(b"")
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert result["refused_opcodes"] == ["no pickle"]
    assert audit.main([str(path)]) == 1


def test_legacy_checkpoints_pass_across_tensor_sizes(tmp_path):
    # Storage after the last STOP can look like an opcode. That is not a pickle
    # torch.load runs, so none of these sizes is a reason to refuse the file.
    torch = pytest.importorskip("torch")
    refused = []
    for n in range(256):
        path = tmp_path / f"{n}.pt"
        torch.save(torch.zeros(n), path, _use_new_zipfile_serialization=False)
        if not audit.audit(path, set())["passes"]:
            refused.append(n)
    assert refused == []


def _makedirs_name(marker: str) -> str:
    """A NUL-free protocol-0 pickle, short enough to be a tar member name."""
    text = f"cos\nmakedirs\n(S'{marker}'\ntR."
    assert "\x00" not in text and len(text) <= 100
    return text


def test_a_pickle_in_a_tar_name_is_refused_and_bytesio_runs_it(tmp_path):
    # The member body is a benign pickle, so the tar reading alone would pass.
    # torch.load of a real file opens the tar. torch.load of a BytesIO never
    # does: it unpickles the leading bytes, which are the member name.
    torch = pytest.importorskip("torch")
    import io
    import tarfile

    marker = Path("/tmp") / f"m{os.getpid()}"
    if marker.exists():
        marker.rmdir()
    benign = pickle.dumps({"w": 1}, protocol=2)
    path = tmp_path / "named.tar"
    with tarfile.open(path, "w:", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo(_makedirs_name(str(marker)))
        info.size = len(benign)
        archive.addfile(info, io.BytesIO(benign))
    assert tarfile.is_tarfile(path)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "os.makedirs" in result["outside_allowlist"]
    assert not marker.exists()
    try:
        with pytest.raises(RuntimeError):
            torch.load(io.BytesIO(path.read_bytes()), weights_only=False)
        assert marker.exists()
    finally:
        if marker.exists():
            marker.rmdir()


def test_a_link_or_device_member_refuses_the_tar(tmp_path):
    import io
    import tarfile

    benign = pickle.dumps(0, protocol=2)

    def build(kind: bytes, link: str | None) -> Path:
        path = tmp_path / f"{kind.decode()}.tar"
        with tarfile.open(path, "w:", format=tarfile.PAX_FORMAT) as archive:
            info = tarfile.TarInfo("pickle")
            info.size = len(benign)
            archive.addfile(info, io.BytesIO(benign))
            extra = tarfile.TarInfo("other")
            extra.type = kind
            if link is not None:
                extra.linkname = link
            else:
                extra.devmajor = 1
                extra.devminor = 3
            archive.addfile(extra)
        return path

    for kind, link in (
        (tarfile.SYMTYPE, "pickle"),
        (tarfile.LNKTYPE, "pickle"),
        (tarfile.CHRTYPE, None),
    ):
        result = audit.audit(build(kind, link), set())
        assert result["passes"] is False, kind
        assert "unreadable tar" in result["refused_opcodes"]


def test_an_unreadable_tar_is_refused(tmp_path):
    import gzip
    import tarfile

    raw = tmp_path / "plain.tar"
    _write_tar(raw, [("pickle", pickle.dumps(0, protocol=2))])
    path = tmp_path / "plain.tar.gz"
    path.write_bytes(gzip.compress(raw.read_bytes()))
    assert tarfile.is_tarfile(path)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "unreadable tar" in result["refused_opcodes"]


def _legacy_prefix() -> bytes:
    """The three pickles torch.load finishes before it unpickles the object."""
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
    """A protocol-0 call with no STOP. pickle.load runs it, then raises."""
    text = f"c{module}\n{name}\n(S'{arg}'\ntR"
    assert "\x00" not in text
    return text.encode()


def test_a_magic_pickle_then_a_stopless_import_is_refused(tmp_path):
    # One finished pickle used to end the scan, so this file passed. torch.load
    # still runs the second pickle, and a tar name is the same bytes.
    torch = pytest.importorskip("torch")
    import io
    import tarfile

    from torch.serialization import MAGIC_NUMBER

    marker = Path("/tmp") / f"s{os.getpid()}"
    if marker.exists():
        marker.unlink()
    payload = pickle.dumps(MAGIC_NUMBER, protocol=0) + _stopless(
        "os", "system", f"touch {marker}"
    )
    path = tmp_path / "magic.pkl"
    path.write_bytes(payload)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "os.system" in result["outside_allowlist"]
    assert not marker.exists()
    try:
        with pytest.raises(EOFError):
            torch.load(path, weights_only=False)
        assert marker.exists()
    finally:
        if marker.exists():
            marker.unlink()

    named = Path("/tmp") / f"t{os.getpid()}"
    if named.exists():
        named.unlink()
    name = (
        pickle.dumps(MAGIC_NUMBER, protocol=0)
        + _stopless("os", "system", f"touch {named}")
    ).decode()
    assert len(name) <= 100
    benign = pickle.dumps(0, protocol=2)
    tar_path = tmp_path / "named.tar"
    with tarfile.open(tar_path, "w:", format=tarfile.PAX_FORMAT) as archive:
        info = tarfile.TarInfo(name)
        info.size = len(benign)
        archive.addfile(info, io.BytesIO(benign))
    assert tarfile.is_tarfile(tar_path)
    named_result = audit.audit(tar_path, set())
    assert named_result["passes"] is False
    assert "os.system" in named_result["outside_allowlist"]
    assert not named.exists()
    try:
        with pytest.raises(pickle.UnpicklingError):
            torch.load(io.BytesIO(tar_path.read_bytes()), weights_only=False)
        assert named.exists()
    finally:
        if named.exists():
            named.unlink()


def test_a_legacy_header_then_a_stopless_makedirs_is_refused(tmp_path):
    # magic, protocol, sys_info, then the object. torch.load runs that fourth
    # pickle from a path and from a BytesIO, STOP or not.
    torch = pytest.importorskip("torch")
    import io

    marker = tmp_path / "made"
    payload = _legacy_prefix() + _stopless("os", "makedirs", str(marker))
    path = tmp_path / "shaped.pkl"
    path.write_bytes(payload)
    result = audit.audit(path, set())
    assert result["passes"] is False
    assert "os.makedirs" in result["outside_allowlist"]
    assert not marker.exists()
    try:
        with pytest.raises(EOFError):
            torch.load(path, weights_only=False)
        assert marker.is_dir()
        marker.rmdir()
        with pytest.raises(EOFError):
            torch.load(io.BytesIO(payload), weights_only=False)
        assert marker.is_dir()
    finally:
        if marker.exists():
            marker.rmdir()


def test_a_tar_past_the_member_or_size_cap_is_refused(tmp_path):
    import tarfile

    tiny = pickle.dumps(0, protocol=2)
    crowded = tmp_path / "crowded.tar"
    _write_tar(crowded, [(f"p{i}", tiny) for i in range(audit._MAX_TAR_MEMBERS + 1)])
    result = audit.audit(crowded, set())
    assert result["passes"] is False
    assert "unreadable tar" in result["refused_opcodes"]

    huge = tmp_path / "huge.tar"
    _write_tar(huge, [("pickle", tiny)])
    header = bytearray(huge.read_bytes()[:512])
    header[124:136] = f"{audit._MAX_TAR_BYTES + 1:011o}\0".encode()
    header[148:156] = b"        "
    header[148:156] = f"{sum(header):06o}\0 ".encode()
    patched = tmp_path / "patched.tar"
    patched.write_bytes(bytes(header) + huge.read_bytes()[512:])
    assert tarfile.is_tarfile(patched)
    refused = audit.audit(patched, set())
    assert refused["passes"] is False
    assert "unreadable tar" in refused["refused_opcodes"]


def test_a_tar_at_the_member_and_byte_caps_is_allowed(tmp_path, monkeypatch):
    # Equality is inside the cap. One past it is not. Directories count, so a
    # directory on top of a full archive is already over.
    import io
    import tarfile

    tiny = pickle.dumps(0, protocol=2)
    full = tmp_path / "full.tar"
    _write_tar(full, [(f"p{i}", tiny) for i in range(audit._MAX_TAR_MEMBERS)])
    assert audit.audit(full, set())["passes"] is True

    crowded = tmp_path / "dirs.tar"
    with tarfile.open(crowded, "w:", format=tarfile.PAX_FORMAT) as archive:
        for i in range(audit._MAX_TAR_MEMBERS):
            directory = tarfile.TarInfo(f"d{i}")
            directory.type = tarfile.DIRTYPE
            archive.addfile(directory)
        info = tarfile.TarInfo("pickle")
        info.size = len(tiny)
        archive.addfile(info, io.BytesIO(tiny))
    directories = audit.audit(crowded, set())
    assert directories["passes"] is False
    assert "unreadable tar" in directories["refused_opcodes"]

    assert audit._MAX_TAR_BYTES == 512 * 1024 * 1024
    payload = pickle.dumps({"w": 1}, protocol=2)
    exact = tmp_path / "exact.tar"
    _write_tar(exact, [("pickle", payload)])
    monkeypatch.setattr(audit, "_MAX_TAR_BYTES", len(payload))
    assert audit.audit(exact, set())["passes"] is True
    monkeypatch.setattr(audit, "_MAX_TAR_BYTES", len(payload) - 1)
    over = audit.audit(exact, set())
    assert over["passes"] is False
    assert "unreadable tar" in over["refused_opcodes"]


def test_a_tar_leading_pickle_does_not_read_the_member_bodies(tmp_path, monkeypatch):
    import io

    path = tmp_path / "wide.tar"
    _write_tar(path, [("pickle", pickle.dumps({"w": 1}, protocol=2))])
    blob = path.read_bytes() + b"\0" * (audit._MAX_LEADING_BYTES + 32)
    path.write_bytes(blob)
    requests = []

    class _Spy(io.BytesIO):
        def read(self, size=-1):
            requests.append(size)
            return super().read(size)

    original = Path.open

    def fake_open(self, mode="r", *args, **kwargs):
        if self == path and "b" in mode:
            return _Spy(blob)
        return original(self, mode, *args, **kwargs)

    monkeypatch.setattr(Path, "open", fake_open)
    result = audit.audit(path, set())
    assert result["passes"] is True
    assert requests
    assert all(
        isinstance(size, int) and 0 <= size <= audit._MAX_LEADING_BYTES
        for size in requests
    )


def test_nested_gzip_and_zip_members_and_a_tar_shaped_pickle(tmp_path):
    # These already fail closed. The tests hold that: a nested tar, a gzip tar,
    # a data.pkl that is really a zip, and a pickle wearing a tar header.
    torch = pytest.importorskip("torch")
    import gzip
    import io
    import tarfile

    nested = tmp_path / "nested.tar"
    inner = tmp_path / "inner.tar"
    _write_tar(inner, [("pickle", pickle.dumps({"w": 1}, protocol=2))])
    _write_tar(nested, [("pickle", inner.read_bytes())])
    assert audit.audit(nested, set())["passes"] is False

    gzipped = tmp_path / "wrapped.tar.gz"
    gzipped.write_bytes(gzip.compress(inner.read_bytes()))
    assert tarfile.is_tarfile(gzipped)
    assert audit.audit(gzipped, set())["passes"] is False

    archive = io.BytesIO()
    torch.save({"w": torch.zeros(1)}, archive)
    zipped = tmp_path / "member.tar"
    _write_tar(zipped, [("data.pkl", archive.getvalue())])
    assert audit.audit(zipped, set())["passes"] is False

    marker = Path("/tmp") / f"n{os.getpid()}"
    if marker.exists():
        marker.rmdir()
    shaped = tmp_path / "shaped.tar"
    body = pickle.dumps(0, protocol=2)
    with tarfile.open(shaped, "w:", format=tarfile.PAX_FORMAT) as tar:
        info = tarfile.TarInfo(_makedirs_name(str(marker)))
        info.size = len(body)
        tar.addfile(info, io.BytesIO(body))
    assert tarfile.is_tarfile(shaped)
    try:
        assert audit.audit(shaped, set())["passes"] is False
        assert not marker.exists()
    finally:
        if marker.exists():
            marker.rmdir()


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
