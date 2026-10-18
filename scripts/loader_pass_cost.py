"""What a pass over the training catalogue costs train.shuffled_loader's spawned workers.

Before 2026-10-17 each pass made a fresh iterator, which spawned the workers again.
Spawning pickles the dataset into each worker, and a pickle larger than a pipe's
64 KB blocks iter() until that worker has re-imported this process's main module.
So iter() waited for the workers one after another, inside train.py's
StopIteration branch, which the training budget does not count.

This times iter() and the first batch of each pass for the loader as it was
("respawned") and as it is ("persistent"). The dataset stands in for the Fr47
catalogue (7,345 patch origins, ~176 KB pickled), and the workers re-import
train.py through this script's own import of it, as they do under train.py. CPU
only: run it beside the loop with nice.

    .venv/bin/python -I scripts/loader_pass_cost.py --out reports/X.json
"""

from __future__ import annotations

import argparse
import functools
import json
import pickle
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "scripts" / "training"), str(ROOT), str(ROOT / "src")]

import numpy as np  # noqa: E402
import torch  # noqa: E402
import train  # noqa: E402
from torch.utils.data import DataLoader, Dataset  # noqa: E402

CATALOGUE = 7345  # "Initialized Dataset: ... Valid Patches 7345" (Fr47)


class Origins(Dataset):
    """A catalogue of patch origins; a pass reads only the first ``length``."""

    def __init__(self, length: int = 24):
        self.origins = np.arange(CATALOGUE * 3, dtype=np.int64).reshape(CATALOGUE, 3)
        self.length = length

    def __len__(self):
        return self.length

    def __getitem__(self, i):
        return torch.from_numpy(self.origins[i])


def respawned(dataset, batch_size: int, seed: int, workers: int) -> DataLoader:
    """train.shuffled_loader as it was on main at f85e0f7d."""
    generator = torch.Generator()
    generator.manual_seed(seed)
    return DataLoader(
        dataset,
        batch_size=batch_size,
        shuffle=True,
        generator=generator,
        pin_memory=True,
        num_workers=workers,
        multiprocessing_context="spawn",
        worker_init_fn=functools.partial(train._init_worker, None),
    )


def passes(loader: DataLoader, count: int) -> list[dict]:
    timings = []
    for _ in range(count):
        start = time.perf_counter()
        batches = iter(loader)
        made = time.perf_counter() - start
        start = time.perf_counter()
        next(batches)
        first = time.perf_counter() - start
        for _ in batches:
            pass
        timings.append({"iter_s": made, "first_batch_s": first})
    return timings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--workers", type=int, default=3)
    ap.add_argument("--passes", type=int, default=3)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    result = {
        "workers": args.workers,
        "dataset_pickle_bytes": len(pickle.dumps(Origins())),
        "loaders": {},
    }
    for name, make in (
        ("respawned", respawned),
        ("persistent", train.shuffled_loader),
    ):
        loader = make(Origins(), 4, seed=5, workers=args.workers)
        result["loaders"][name] = passes(loader, args.passes)
        del loader
        for i, t in enumerate(result["loaders"][name]):
            print(
                f"{name:10s} pass {i}: iter() {t['iter_s']:6.2f} s, first batch {t['first_batch_s']:6.2f} s",
                flush=True,
            )
    args.out.write_text(json.dumps(result, indent=1) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
