"""Presence checks for declared original study inputs; never download or decode."""

import os
import re
import subprocess

STUDY_PATHS = {
    "spiral_patches": ("local_data/spiral_patches_phercparis4/umbilicus.json",),
    "spiral_rays": tuple(
        f"local_data/spiral_winding_model_phercparis4/shard_0/{name}.npy"
        for name in (
            "ray_origin_zyx",
            "ray_step_zyx",
            "crossing_t",
            "crossing_level",
            "crossing_offsets",
        )
    ),
}


def git_environment():
    """Honor -C despite hook repository selectors; keep auth and guard settings."""
    selectors = {
        "GIT_DIR",
        "GIT_WORK_TREE",
        "GIT_INDEX_FILE",
        "GIT_COMMON_DIR",
        "GIT_OBJECT_DIRECTORY",
        "GIT_ALTERNATE_OBJECT_DIRECTORIES",
        "GIT_PREFIX",
    }
    return {k: v for k, v in os.environ.items() if k not in selectors} | {
        "GIT_NO_LAZY_FETCH": "1"
    }


def missing_study_inputs(root, names):
    if not names or any(
        not isinstance(name, str) or name not in STUDY_PATHS for name in names
    ):
        raise ValueError(
            "research_input requires a known study name: spiral_patches or spiral_rays"
        )
    return [
        f"missing original study input: {path}"
        for name in dict.fromkeys(names)
        for path in STUDY_PATHS[name]
        if not (root / path).is_file()
    ]


def missing_villa_refs(root, refs):
    if not refs or any(
        not isinstance(ref, str) or not re.fullmatch(r"[0-9a-f]{7,40}", ref)
        for ref in refs
    ):
        raise ValueError(
            "villa_history requires immutable commit IDs (7-40 lowercase hex digits)"
        )
    repo = root / "villa"
    env = git_environment()

    def git(*args):
        return subprocess.run(
            ["git", "-c", "protocol.allow=never", "-C", str(repo), *args],
            capture_output=True,
            text=True,
            env=env,
            timeout=10,
        )

    own = git("rev-parse", "--show-toplevel")
    if (
        own.returncode
        or not own.stdout.strip()
        or repo.resolve() != root.joinpath(own.stdout.strip()).resolve()
    ):
        return [
            "villa history requires its own initialized checkout, not the parent repository"
        ]
    return [
        f"missing Villa commit: {ref}"
        for ref in dict.fromkeys(refs)
        if git("rev-parse", "--verify", f"{ref}^{{commit}}").returncode
    ]
