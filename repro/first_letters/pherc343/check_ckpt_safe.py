"""Load each checkpoint with weights_only=True (refuses arbitrary pickle code) and print its top-level layout."""

import sys

import torch

for path in sys.argv[1:]:
    name = path.rsplit("/", 1)[-1]
    try:
        payload = torch.load(path, map_location="cpu", weights_only=True, mmap=True)
    except Exception as error:  # noqa: BLE001 - the point is to report any refusal
        print("NOT_WEIGHTS_ONLY", name, type(error).__name__, str(error)[:300])
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
