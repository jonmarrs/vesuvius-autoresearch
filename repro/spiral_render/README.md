# Rendering ink from a spiral fit, using only published artifacts

**Status: this works.** `./setup_workdir.sh <work> <fitted_meshes>` then `./run_render.sh <work>`
renders legible Greek from our own 30k-step fit, ten windings, against the published ink-3d volume.
Lasagna flatten 1m34s on one 4090, render about 8 minutes streaming from S3.

**Read this first: use the LASAGNA path, not flatboi.** `run_single.py` passes no `--strips`, so
villa's real pipeline is the default full-scroll concat flattened by `lasagna/fit.py`. The
`--strips` path uses flatboi instead and is a dead end here: on a clean mesh (12,521 verts,
manifold, single component, zero degenerate faces) flatboi ran **9h12m without converging**, at both
`--flatten-keep 100` and the decimated default. Everything in section 2 below concerns tools only
the flatboi path needs, so it is real but not on the critical path.

What this directory is for: `render_ink.py` and `get_ink_metrics.py` turn a spiral fit into
`total_fg_pixels`, the number villa's spiral autoresearch loop optimises. Getting there from
published data alone takes four things that are not written down anywhere, recorded here so the
next person does not rediscover them.

## 0. Run `preflight.sh` first

Every obstacle in this README surfaced partway through a two-hour render. `./preflight.sh` checks
all of them in seconds and names what is missing: both interpreters, the villa checkout and the trees
renders extract from it, the rebuilt `vc_tifxyz2obj`, whether `serial_folds.patch` still applies, and
GPU/disk/RAM headroom. It exits non-zero, so it can gate a run.

**Environment, and the one trap worth stating twice:**

| variable | what it must point at | default |
|---|---|---|
| `RENDER_VENV` | python with **torch** — runs `render_ink.py` and the lasagna flatten | villa-spiral's `spiral-fitting/.venv` |
| `SCORE_VENV` | python with **huggingface_hub + nnunetv2** — runs `get_ink_metrics.py` | `data/ink_scorer_venv` |
| `VILLA` | a villa checkout; renders extract `origin/main`, fits run the **working tree** | `../villa-spiral` |
| `VC_IMAGE` | container with the rebuilt VC tools | `vc-render:local` |

**`VENV` means different things in different scripts** — the fit/render one in `run_render.sh`, the
scoring one in `score_arms.sh`. Setting it globally satisfies one and breaks the other, and the
failure arrives *after* the render has already run, as `No module named huggingface_hub`. Preflight
fails loudly if the two resolve to the same path.

The preflight also prints both villa refs, because fits and renders genuinely use different ones
(worktree vs `origin/main`) and quoting a single ref for "the tooling" has been wrong here twice.

## 1. The native binaries come from the published container, not a source build

Building VC3D from source pulls Ceres, OpenCV, CGAL and Qt. The published image has the tools
already:

```
docker pull ghcr.io/scrollprize/villa/volume-cartographer:edge
```

It ships `vc_render_tifxyz`, `vc_tifxyz_trim`, `vc_tifxyz2obj`, `vc_obj2tifxyz` and `flatboi`.

## 2. That image cannot render, and `Dockerfile` here fixes it

`:edge` and `:main` are the same digest
(`sha256:bad516f66001abca759454cc43e4fd11e5b19aa55d36bdc2043817291c8083c4`, built 2026-05-13) and
are older than `render_ink.py`. Two tools are wrong:

* **`vc_obj_uv_lift` is absent.** `render_ink.py` invokes it whenever `--flatten-keep < 100` (the
  default is 6.25). It is 381 lines depending only on header-only libigl, Eigen and OpenMP, so it
  builds standalone in seconds.
* **`vc_tifxyz2obj` predates `--keep`**, and answers `error: unknown option '--keep=6.2500'`.

The second is the fatal one. Without `--keep` the only accepted setting is `--flatten-keep 100`,
which is the case the option's own help warns about ("smaller mesh is less prone to SLIM
divergence"), and it does not converge:

| windings | vertices into flatboi | `--flatten-iters` | result |
|---:|---:|---:|---|
| 10 | 200,196 | 50 | killed at 1h51m, still running |
| 3 | ~60,000 | 10 | killed at 1h13m, still running |

`Dockerfile` rebuilds `vc_tifxyz2obj` from villa source pinned by `VILLA_SHA` and grafts it plus
its five shared libraries onto the published runtime image, shadowing the stale binary on PATH. The
key economy is building **one CMake target**, not VC3D: `--target vc_tifxyz2obj` pulls in
`libvc_core` and skips the Qt UI, flatboi, python bindings and tests, so configure takes seconds and
the compile a few minutes rather than the hour a full build costs. The `builder-ubuntu-24.04` image
supplies Ceres, OpenCV, CGAL and Boost, so no root and no apt on the host.

The build asserts `vc_tifxyz2obj` accepts `--keep` and fails if not, so it cannot silently revert to
the broken path.

With that in place `--keep` does what it exists to do, emitting the coarse/fine pair:

```
w010-019_coarse.obj    12,521 verts   <- flatboi flattens this
w010-019.obj          200,196 verts   <- vc_obj_uv_lift lifts the UVs back onto this
```

Reported upstream as ScrollPrize/villa#1660; a refreshed published image would make this whole
directory unnecessary.

## 3. The published mesh frame and the published ink volume differ by exactly 4x

```
spiral_datasets/PHercParis4/lasagna_inputs/las_008_*   level 0 = [18946,  8174,  8174]   9.6 um
representations/predictions/ink-3d/...v3-78k-fullsup   level 0 = [75784, 32693, 32693]   2.4 um
```

The ink volume's level 0 matches `volumes/20260411134726-2.400um-...-masked.zarr` exactly, so it
is the 2.4 um scroll frame. A fit run on the published lasagna inputs emits meshes in the 9.6 um
frame.

`render_ink.py` assumes the mesh is already in the volume's level-0 frame and offers no way to say
otherwise. **Unscaled, the render exits 0 and writes an entirely black strip**, reported only as
`p95=0.0` in passing. Verified by sampling the ink volume at the mesh's own vertices
(`scripts/probe_ink_volume_frame.py`):

```
 scale   in bounds  sampled   nonzero     mean   max
     1      100.0%      200      0.0%     0.00     0
     2      100.0%      200     66.5%    12.04   250
     4      100.0%      200     90.0%    19.64   250
```

Note scale 2 reads 66.5% nonzero: the scroll is dense enough that a wrong-but-close scale still
lands on papyrus often, so the nonzero fraction alone does not identify the scale. The array-shape
ratio does, and 4 agrees with it.

`vc_render_tifxyz` has `--scale-segmentation` for exactly this, but `render_ink.py` does not pass
it. Inject it with a wrapper via `--vc-render-bin`:

```sh
#!/bin/sh
exec vc_render_tifxyz --scale-segmentation 4 "$@"
```

## 4. `lasagna/fit.py` imports a module that is not in `lasagna/`

```
ModuleNotFoundError: No module named 'vc3d_fiber_format'
```

It lives in villa's `vesuvius/src/vc3d_fiber_format/`, so the flatten dies on import unless
`vesuvius/src` is on `PYTHONPATH`. `setup_workdir.sh` extracts it alongside `lasagna`.

## 5. GPU: split host and container

There is no nvidia container runtime here, so lasagna cannot use the GPU from inside the image.
`run_render.sh` runs the python on the HOST (its venv has torch 2.11.0+cu128 on a 4090) and calls
the native binaries in the container through `bin/` wrappers. Those mount the workspace at an
**identical** path so absolute arguments need no translation, and pass `--user` so outputs are not
root owned.

## 6. The ink volume is streamable, no bulk download

`--volume <empty local cache dir> --remote-url <the s3 zarr url>`. Level 0 is 75784 x 32693 x
32693 uint8 in 256^3 chunks, so only the chunks under the mesh are fetched.

## Putting it together

```sh
docker build -t vc-render:local .            # ~5 min: one CMake target, not all of VC3D
docker run --rm -v "$WORK":/work --entrypoint sh vc-render:local -c "
  cd /work/sf_main && python3 -u render_ink.py /work/meshes \
    --volume /work/inkcache --remote-url '$INK_URL' \
    --vc-render-bin /work/bin/vc_render_scaled \
    --strips --no-full-scroll --num-processes 1"
```

`--flatten-keep` is left at its documented default, which the rebuilt `vc_tifxyz2obj` accepts.
`sf_main` must be a `spiral-fitting` tree recent enough to have `--remote-url`; the checkout in
`villa-spiral` was 13 commits behind and did not.

Two costs worth knowing before starting. flatboi is single threaded and still slow even on the
decimated mesh, so a full 120 winding fit is a long job on a 4 core box. And `vc_render_scaled` must
be on a path visible inside the container.

## 7. Scoring an OUTER-winding strip OOMs the stock scorer

The four obstacles above are about getting a render at all. A fifth appears only at the outer
windings, because those strips are an order of magnitude bigger:

| arm | flat grid | rendered strip |
|---|---|---|
| w010-w019 (inner) | 881 x 304 | 8,810 x 3,040 = 26.8M px |
| w120-w129 (outer) | 8267 x 426 | 82,670 x 4,260 = 352M px |

`get_ink_metrics.py` launches one subprocess per fold and waits for all three, so at 352M px three
copies of the strip's logits are live at once. On a 32GB box that is fatal, and it is fatal in a way
the fold logs do not explain:

```
[mem] used= 8706MB avail=23386MB    <- before launch
[mem] used=30878MB avail= 1214MB    <- three folds live
  fold 0 (GPU 0) FAILED (rc=1)
  fold 1 (GPU 0) FAILED (rc=-9)     <- SIGKILL, the OOM killer
```

`serial_folds.patch` adds an opt-in `INK_METRIC_SERIAL_FOLDS=1`: folds run one at a time, and the
ensemble accumulates in place rather than stacking three arrays and calling `np.mean`. The default
path is untouched. `score_arms.sh` sets the variable and traces memory alongside, because an OOM is
otherwise silent.

**`setup_workdir.sh` applies the patch, and you should not do it by hand.** The script extracts a
fresh *stock* `spiral-fitting` tree from villa, so a work dir does not carry the gate unless
something puts it there. Two arms were scored with `INK_METRIC_SERIAL_FOLDS=1` exported and nothing
in the code reading it: the variable was set, the folds ran concurrently anyway, memory reached
30.6GB and nnU-Net's export workers were OOM-killed with

```
RuntimeError: Segmentation export worker died. It was likely killed by
your OS because of insufficient available CPU RAM.
```

which reads like a `--procs` problem and is not one. `--procs` stays at the scorer's default of 8;
once folds are serial, 8 fits in about 19-20GB. The diagnostic that distinguishes the two causes is
the launch line: serial mode prints `launching fold 0/1/2` minutes apart, concurrent mode prints
them together. Peak memory says it more reliably than the log ordering does, since those lines are
written at launch either way.

`setup_workdir.sh` now applies `serial_folds.patch` and then greps for the gate, failing if it is
absent, so a work dir cannot be built without it.

**Check the exit code, not just the log.** `get_ink_metrics.py` fails cleanly, but

```sh
echo "[exit] $(basename "$ARM") scoring rc=$?"     # WRONG
```

expands left to right: the command substitution runs and overwrites `$?` with *its* status before
`rc=$?` is read, printing `rc=0` over a run that had just lost two of three folds. Capture `rc=$?`
on its own line, and assert `metrics.json` exists as well -- the file check catches this class
regardless of the shell subtlety.

**The scorer is not bit-deterministic, patched or not.** Three runs over one fixed strip:

| run | `total_fg_pixels` | `line_score` |
|---|---:|---|
| on record | 249,913 | 0.40331167445607574 |
| stock path, re-run | 249,905 | 0.40331167445607574 |
| serial path | 249,906 | 0.40331167445607574 |

The **stock** path also fails to reproduce its own earlier number, so the drift is nnU-Net run-to-run
nondeterminism on GPU and not the patch. The spread is 0.0032%, against a documented **1.42%**
floor for a full render+score re-run on identical meshes: essentially all of that 1.42% is the
render, and a re-score is close to free of noise. `line_score` is bit-identical across all three,
being computed the same way from the averaged probabilities.

**Careful where you run git.** The scratch output root used throughout this work,
`openclaw-workspace/Neo-VM/spiral_out`, sits *inside another git repository* -- the workspace repo,
which has a live remote. `spiral_out` is neither tracked nor gitignored there, so it shows up as
**33 GB of untracked content** (including eleven ~2 GB fit checkpoints).

Two consequences. A `git add -A` or a careless `git commit -a` from that directory would try to
commit tens of gigabytes of render output to an unrelated remote. And any `git` command run after
`cd`-ing there acts on the workspace repo, not on this one -- I ran `git add`/`commit`/`push` from
there by accident; the add failed on a non-matching pathspec so nothing happened, but the push was
aimed at the wrong remote and would not have been a no-op had that branch been ahead.

Check `git rev-parse --show-toplevel` before any git operation in a session that also touches
`spiral_out`, and never trust that a `cd` earlier in a compound command left you where you think.

**An outer render can be OOM-killed, and there is no resume.** One of five outer renders here died
that way: `vc_render_tifxyz` reached 26.9GB on a 32GB box and was SIGKILLed, surfacing as
`CalledProcessError ... returned non-zero exit status 137` from `render_ink.py`. Ninety-one minutes
of banding were lost, because nothing is checkpointed -- a failure costs the whole render, not the
remaining part. The four that succeeded peaked around 26GB, so the margin is thin rather than
comfortable, and whether a given run survives depends on what else is resident.

Before starting one, get the box as empty as you can and keep it that way; the desktop applications
that were resident during the failure came to about 1.8GB, which is the same order as the margin.
Do not run the test suite, another render, or a scoring job alongside it.

Rendering an outer strip is also slow for the same reason. `vc_render_tifxyz` reached 26.1GB RSS and
the box began swapping, taking band times from 26s to 18m. Four ten-winding outer renders took
**1h55m, 2h00m, 2h02m and 2h32m**, against about 8 minutes for ten inner ones. Budget ~2h per outer
arm plus ~15 min to score it, and run them strictly one at a time.

## 8. The render step leaves about 1GB of headroom, so do not run anything else

Section 7 is about the *scoring* step OOMing. The *render* step has the same problem for a different
reason, and it is easy to miss because nothing fails:

```
total 31G  used 29G  available 1G
  25.3G vc_render_tifxyz
```

measured mid-render on 2026-09-04, with `serial_folds` already in force. `vc_render_tifxyz` holds
roughly 25GB for the whole ~3h45m outer render. `preflight.sh` reports `RAM: 31G` as **ok**, and by
its own rule that is correct -- the render fits. What it cannot know is that the margin is about a
gigabyte, so anything else memory-hungry started during that window is competing for it.

**Practical rule: while a render is in flight, do not start the test suite, a second arm, a
container build, or another render.** A multi-arm study is running unattended for tens of hours, and
the cost of losing an arm is the arm plus everything queued behind it.

Two honesty notes, because the obvious inference here is wrong:

* **No OOM kill has actually occurred during a render.** `journalctl -k` over the whole
  patch-bootstrap study window reports zero `oom_kill` events. The risk above is inferred from the
  headroom number, not from a corpse.
* A full test-suite run launched during the first arm's render *was* killed, and it is tempting to
  present that as the OOM. It was not -- the kernel log is clean and the harness stopped it. Do not
  cite it as evidence.

The reason to write the rule down anyway is that 1GB of headroom is not a margin, and the failure it
would produce is the expensive kind: a dead arm partway through an unattended multi-day comparison.
