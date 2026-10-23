"""The native retry probe behind the prepared villa #1482 fix, and its record.

`repro/ink_native/check_retry_cycle.py` hands villa's `InkDataset` two empty
corners of a published mesh and calls `__getitem__` under a two-second
watchdog. Its before and after records are the evidence for the fix:

- a cycle is a timeout and exits 1;
- a bounded retry is a RuntimeError after exactly the two patches, and exits 0;
- it refuses, with exit 2 and no record, a mesh that is not the published one,
  a corner with surface in it, a patch villa does not reject, a voxel read
  before the geometry rejects the patch, and an existing record. Until
  2026-10-23 a refusal exited 1, like the timeout.

Nothing tested any of it. These tests drive the probe on stand-in villa
modules and a stand-in mesh, so neither villa nor the mesh is needed. The
records, the report and the PR draft are then bound to each other and to the
committed patch.
"""

import ast
import hashlib
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

_REPO = Path(__file__).resolve().parent.parent
_PROBE = _REPO / "repro" / "ink_native" / "check_retry_cycle.py"
_EVIDENCE = _REPO / "reports" / "evidence"
_BEFORE = _EVIDENCE / "villa_native_retry_before_2026-10-23.json"
_AFTER = _EVIDENCE / "villa_native_retry_after_2026-10-23.json"
_TRANSCRIPT = _EVIDENCE / "villa_native_retry_validation_2026-10-23.txt"
_REPORT = _REPO / "reports" / "villa_native_retry_cycle_2026-10-23.md"
_DRAFT = _REPO / "docs" / "VILLA_DRAFT_native_retry_cycle.md"
_PATCH = _REPO / "docs" / "villa_pr_native_retry_cycle.patch"

# villa's native sample: the tifxyz geometry rejects a patch with no surface in
# it before any voxel is read
_NATIVE = """
    def _native_sample(self, patch):
        surface = self._tifxyz_cache[str(patch.segment.segment_dir)]
        _, y0, x0, _, y1, x1 = patch.bbox
        if not surface[y0:y1, x0:x1][3].any():
            return None
        return self._open("image")[0]
"""
_READS_FIRST = """
    def _native_sample(self, patch):
        self._open("image")[0]
"""
# villa's first touch of a volume it reads, in _read_flat_surface
_TOUCHES_SHAPE = """
    def _native_sample(self, patch):
        self._open("supervision").shape
"""
# rejects everything, so only the probe's corner check can stop it
_REJECTS = """
    def _native_sample(self, patch):
        return None
"""
# admits a surface-free patch without reading a voxel: only the probe's own
# pre-check, that both patches are rejected, can stop it
_ADMITS = """
    def _native_sample(self, patch):
        return "sample"
"""
_ADMITS_FIRST = """
    def _native_sample(self, patch):
        return "sample" if patch.bbox[2] == 0 else None
"""
_ADMITS_SECOND = """
    def _native_sample(self, patch):
        return "sample" if patch.bbox[2] > 0 else None
"""
# rejects both patches while the probe checks them, then reads a voxel in the
# retry itself: a refusal, not a retry failure
_READS_IN_RETRY = """
    def _native_sample(self, patch):
        self.calls = getattr(self, "calls", 0) + 1
        if self.calls > 2:
            self._open("image")[0]
"""
# villa before the fix: every rejection picks another patch, with no memory
_CYCLE = """
        current = index
        while True:
            if self._native_sample(self.patches[current]) is not None:
                return "sample"
            rng = random.Random(self.config.seed + current * 7919)
            replacement = current
            while replacement == current:
                replacement = rng.randrange(len(self.patches))
            current = replacement
"""
# after: each patch at most once, then a RuntimeError naming the attempts
_BOUNDED = """
        current, attempted = index, set()
        while True:
            attempted.add(current % len(self.patches))
            if self._native_sample(self.patches[current]) is not None:
                return "sample"
            if len(attempted) >= len(self.patches):
                raise RuntimeError(f"after trying {len(attempted)} distinct patches")
            current = (current + 1) % len(self.patches)
"""
_RETURNS = """
        self._native_sample(self.patches[index])
        return "sample"
"""
_GIVES_UP_EARLY = """
        self._native_sample(self.patches[index])
        raise RuntimeError("gave up after one patch")
"""
_SAME_PATCH_TWICE = """
        self._native_sample(self.patches[index])
        self._native_sample(self.patches[index])
        raise RuntimeError("after trying 2 distinct patches")
"""
# a fix that counts attempts but does not remember them: the cycle, then a stop
_COUNTS_NOT_DISTINCT = """
        current = index
        for _ in range(6):
            self._native_sample(self.patches[current])
            current = (current + 1) % len(self.patches)
        raise RuntimeError("after trying 6 patches")
"""
_BOTH_THEN_RETURNS = """
        for patch in self.patches:
            self._native_sample(patch)
        return "sample"
"""
_BOTH_THEN_OTHER_ERROR = """
        for patch in self.patches:
            self._native_sample(patch)
        raise ValueError("not a retry failure")
"""
_DATASET = """
import json, os, random


class InkDataset:
    def __init__(self, config, do_augmentations, patches):
        self.config, self.patches, self._tifxyz_cache = config, list(patches), {{}}
        with open(os.environ["STANDIN_RECORD"], "w") as stream:
            json.dump({{
                "mapping": config.mapping,
                "do_augmentations": do_augmentations,
                "bboxes": [list(p.bbox) for p in self.patches],
                "segments": [str(p.segment.segment_dir) for p in self.patches],
                "segment": {{
                    k: str(v) for k, v in vars(self.patches[0].segment).items()
                    if k not in ("data_config", "source")
                }},
                "segment_config_is_config": self.patches[0].segment.data_config is config,
                "segment_source_is_dataset": (
                    self.patches[0].segment.source is config.datasets[0]
                ),
            }}, stream)

    def _open(self, *args):
        return {{}}
{native}
    def __getitem__(self, index):
{retry}
"""
_CONFIG = """
class _Source:
    def __init__(self, mapping):
        self.__dict__.update(mapping)


class InkDataConfig:
    @classmethod
    def from_mapping(cls, mapping):
        config = cls()
        config.mapping, config.seed = mapping, mapping["seed"]
        config.datasets = [_Source(d) for d in mapping["datasets"]]
        return config
"""
_TYPES = """
class Patch:
    def __init__(self, segment, bbox):
        self.segment, self.bbox = segment, bbox


class Segment:
    def __init__(self, **fields):
        self.__dict__.update(fields)
"""
# the stored grid is half resolution, so reading the shape before
# use_full_resolution() would put the second corner in the wrong place
_TIFXYZ = """
import json
from pathlib import Path

import numpy as np


class _Surface:
    def __init__(self, valid):
        self._valid, self._full = valid, False

    def use_full_resolution(self):
        self._full = True

    @property
    def shape(self):
        h, w = self._valid.shape
        return (h, w) if self._full else (h // 2, w // 2)

    def __getitem__(self, key):
        valid = self._valid[key]
        return (valid * 0.0, valid * 0.0, valid * 0.0, valid)


def read_tifxyz(path):
    meta = json.loads((Path(path) / "meta.json").read_text())
    valid = np.zeros(meta["shape"], bool)
    for y0, y1, x0, x1 in meta["valid"]:
        valid[y0:y1, x0:x1] = True
    return _Surface(valid)
"""
_RUN = """
import importlib.util, json, os, signal, sys

if os.environ.get("STANDIN_NO_TIMER"):
    del signal.setitimer
spec = importlib.util.spec_from_file_location("check_retry_cycle", sys.argv[1])
probe = importlib.util.module_from_spec(spec)
spec.loader.exec_module(probe)
if sys.argv[2] != "published":
    probe.HASHES = json.loads(sys.argv[2])
sys.argv = [sys.argv[1]] + sys.argv[3:]
raise SystemExit(probe.main())
"""
_SHAPE = (256, 320)


def _villa(root, retry, native=_NATIVE):
    # module paths without a literal "name.py": the suite guard reads a bare
    # script name as a file under scripts/, and "config.py" is the loop's
    pkg = root / "villa" / "vesuvius"
    modules = {
        "__init__": "",
        "ink_detection/__init__": "",
        "ink_detection/data/__init__": "",
        "ink_detection/config": _CONFIG,
        "ink_detection/types": _TYPES,
        "tifxyz": _TIFXYZ,
        "ink_detection/data/dataset": _DATASET.format(native=native, retry=retry),
    }
    for name, code in modules.items():
        path = (pkg / name).with_suffix(".py")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(code)
    return (pkg / "ink_detection" / "data" / "dataset").with_suffix(".py")


def _mesh(root, valid=((100, 200, 100, 200),)):
    mesh = root / "segments" / "mesh"
    mesh.mkdir(parents=True)
    (mesh / "meta.json").write_text(json.dumps({"shape": _SHAPE, "valid": valid}))
    for axis in "xyz":
        (mesh / f"{axis}.tif").write_bytes(f"stand-in {axis} grid".encode())
    names = ("meta.json", "x.tif", "y.tif", "z.tif")
    return mesh, {n: hashlib.sha256((mesh / n).read_bytes()).hexdigest() for n in names}


def _probe(
    tmp_path,
    retry,
    native=_NATIVE,
    valid=((100, 200, 100, 200),),
    hashes=None,
    out=None,
    missing=None,
    env=(),
):
    dataset = _villa(tmp_path, retry, native)
    mesh, own = _mesh(tmp_path, valid)
    if missing:
        (mesh / missing).unlink()
    out = out or tmp_path / "probe.json"
    kept = os.path.lexists(out)
    record = tmp_path / "constructed.json"
    runner = tmp_path / "run.py"
    runner.write_text(_RUN)
    proc = subprocess.run(
        [
            sys.executable,
            str(runner),
            str(_PROBE),
            hashes or json.dumps(own),
            "--mesh",
            str(mesh),
            "--out",
            str(out),
        ],
        env={
            "PYTHONPATH": str(tmp_path / "villa"),
            "STANDIN_RECORD": str(record),
            "PATH": "/usr/bin:/bin",
            **dict(env),
        },
        capture_output=True,
        text=True,
        timeout=60,
    )
    written = json.loads(out.read_text()) if out.exists() and not kept else None
    built = json.loads(record.read_text()) if record.exists() else None
    return proc, written, built, own, dataset, mesh


def test_a_retry_cycle_is_a_timeout_and_exits_1(tmp_path):
    proc, rec, _, own, dataset, _ = _probe(tmp_path, _CYCLE)
    assert proc.returncode == 1, proc.stderr
    assert rec["outcome"] == "timeout" and rec["bounded"] is False
    assert rec["message"] == "retry did not terminate within two seconds"
    # two rejected patches alternate until the two-second watchdog
    assert rec["first_attempts"] == [0, 1] * 4 and rec["attempt_count"] > 8
    assert 2.0 <= rec["seconds"] < 5.0
    assert rec["input_sha256"] == own
    before = json.loads(_BEFORE.read_text())
    assert (rec["scope"], rec["source_url"]) == (before["scope"], before["source_url"])
    assert (
        rec["dataset_source_sha256"] == hashlib.sha256(dataset.read_bytes()).hexdigest()
    )


def test_a_bounded_retry_is_a_runtime_error_after_both_patches(tmp_path):
    proc, rec, built, _, _, mesh = _probe(tmp_path, _BOUNDED)
    assert proc.returncode == 0, proc.stderr
    assert rec["outcome"] == "runtime_error" and rec["bounded"] is True
    assert rec["message"] == "after trying 2 distinct patches"
    assert rec["first_attempts"] == [0, 1] and rec["attempt_count"] == 2
    # the corners come from the full-resolution grid
    h, w = _SHAPE
    assert rec["mesh_shape"] == [h, w] and rec["corners_yx"] == [[0, 0], [0, w - 64]]
    # what it hands villa: the top-left and top-right 64x64 regions, native
    # 3D, no augmentation, the mesh's own directory as the segment
    assert built["bboxes"] == [[0, 0, 0, 17, 64, 64], [0, 0, w - 64, 17, 64, w]]
    assert built["do_augmentations"] is False
    assert built["segments"] == [str(mesh)] * 2
    # volume_scale 0 is the full-resolution grid the report describes; the
    # volume and label paths are never opened, because _open is the sentinel
    assert built["mapping"] == {
        "mode": "full_3d",
        "patch_size": [17, 64, 64],
        "patch_overlap": 0.25,
        "patch_min_labeled_coverage": 0.0,
        "seed": 17,
        "datasets": [
            {
                "segments_path": str(mesh.parent),
                "volume_path": "unused-volume",
                "volume_scale": 0,
            }
        ],
    }
    assert built["segment"] == {
        "dataset_idx": "0",
        "segment_relpath": "mesh",
        "segment_dir": str(mesh),
        "segment_name": "mesh",
        "image_volume": "unused-volume",
        "inklabels": "unused-labels",
        "supervision_mask": "unused-supervision",
    }
    assert built["segment_config_is_config"] and built["segment_source_is_dataset"]


@pytest.mark.parametrize(
    "retry",
    [
        _RETURNS,
        _GIVES_UP_EARLY,
        _SAME_PATCH_TWICE,
        _COUNTS_NOT_DISTINCT,
        _BOTH_THEN_RETURNS,
    ],
    ids=[
        "returns",
        "one-patch",
        "same-patch-twice",
        "counts-not-distinct",
        "both-then-returns",
    ],
)
def test_anything_else_is_not_bounded(tmp_path, retry):
    proc, rec, _, _, _, _ = _probe(tmp_path, retry)
    assert proc.returncode == 1, proc.stderr
    assert rec["bounded"] is False


def test_an_error_that_is_not_the_retry_failure_is_not_classified(tmp_path):
    proc, rec, _, _, _, _ = _probe(tmp_path, _BOTH_THEN_OTHER_ERROR)
    assert proc.returncode == 1 and "ValueError: not a retry failure" in proc.stderr
    assert rec is None


def _refused(proc, rec, why):
    """A refusal exits 2, says why, and writes nothing."""
    assert proc.returncode == 2, proc.stderr
    assert f"refused: {why}" in proc.stderr and "Traceback" not in proc.stderr
    assert rec is None


def test_a_mesh_that_is_not_the_published_one_is_refused(tmp_path):
    proc, rec, _, _, _, _ = _probe(tmp_path, _BOUNDED, hashes="published")
    _refused(proc, rec, "meta.json: not the stated published Scroll-1 mesh")


@pytest.mark.parametrize("name", ["meta.json", "x.tif", "y.tif", "z.tif"])
def test_each_mesh_file_is_hashed(tmp_path, name):
    _, own = _mesh(tmp_path / "hashes")
    proc, rec, _, _, _, _ = _probe(
        tmp_path, _BOUNDED, hashes=json.dumps({**own, name: "0" * 64})
    )
    _refused(proc, rec, f"{name}: not the stated published Scroll-1 mesh")


@pytest.mark.parametrize("corner", ["top-left", "top-right"])
def test_a_corner_with_surface_in_it_is_refused(tmp_path, corner):
    w = _SHAPE[1]
    surface = (0, 8, 0, 8) if corner == "top-left" else (0, 8, w - 8, w)
    x = 0 if corner == "top-left" else w - 64
    proc, rec, _, _, _, _ = _probe(
        tmp_path, _BOUNDED, native=_REJECTS, valid=(surface,)
    )
    _refused(proc, rec, f"the 64x64 region at y=0, x={x} has surface")


@pytest.mark.parametrize(
    "admits", [_ADMITS, _ADMITS_FIRST, _ADMITS_SECOND], ids=["both", "first", "second"]
)
def test_a_patch_villa_does_not_reject_is_refused(tmp_path, admits):
    proc, rec, _, _, _, _ = _probe(tmp_path, _BOUNDED, native=admits)
    _refused(proc, rec, "villa admits a supplied patch")


def test_a_voxel_read_in_the_retry_is_a_refusal_not_a_retry_failure(tmp_path):
    proc, rec, _, _, _, _ = _probe(tmp_path, _CYCLE, native=_READS_IN_RETRY)
    _refused(proc, rec, "The geometry rejection must precede voxel reads")


def test_a_missing_mesh_file_is_refused(tmp_path):
    proc, rec, _, _, _, mesh = _probe(tmp_path, _BOUNDED, missing="z.tif")
    _refused(proc, rec, f"z.tif: missing from {mesh}")


def test_no_posix_timer_is_refused(tmp_path):
    proc, rec, _, _, _, _ = _probe(tmp_path, _BOUNDED, env={"STANDIN_NO_TIMER": "1"})
    _refused(proc, rec, "This bounded probe requires a POSIX interval timer")


def test_an_output_with_no_directory_is_refused_before_the_run(tmp_path):
    # with villa's cycle, a late failure would cost the whole two seconds first
    out = tmp_path / "absent" / "probe.json"
    proc, rec, built, _, _, _ = _probe(tmp_path, _CYCLE, out=out)
    _refused(proc, rec, f"{out.parent} is not a directory")
    assert built is None


@pytest.mark.parametrize(
    "touch", [_READS_FIRST, _TOUCHES_SHAPE], ids=["index", "shape"]
)
def test_a_voxel_read_before_the_rejection_is_refused(tmp_path, touch):
    proc, rec, _, _, _, _ = _probe(tmp_path, _BOUNDED, native=touch)
    _refused(proc, rec, "The geometry rejection must precede voxel reads")


def test_a_dangling_symlink_at_the_output_is_refused(tmp_path):
    out = tmp_path / "probe.json"
    out.symlink_to(tmp_path / "nowhere.json")
    proc, _, built, _, _, _ = _probe(tmp_path, _BOUNDED)
    _refused(proc, None, f"{out} exists; records are never overwritten")
    assert built is None and not (tmp_path / "nowhere.json").exists()


def test_a_record_is_never_overwritten(tmp_path):
    (tmp_path / "probe.json").write_text("kept\n")
    proc, _, built, _, _, _ = _probe(tmp_path, _BOUNDED)
    out = tmp_path / "probe.json"
    _refused(proc, None, f"{out} exists; records are never overwritten")
    assert (tmp_path / "probe.json").read_text() == "kept\n"
    # it refuses before it builds anything, not after a run
    assert built is None


# --- the committed records, report and draft -------------------------------


def _records():
    return json.loads(_BEFORE.read_text()), json.loads(_AFTER.read_text())


def _flat(path):
    return " ".join(path.read_text().split())


def _probe_constants():
    tree = ast.parse(_PROBE.read_text())
    hashes = next(
        ast.literal_eval(n.value)
        for n in tree.body
        if isinstance(n, ast.Assign) and n.targets[0].id == "HASHES"
    )
    url = next(
        k.value.value
        for n in ast.walk(tree)
        if isinstance(n, ast.Call)
        for k in n.keywords
        if k.arg == "source_url"
    )
    return hashes, url


def _patch_files():
    chunks = _PATCH.read_text().split("diff --git ")[1:]
    return {c.split()[0][2:]: c.split("\n@@", 1)[1].splitlines() for c in chunks}


def _added(lines):
    return [x[1:] for x in lines if x.startswith("+") and not x.startswith("+++")]


def _new_test_cases():
    """Test cases in the patch's new test file, each parametrization counted."""
    lines = next(v for k, v in _patch_files().items() if "/tests/" in k)
    tree = ast.parse("\n".join(_added(lines)))
    cases = {}
    for f in tree.body:
        if isinstance(f, ast.FunctionDef) and f.name.startswith("test_"):
            n = 1
            for d in f.decorator_list:
                if (
                    isinstance(d, ast.Call)
                    and getattr(d.func, "attr", "") == "parametrize"
                ):
                    n *= len(d.args[1].elts)
            cases[f.name] = n
    return cases


def test_both_records_are_the_probe_on_the_published_mesh():
    hashes, url = _probe_constants()
    before, after = _records()
    for rec in (before, after):
        assert rec["input_sha256"] == hashes and rec["source_url"] == url
        h, w = rec["mesh_shape"]
        assert rec["corners_yx"] == [[0, 0], [0, w - 64]]
    # the same probe on two versions of villa's dataset module
    assert before["dataset_source_sha256"] != after["dataset_source_sha256"]
    assert before["outcome"] == "timeout" and not before["bounded"]
    assert before["first_attempts"] == [0, 1] * 4
    assert after["outcome"] == "runtime_error" and after["bounded"]
    assert after["first_attempts"] == [0, 1] and after["attempt_count"] == 2


def test_the_bounded_error_is_the_patchs_own_message():
    lines = next(v for k, v in _patch_files().items() if k.endswith("dataset.py"))
    body = "\n".join(_added(lines))
    raise_block = body.split("raise RuntimeError(", 1)[1].split("\n)", 1)[0]
    pieces = re.findall(r'^\s*f?"(.*)"\s*$', raise_block, re.M)
    _, after = _records()
    n = after["attempt_count"]
    expected = (
        "".join(pieces)
        .replace("{len(attempted)}", str(n))
        .replace("{requested_index}", "0")
        .replace("{len(self.patches)}", str(len(after["corners_yx"])))
    )
    assert after["message"] == expected


def test_the_report_and_draft_state_the_records():
    before, after = _records()
    report, draft = _flat(_REPORT), _flat(_DRAFT)
    assert (
        f"{before['attempt_count']:,} attempts; watchdog after {before['seconds']:.3f} s"
        in report
    )
    assert f"{after['attempt_count']} attempts; clear RuntimeError" in report
    assert (
        f"{before['attempt_count']:,} attempts before the two-second watchdog" in draft
    )
    h, w = before["mesh_shape"]
    assert f"Its full-resolution grid is {h:,} by {w:,}." in report
    # the download command fetches what the probe hashes
    assert f'"{before["source_url"]}$name"' in report


def test_the_patch_size_and_test_counts_are_the_patch_and_transcript():
    files = _patch_files()
    production = next(v for k, v in files.items() if k.endswith("dataset.py"))
    plus = len(_added(production))
    minus = sum(x.startswith("-") and not x.startswith("---") for x in production)
    assert minus == 0
    report, draft = _flat(_REPORT), _flat(_DRAFT)
    assert f"The production change is +{plus} lines." in report
    assert f"Production change: +{plus} lines in `data/dataset.py`" in draft
    budget = re.search(
        r"MAX_NATIVE_RESAMPLE_ATTEMPTS = (\d+)", "\n".join(_added(production))
    )
    assert f"`min(dataset size, {budget[1]})`" in report
    assert f"up to {budget[1]} distinct patches" in draft
    assert f"The {budget[1]}-attempt budget follows #1921" in draft

    cases = _new_test_cases()
    words = {4: "four", 5: "five", 9: "nine", 13: "13"}
    new = sum(cases.values())
    assert f"The {words[new]} new test cases cover" in report
    assert f"{words[new].capitalize()} regression cases pass" in draft

    transcript = _TRANSCRIPT.read_text()
    baseline = transcript.split("final-tests.txt", 1)[0]
    failed = re.findall(r"^FAILED \S+::(test_\w+)", baseline, re.M)
    passed = int(re.search(r"(\d+) failed, (\d+) passed", baseline)[2])
    # every baseline failure is one of the new cases; the rest passed
    assert set(failed) <= set(cases) and len(failed) + passed == new
    assert (
        f"| Nine new retry cases | {len(failed)} failed, {passed} passed | {new} passed |"
        in report
    )
    assert f"On main, {words[len(failed)]} fail and {words[passed]} pass" in draft

    final = re.search(r"(\d+) passed, (\d+) deselected", transcript)
    total, deselected = int(final[1]), int(final[2])
    existing = total - new
    assert f"| {existing} passed, {deselected} deselected |" in report
    assert f"all **{total} selected cases, {deselected} deselected**" in report
    assert (
        f"{words[existing].capitalize()} existing native-data cases also pass" in draft
    )

    smoke = re.search(
        r"--- (\d+)/(\d+) passed, (\d+) skipped, (\d+) failed in ([\d.]+)s ---",
        transcript,
    )
    assert (
        f"**{smoke[1]}/{smoke[2]} passed, {smoke[3]} skipped, {smoke[4]} failed in {smoke[5]} s**"
        in report
    )
