"""Load a third-party checkpoint with torch's weights-only unpickler before villa loads it without one.

villa's ink checkpoint loader calls torch.load(..., weights_only=False), which runs whatever the pickle asks for.
A file that loads here holds only tensors and plain Python values, so handing it to villa runs no code of its own.
Prints the model type and patch size the checkpoint's embedded configuration names.

usage: check_checkpoint.py CHECKPOINT.pth
"""

from __future__ import annotations

import json
import sys


def describe(state: object) -> dict:
    """The parts of an ink checkpoint's embedded configuration that decide which model villa builds."""
    out: dict = {"top_level_keys": sorted(state) if isinstance(state, dict) else None}
    config = state.get("config") if isinstance(state, dict) else None
    if isinstance(config, dict):
        model = config.get("model") if isinstance(config.get("model"), dict) else config
        out["model_type"] = model.get("model_type", config.get("model_type"))
        out["patch_size"] = config.get("patch_size", config.get("crop_size"))
    return out


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    if len(args) != 1:
        print(__doc__, file=sys.stderr)
        return 2
    import torch

    try:
        state = torch.load(args[0], map_location="cpu", weights_only=True)
    except Exception as error:  # noqa: BLE001 - any refusal means: do not hand it to villa
        print(
            f"REFUSED: {args[0]} does not load weights-only: {error}", file=sys.stderr
        )
        return 1
    print(json.dumps({"weights_only_load": "ok", **describe(state)}, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
