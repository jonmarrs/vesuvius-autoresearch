"""Pre-flight for the villa PR that aligns spiral-fitting/autoresearch.md with runners/run_single.py.

Run it on posting day. It fetches villa, then:

1. **Patch.** Regenerates the patch against the current `origin/main` autoresearch.md from the
   replacement table below. Every anchor must match exactly once, and the result must `git apply
   --check` cleanly.
2. **Claims.** Runs the current `runners/run_single.py` with its fit/render/score subprocesses
   stubbed, and re-proves every behaviour the patch states. Nothing is taken from notes.
3. **Duplicates.** Lists open villa PRs touching autoresearch.md or runners/, and searches issues
   and PRs for the topic.

Any FAIL means do not post. Writes the patch to docs/villa_pr_autoresearch_runner.patch.

Usage: .venv/bin/python scripts/check_villa_runner_pr.py [--ref origin/main] [--no-network]
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parent.parent
VILLA = ROOT / "villa"
DOC = "spiral-fitting/autoresearch.md"
PATCH_OUT = ROOT / "docs" / "villa_pr_autoresearch_runner.patch"
BODY = ROOT / "docs" / "villa_pr_autoresearch_runner_body.md"

# (anchor that must occur exactly once in the upstream doc, replacement)
REPLACEMENTS = [
    (
        "   - `run_single.py` — the pipeline runner you launch",
        "   - `runners/run_single.py` — the pipeline runner you launch",
    ),
    (
        "`run_single.py` reads three things from the environment, which the caller sets:\n"
        "\n"
        "- `CUDA_VISIBLE_DEVICES` — the GPU subset for this run. `run_single.py` honours it: "
        "`--nproc_per_node` is set to the number of visible GPUs, and the pin is passed straight "
        "through to every step.\n"
        "- `FIT_SPIRAL_RUN_TAG` — the run tag (names the output dir and the fitted-mesh folder).\n"
        "- `FIT_SPIRAL_OUT_DIR` — the base output dir.\n",
        "`runners/run_single.py` takes these flags (see its `--help`):\n"
        "\n"
        "- `--gpus 0,1,2,3` — the GPU subset for this run: one fit rank per GPU, and the pin is "
        "passed straight through to every step. `CUDA_VISIBLE_DEVICES` alone is not enough: "
        "without `--gpus` the fit runs as a single process.\n"
        "- `--output <out_dir>/<tag>` — this run's output dir, which must be new or empty. The runner "
        "sets `FIT_SPIRAL_OUT_DIR` from it.\n"
        "- `--config <file>` — a JSON object of config overrides. The runner sets "
        "`FIT_SPIRAL_CONFIG_OVERRIDES` from it and drops that variable from its own environment.\n"
        "- `--dataset` and `--ink-volume` (required), and `--no-wandb`: the runner sets `WANDB_MODE` "
        "itself, so exporting `WANDB_MODE=disabled` does not turn W&B off.\n",
    ),
    (
        "On an 8-GPU box that means one run pinned to `CUDA_VISIBLE_DEVICES=0,1,2,3` and one to "
        "`4,5,6,7`, launched concurrently.",
        "On an 8-GPU box that means one run with `--gpus 0,1,2,3` and one with `--gpus 4,5,6,7`, "
        "launched concurrently.",
    ),
    (
        "Per-step logs go to `<out_dir>/logs/<tag>.{fit,ink,coverage}.log`, and the ink metric is "
        "written to `<out_dir>/<datedir>_<tag>/meshes/fitted_<tag>/ink_metric/metrics.json`.",
        "The runner writes no log files of its own: redirect each run's output to "
        "`<out_dir>/logs/<tag>.log`, and read the fit, render and scoring logs this document "
        "mentions from that file. The ink metric is written to "
        "`<out_dir>/<tag>/<run dir>/meshes/fitted/ink_metric/metrics.json` (`fitted_<name>` if "
        "`FIT_SPIRAL_RUN_TAG=<name>` is set in the environment).",
    ),
    (
        "by directly hacking the code, or by setting environment variables.",
        "by directly hacking the code, or with config overrides passed as `--config` (see above).",
    ),
    (
        "each with its own `FIT_SPIRAL_RUN_TAG`.",
        "each with its own `--output`.",
    ),
    (
        "for each line it exports `CUDA_VISIBLE_DEVICES`, `FIT_SPIRAL_RUN_TAG`, `FIT_SPIRAL_OUT_DIR` "
        "(and `WANDB_MODE=disabled`) and runs `python run_single.py` in the background with all "
        "output redirected to the per-step logs, then `wait`s for both.",
        "for each line it runs `python runners/run_single.py --gpus <gpus> --output <out_dir>/<tag> "
        "--dataset ... --ink-volume ... --no-wandb` in the background with all output redirected to "
        "`<out_dir>/logs/<tag>.log`, then `wait`s for both.",
    ),
]

results: list[tuple[str, bool, str]] = []


def claim(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))


def git(*args: str) -> str:
    return subprocess.run(
        ["git", "-C", str(VILLA), *args], check=True, capture_output=True, text=True
    ).stdout


# --------------------------------------------------------------------------- 1. patch


def build_patch(ref: str, work: Path) -> None:
    doc = git("show", f"{ref}:{DOC}")
    new = doc
    for anchor, repl in REPLACEMENTS:
        n = new.count(anchor)
        claim(f"anchor matches once: {anchor[:60]!r}", n == 1, f"{n} matches")
        if n == 1:
            new = new.replace(anchor, repl)
    a, b = work / "a" / DOC, work / "b" / DOC
    for p, text in ((a, doc), (b, new)):
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
    diff = subprocess.run(
        ["git", "diff", "--no-index", "--no-prefix", f"a/{DOC}", f"b/{DOC}"],
        cwd=work,
        capture_output=True,
        text=True,
    ).stdout
    PATCH_OUT.write_text(diff)
    # apply against a clean checkout of the doc at ref
    chk = work / "apply"
    (chk / Path(DOC).parent).mkdir(parents=True)
    (chk / DOC).write_text(doc)
    subprocess.run(["git", "init", "-q"], cwd=chk, check=True)
    r = subprocess.run(
        ["git", "apply", "--check", str(PATCH_OUT)],
        cwd=chk,
        capture_output=True,
        text=True,
    )
    claim(
        "patch applies cleanly to the ref's autoresearch.md",
        r.returncode == 0,
        r.stderr.strip(),
    )
    removed = sum(
        1 for ln in diff.splitlines() if ln.startswith("-") and not ln.startswith("---")
    )
    added = sum(
        1 for ln in diff.splitlines() if ln.startswith("+") and not ln.startswith("+++")
    )
    claim(
        "patch is small (<= 12 lines each way)",
        removed <= 12 and added <= 12,
        f"-{removed} +{added}",
    )
    stale = [
        s
        for s in (
            "CUDA_VISIBLE_DEVICES=0,1,2,3",
            "exports `CUDA_VISIBLE_DEVICES`",
            "reads three things from the environment",
        )  # fmt: skip
        if s in new
    ]
    claim(
        "no env-var launch instructions remain after the patch", not stale, str(stale)
    )


# --------------------------------------------------------------------------- 2. claims


def extract(ref: str, dest: Path) -> Path:
    raw = subprocess.run(
        ["git", "-C", str(VILLA), "archive", ref, "spiral-fitting"],
        check=True,
        capture_output=True,
    ).stdout
    with tarfile.open(fileobj=io.BytesIO(raw)) as tf:
        tf.extractall(dest, filter="data")
    return dest / "spiral-fitting"


def probe(sf: Path, work: Path) -> None:
    sys.path[:0] = [str(sf / "runners"), str(sf)]
    import run_single  # noqa: PLC0415

    seen: list[dict] = []

    def fake_run(command, *, check, env):
        script = next(Path(p).name for p in command if str(p).endswith(".py"))
        seen.append({"script": script, "cmd": list(command), "env": dict(env)})
        if script == "fit_spiral.py":
            out = Path(env["FIT_SPIRAL_OUT_DIR"])
            tag = env.get("FIT_SPIRAL_RUN_TAG")
            (out / "run" / "meshes" / (f"fitted_{tag}" if tag else "fitted")).mkdir(
                parents=True
            )
        elif script == "render_ink.py":
            (Path(command[2]) / "ink").mkdir()
            (Path(command[2]) / "ink" / "w001.jpg").touch()
        else:
            m = Path(command[2]).parent / "ink_metric"
            m.mkdir()
            (m / "metrics.json").write_text(
                json.dumps({"summary": {"total_fg_pixels": 1}})
            )
        return SimpleNamespace(returncode=0)

    real_run = subprocess.run
    run_single.subprocess.run = fake_run
    ds = work / "ds"
    ds.mkdir()
    documented_env = {
        "CUDA_VISIBLE_DEVICES": "4,5,6,7",
        "FIT_SPIRAL_RUN_TAG": "jul9a",
        "FIT_SPIRAL_OUT_DIR": str(work / "ignored"),
        "WANDB_MODE": "disabled",
        "FIT_SPIRAL_CONFIG_OVERRIDES": '{"from_env": 1}',
    }
    saved = {k: os.environ.get(k) for k in documented_env}
    os.environ.update(documented_env)
    try:

        def launch(name: str, *extra: str, cfg: dict | None = None) -> list[dict]:
            argv = [
                "--dataset",
                str(ds),
                "--ink-volume",
                str(ds),
                "--output",
                str(work / name),
            ]
            if cfg is not None:
                cp = work / f"{name}.json"
                cp.write_text(json.dumps(cfg))
                argv += ["--config", str(cp)]
            start = len(seen)
            run_single.run(run_single.build_parser().parse_args(argv + list(extra)))
            return seen[start:]

        # documented launch: no flags at all
        r = real_run(
            [sys.executable, str(sf / "runners" / "run_single.py")],
            capture_output=True, text=True, env={**os.environ},
        )  # fmt: skip
        claim(
            "launched as documented (env vars, no flags) it exits 2 on missing --dataset/--ink-volume",
            r.returncode == 2
            and "--dataset" in r.stderr
            and "--ink-volume" in r.stderr,
            f"exit {r.returncode}",
        )

        no_gpus = launch("no_gpus", "--no-wandb")
        fit = next(s for s in no_gpus if s["script"] == "fit_spiral.py")
        claim(
            "without --gpus the fit is ONE process, though CUDA_VISIBLE_DEVICES lists 4",
            "torch.distributed.run" not in fit["cmd"]
            and fit["env"]["CUDA_VISIBLE_DEVICES"] == "4,5,6,7",
            " ".join(Path(c).name for c in fit["cmd"][:3]),
        )
        claim(
            "--output overrides the caller's FIT_SPIRAL_OUT_DIR",
            fit["env"]["FIT_SPIRAL_OUT_DIR"] == str(work / "no_gpus"),
            fit["env"]["FIT_SPIRAL_OUT_DIR"],
        )
        claim(
            "the caller's FIT_SPIRAL_CONFIG_OVERRIDES is dropped",
            "FIT_SPIRAL_CONFIG_OVERRIDES" not in fit["env"],
            str(fit["env"].get("FIT_SPIRAL_CONFIG_OVERRIDES")),
        )
        claim(
            "FIT_SPIRAL_RUN_TAG from the environment still reaches the fit",
            fit["env"].get("FIT_SPIRAL_RUN_TAG") == "jul9a",
        )
        gpus = launch("gpus", "--no-wandb", "--gpus", "0,1,2,3")
        fit = next(s for s in gpus if s["script"] == "fit_spiral.py")
        claim(
            "--gpus 0,1,2,3 launches torch.distributed.run with 4 ranks",
            "torch.distributed.run" in fit["cmd"]
            and "--nproc-per-node=4" in fit["cmd"],
        )
        claim(
            "--gpus pins every step (fit, render, score)",
            len(gpus) == 3
            and all(s["env"]["CUDA_VISIBLE_DEVICES"] == "0,1,2,3" for s in gpus),
            str([s["env"]["CUDA_VISIBLE_DEVICES"] for s in gpus]),
        )

        wb = launch("wandb_default", "--gpus", "0")
        fit = next(s for s in wb if s["script"] == "fit_spiral.py")
        claim(
            "without --no-wandb, WANDB_MODE=disabled from the environment is overridden to online",
            fit["env"]["WANDB_MODE"] == "online",
            fit["env"]["WANDB_MODE"],
        )

        cfg_key = _a_config_key(sf)
        cfgd = launch("cfg", "--no-wandb", cfg={cfg_key[0]: cfg_key[1]})
        fit = next(s for s in cfgd if s["script"] == "fit_spiral.py")
        got = json.loads(fit["env"].get("FIT_SPIRAL_CONFIG_OVERRIDES", "{}"))
        claim(
            "--config sets FIT_SPIRAL_CONFIG_OVERRIDES for the fit",
            got.get(cfg_key[0]) == cfg_key[1],
            str(got),
        )

        try:
            launch("gpus", "--no-wandb")
            refused = False
        except ValueError as e:
            refused = "must be empty" in str(e)
        claim("a non-empty --output is refused", refused)
    finally:
        run_single.subprocess.run = real_run
        for k, v in saved.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v


def _a_config_key(sf: Path) -> tuple[str, object]:
    """A real config key and a valid value for it, so --config validation accepts it."""
    sys.path.insert(0, str(sf))
    import config  # noqa: PLC0415

    c = config.Config() if hasattr(config, "Config") else None
    for name in ("optimizer_num_training_steps", "num_training_steps"):
        if c is not None and hasattr(c, name):
            return name, int(getattr(c, name)) // 2
        if isinstance(c, dict) and name in c:
            return name, int(c[name]) // 2
    raise SystemExit(
        "no training-steps key found in config.Config; update _a_config_key"
    )


def static_claims(ref: str) -> None:
    tut = git("show", f"{ref}:scrollprize.org/docs/38_tutorial_spiral.md")
    claim(
        "villa's tutorial presents runners/run_single.py as the one-command pipeline",
        "runners/run_single.py" in tut and "--ink-volume" in tut,
    )
    # fitted mesh dir name: fit_spiral suffix 'fitted' -> save_mesh(name=suffix, run_tag=...) ->
    # meshes/{name}{tag_suffix}, tag_suffix = f'_{run_tag}'. (A stubbed fit cannot prove this.)
    fs = git("show", f"{ref}:spiral-fitting/fit_spiral.py")
    sm = git("show", f"{ref}:spiral-fitting/satisfaction_metrics.py")
    sh = git("show", f"{ref}:spiral-fitting/spiral_helpers.py")
    claim(
        "fitted mesh dir is meshes/fitted_<tag> (meshes/fitted without a tag)",
        "suffix = 'fitted'" in fs and "run_tag=run_tag, name=suffix" in sm
        and "tag_suffix = f'_{run_tag}' if run_tag else ''" in sh
        and "out_dir = f'{out_path}/meshes/{name}{tag_suffix}'" in sh,
    )  # fmt: skip
    claim(
        "run_single itself opens no log file (the scorer's fold logs live in a deleted _work dir)",
        not re.search(r"\.log[\"']|stdout=|stderr=", git("show", f"{ref}:spiral-fitting/runners/run_single.py"))
        and "shutil.rmtree(work_dir" in git("show", f"{ref}:spiral-fitting/get_ink_metrics.py"),
    )  # fmt: skip
    ls = git("ls-tree", "-r", "--name-only", ref, "spiral-fitting")
    claim(
        "no run_single.py outside runners/ (the doc's bare name resolves to nothing)",
        [p for p in ls.splitlines() if Path(p).name == "run_single.py"]
        == ["spiral-fitting/runners/run_single.py"],
    )


def _function(src: str, name: str) -> str:
    """Source of top-level function `name` (to the next top-level def), or ''."""
    m = re.search(rf"^def {name}\(.*?(?=^def |\Z)", src, re.S | re.M)
    return m.group(0) if m else ""


def body_claims(ref: str, sha: str) -> None:
    body = BODY.read_text()
    rs = git("show", f"{ref}:spiral-fitting/runners/run_single.py")
    fc, fe, ro = (
        _function(rs, n)
        for n in ("fit_command", "fit_environment", "require_empty_output")
    )
    claim("body: fit_command() uses torch.distributed.run only for > 1 --gpus device",
          "torch.distributed.run" in fc and "len(gpu_ids) > 1" in fc)  # fmt: skip
    claim("body: fit_environment() pops FIT_SPIRAL_CONFIG_OVERRIDES and sets WANDB_MODE",
          'env.pop("FIT_SPIRAL_CONFIG_OVERRIDES"' in fe and 'env["WANDB_MODE"]' in fe)  # fmt: skip
    claim("body: require_empty_output() refuses a non-empty dir", "must be empty" in ro)
    claim("body: every cited function is named in the body",
          all(f"`{n}()`" in body for n in ("fit_command", "fit_environment", "require_empty_output")))  # fmt: skip
    claim(
        "body: cites the SHA checked today",
        sha in body,
        f"today {sha}; update the body if FAIL",
    )
    both = body + PATCH_OUT.read_text()
    markers = [m for m in ("Claude", "Generated with", "\U0001F916", "Co-Authored-By", "Anthropic",
                           "ChatGPT", "LLM") if m in both]  # fmt: skip
    claim("no AI-authorship markers in body or patch", not markers, str(markers))


# --------------------------------------------------------------------------- 3. duplicates


def duplicates() -> None:
    def gh(*args: str) -> str:
        return subprocess.run(
            ["gh", *args], check=True, capture_output=True, text=True
        ).stdout

    prs = json.loads(gh("pr", "list", "-R", "ScrollPrize/villa", "--state", "open", "--limit", "200",
                        "--json", "number,title,files,author"))  # fmt: skip
    touching = [
        f"#{p['number']} {p['author']['login']}: {p['title']}"
        for p in prs
        if any(
            f["path"] == DOC or f["path"].startswith("spiral-fitting/runners/")
            for f in p["files"]
        )
    ]
    claim(
        "no OPEN PR touches autoresearch.md or runners/",
        not touching,
        "; ".join(touching),
    )
    mine = [p for p in prs if p["author"]["login"] == "jonmarrs"]
    claim("our open villa PRs <= 2 before posting (cap 3)", len(mine) <= 2,
          ", ".join(f"#{p['number']}" for p in mine))  # fmt: skip
    hits = []
    for q in ("autoresearch run_single", "run_single --gpus", "FIT_SPIRAL_CONFIG_OVERRIDES",
              "autoresearch.md CUDA_VISIBLE_DEVICES", "run_single.py WANDB_MODE"):  # fmt: skip
        out = json.loads(gh("search", "issues", q, "-R", "ScrollPrize/villa", "--include-prs",
                            "--json", "number,title,state", "--limit", "20"))  # fmt: skip
        hits += [f"#{h['number']} {h['state']} {h['title']}" for h in out]
    hits = sorted(set(hits))
    on_topic = [
        h
        for h in hits
        if any(w in h.lower() for w in ("autoresearch", "run_single", "runner"))
    ]
    claim(
        "topic search: no hit titled about autoresearch/run_single/runner",
        not on_topic,
        "; ".join(on_topic),
    )
    if hits:
        print(
            "INFO  other search hits (reviewed 2026-09-29: #1607 #1716 #1732 #1735 #1736 #1745 #1830 "
            "#1836 #1837 #1883 are fit_spiral/README work, no overlap). Review any NEW number:"
        )
        for h in hits:
            print(f"        {h}")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--ref", default="origin/main")
    ap.add_argument("--no-network", action="store_true")
    args = ap.parse_args()
    if not args.no_network:
        git("fetch", "-q", "origin")
    sha = git("rev-parse", "--short", args.ref).strip()
    with tempfile.TemporaryDirectory() as t:
        work = Path(t)
        build_patch(args.ref, work / "patch")
        static_claims(args.ref)
        (work / "probe").mkdir()
        probe(extract(args.ref, work / "src"), work / "probe")
    body_claims(args.ref, sha)
    if not args.no_network:
        duplicates()
    bad = 0
    print(f"villa {args.ref} = {sha}\n")
    for name, ok, detail in results:
        bad += not ok
        print(
            f"{'PASS' if ok else 'FAIL'}  {name}" + (f"  [{detail}]" if detail else "")
        )
    print(
        f"\n{len(results) - bad}/{len(results)} pass; patch -> {PATCH_OUT.relative_to(ROOT)}"
    )
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
