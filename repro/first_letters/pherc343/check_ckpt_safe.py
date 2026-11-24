"""Check restricted CPU loading; refuse empty input and report failures via exit status.

A successful check is not a general safety certification or a persisted receipt.
"""

import importlib.util
import sys
from pathlib import Path


def _length_or_value(value):
    """Scalar tensors expose __len__ but raise TypeError when it is called."""
    try:
        return len(value)
    except TypeError:
        return value


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print("usage: check_ckpt_safe.py CHECKPOINT [CHECKPOINT ...]", file=sys.stderr)
        return 2

    import torch

    # python -I drops PYTHONPATH, and the portable CI venv does not install this
    # package. The gate is this checkout's file, loaded by path: a regular
    # vesuvius_autoresearch package elsewhere on sys.path would otherwise win
    # over a namespace portion inserted into sys.path.
    gate = (
        Path(__file__).resolve().parents[3]
        / "src/vesuvius_autoresearch/core/checkpoint_refusal.py"
    )
    spec = importlib.util.spec_from_file_location("vesuvius_checkpoint_refusal", gate)
    if spec is None or spec.loader is None:
        print(f"cannot load {gate}", file=sys.stderr)
        return 2
    refusal = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(refusal)
    require_zip_checkpoint = refusal.require_zip_checkpoint

    failed = False
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        try:
            require_zip_checkpoint(path)
            payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        except Exception as error:  # noqa: BLE001 - report every refusal in the batch
            print("NOT_WEIGHTS_ONLY", name, type(error).__name__, str(error)[:300])
            failed = True
            continue
        if isinstance(payload, dict):
            layout = {
                key: (type(value).__name__, _length_or_value(value))
                for key, value in payload.items()
            }
        else:
            layout = type(payload).__name__
        print("WEIGHTS_ONLY_OK", name, str(layout)[:500])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
