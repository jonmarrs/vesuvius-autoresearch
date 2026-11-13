"""Check restricted CPU loading; refuse empty input and report failures via exit status.

A successful check is not a general safety certification or a persisted receipt.
"""

import sys


def main() -> int:
    paths = sys.argv[1:]
    if not paths:
        print("usage: check_ckpt_safe.py CHECKPOINT [CHECKPOINT ...]", file=sys.stderr)
        return 2

    import torch

    failed = False
    for path in paths:
        name = path.rsplit("/", 1)[-1]
        try:
            payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
        except Exception as error:  # noqa: BLE001 - report every refusal in the batch
            print("NOT_WEIGHTS_ONLY", name, type(error).__name__, str(error)[:300])
            failed = True
            continue
        if isinstance(payload, dict):
            layout = {
                key: (
                    type(value).__name__,
                    len(value) if hasattr(value, "__len__") else value,
                )
                for key, value in payload.items()
            }
        else:
            layout = type(payload).__name__
        print("WEIGHTS_ONLY_OK", name, str(layout)[:500])
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
