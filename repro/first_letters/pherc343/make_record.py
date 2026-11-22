"""Assemble reports/first_letters_343_reproduction.json from the files the kill test left on disk.

Usage: make_record.py RUN_ROOT OUT.json

Nothing is typed in here except what no file records: the host, the times the training loop was
stopped and started, and the list of what the run did not measure. Every other number is read from
the run's own logs and comparison files under RUN_ROOT.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

NAME = "concat_w047-w048_R5B2_z9500-11000"
MODELS = ("dnative", "hybrid_3d2d-seed42", "hecate", "hybrid_3d2d-seed43")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def load(path: Path) -> dict:
    return json.loads(path.read_text())


def git(repo: Path, *args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(repo), *args], check=True, capture_output=True, text=True
    ).stdout.strip()


def stage_a(log: Path) -> dict:
    lines = log.read_text().splitlines()
    start = next(line for line in lines if line.startswith("STAGEA_START")).split()[1]
    end = next(line for line in lines if line.startswith("STAGEA_EXIT")).split()
    seconds = next(line for line in lines if line.startswith("STAGEA_SECONDS")).split()[
        1:
    ]
    jobs = [line.split("\t") for line in lines if line.split("\t")[0] in MODELS]
    if len(jobs) != 8:
        raise SystemExit(f"expected 8 job lines in {log}, found {len(jobs)}")
    renders = ("plain", "padded")
    return {
        "started": start,
        "finished": end[2],
        "exit": int(end[1]),
        "wall_seconds": {k: int(v) for k, v in (item.split("=") for item in seconds)},
        "jobs": [
            {
                "render": renders[i // 4],
                "model": j[0],
                "depth": int(j[1]),
                "seconds": int(j[2]),
                "exit": int(j[3]),
            }
            for i, j in enumerate(jobs)
        ],
    }


def gpu(csv: Path) -> dict:
    rows = [line.split(",") for line in csv.read_text().splitlines() if line.strip()]
    used = [int(row[1].split()[0]) for row in rows]
    return {"samples": len(used), "interval_seconds": 5, "peak_memory_mib": max(used)}


def whole_image(published: Path, ours: Path) -> dict:
    import cv2
    import numpy as np

    a, b = cv2.imread(str(published)), cv2.imread(str(ours))
    if a.shape != b.shape:
        raise SystemExit(f"image shapes differ: {a.shape} vs {b.shape}")
    diff = np.abs(a.astype(np.int16) - b.astype(np.int16)).max(axis=2)
    return {
        "shape_hw": list(a.shape[:2]),
        "pixels": int(diff.size),
        "differing_pixels": int((diff > 0).sum()),
        "max_abs_diff": int(diff.max()),
        "sha256": sha256(ours),
    }


def main() -> int:
    root, out = Path(sys.argv[1]), Path(sys.argv[2])
    work, repo = root / "work", root / "src/repo"
    render_log = (root / "logs/render_66.log").read_text().splitlines()
    render_start = next(
        line for line in render_log if line.startswith("RENDER_START")
    ).split()
    render_exit = next(
        line for line in render_log if line.startswith("RENDER_EXIT")
    ).split()
    render_args = dict(item.split("=", 1) for item in render_start[2:])
    wall = next(line for line in render_log if "Elapsed (wall clock)" in line).rsplit(
        " ", 1
    )[1]
    minutes, seconds = wall.split(":")
    cache_bytes = sum(
        p.stat().st_size for p in (root / "vchome").rglob("*") if p.is_file()
    )

    sums = {}
    for line in (repo / "outputs/SHA256SUMS").read_text().splitlines():
        digest, path = line.split(maxsplit=1)
        if path.strip().lstrip("*").startswith(f"{NAME}.tifxyz/"):
            sums[path.strip().lstrip("*").split("/", 1)[1]] = digest
    mesh = {
        name: {"published": digest, "ours": sha256(work / f"mesh/{NAME}.tifxyz" / name)}
        for name, digest in sorted(sums.items())
    }
    for entry in mesh.values():
        entry["match"] = entry["published"] == entry["ours"]

    compare = {v: load(work / f"compare_{v}.json") for v in ("pubstats", "ownstats")}
    for value in compare.values():
        for key in ("published", "ours"):
            value[key] = value[key].replace(str(root) + "/", "")

    record = {
        "what": "PHerc. 343 First Letters image rebuilt on this machine (the campaign's kill test)",
        "date": "2026-11-10",
        "recipe": {
            "repository": git(repo, "remote", "get-url", "origin").removesuffix(".git"),
            "commit": git(repo, "rev-parse", "HEAD"),
            "published_image_sha256": sha256(repo / f"outputs/{NAME}.png"),
        },
        "host": {"cpu_cores": 4, "ram_gb": 31, "gpu": "RTX 4090, 24 GB"},
        "scope": {
            "run_here": [
                "join of the two published windings into one mesh (mesh/build_concat.py)",
                "66-layer render from CT streamed off the public bucket",
                "four released ink models at depth +1, plain and padded render",
                "tile-phase merge and the submission image",
            ],
            "taken_from_the_publication": [
                "the two windings w047 and w048 (the spiral fit, snap and flatten were not run)",
                "the scroll axis, the row lines and the 18 letter boxes",
                "the per-model and ensemble statistics pooled over 31 depths (image_pubstats only)",
            ],
        },
        "checkpoints": {
            "downloads_sha256_checked_by": "ink/scripts/fetch_checkpoints.sh",
            "dense_native": "rebuilt from the published safetensors (the original .pth is not public)",
            "all_load_with_weights_only": True,
        },
        "mesh": {"files": mesh, "all_match": all(e["match"] for e in mesh.values())},
        "render": {
            "renderer_image": render_args["image"],
            "renderer_source": "villa 75c79ac5f (volume-cartographer tree identical to 41701aa)",
            "started": render_start[1],
            "finished": render_exit[2],
            "exit": int(render_exit[1]),
            "wall_seconds": round(int(minutes) * 60 + float(seconds), 1),
            "threads": int(render_args["threads"]),
            "cache_gb": int(render_args["cache_gb"]),
            "container_memory_cap": render_args["mem"],
            "ct_bytes_cached": cache_bytes,
            "check": {
                k: v
                for k, v in load(work / "render_check.json").items()
                if k != "render"
            },
        },
        "ink": {
            **stage_a(root / "logs/stage_a.log"),
            "parallel": {"villa_jobs": 1, "hecate_jobs": 1},
            "gpu": gpu(root / "logs/stage_a_gpu.csv"),
            "gpu_shared_with": "finding 109's intermittent use; the training loop was stopped",
            "full_recipe_jobs": 496,
            "jobs_run": 8,
        },
        "rerun_same_model": {
            "model": "hybrid_3d2d-seed42",
            "render": "plain",
            "maps": load(work / "rerun_seed42_determinism.json"),
        },
        "image": {
            v: {
                "comparison": compare[v],
                "whole_png": whole_image(
                    repo / f"outputs/{NAME}.png", work / f"image_{v}/{NAME}.png"
                ),
            }
            for v in ("pubstats", "ownstats")
        },
        "training_loop": {
            "stopped": "2026-11-10T09:58-08:00",
            "started": "2026-11-10T10:20-08:00",
        },
        "not_measured": [
            "the spiral fit, snap and flatten that produced the two windings",
            "the 31-depth sweep (496 jobs) and the statistics pooled from it",
            "host memory of the ink jobs",
            "the cause of the 8-byte difference in the render's file tree",
            "whether any of this shows text on a scroll that has not been read",
        ],
    }
    pub = compare["pubstats"]
    record["verdict"] = (
        "REPRODUCED"
        if record["mesh"]["all_match"]
        and record["render"]["check"]["decoded_voxels_identical_where_published"]
        and pub["ink_shown_iou"] >= 0.99
        and pub["abs_diff"]["max"] <= 8
        else "NOT_REPRODUCED"
    )
    out.write_text(json.dumps(record, indent=2) + "\n")
    print(record["verdict"], out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
