# Design and architecture review — the owner's #485, the depth sweep's run script

Date: 2026-11-24. Baseline: `2aa4ded` (main after round #224's merge).
Reviewer: Claude (Anthropic), at the owner's request.

This round covers the 09:12 UTC firing on 2026-11-24. Main had not moved since round #224's merge.

It finishes **#485**, finding 135, with `repro/first_letters/pherc0211_control/run_depth_sweep.sh`, which round #224
left. The script reads nothing new into being: every map comes from a render on disk. Its steps, each run only if
the one before exited 0:
- **check** the weights and the winner's `inference.py` against their SHA-256 values;
- **sweep211**: for each arm, winding and shift D other than 0, `depth_sweep.py planes`, then Studio with the
  winner's command;
- **sweep343**: the same on PHerc. 343's surface;
- **repeat**: Studio again on finding 124's own w035 planes, compared with finding 124's map;
- **compare**: `depth_sweep.py compare`, then `compare343`.

A sampler records the GPU's memory from the first sweep to the repeat. The script is under `repro/first_letters/`,
so this round adds tests only.

## What changed

### The run script's blocks are run (`tests/test_studio_depth_sweep.py`)

No test ran or read `run_depth_sweep.sh`, and all 17 of this round's mutants of it survived. Eight new test
functions, 16 cases, take each block from the script's own text and run it under `bash -u` with stand-in commands,
as round #221 ran `run_snap_passes.sh`. They kill all 17.
- **The up-front checks.** An existing output folder, a missing Studio environment, a missing render, a missing
  reversed D = 0 map, or a missing PHerc. 343 render or map stops the run, before anything runs.
- **A failed step** records its gate and stops the run.
- **The sweeps.**
  - Each arm, winding and shift's planes are made for that shift. Studio then reads them with the winner's command
    and writes the map into the shift's own folder (`d-2`, `d+1`); PHerc. 343's is `forward.npy`.
  - Each set of planes is deleted once read.
  - A shift whose planes fail stops the sweep, before Studio reads it.
- **`compare`.**
  - Without a verdict, `compare` still describes PHerc. 343, then fails.
  - If `compare343` fails, `compare` fails too.
  - It takes the band's distance field from `work/surf_sdt`.
- **The repeat** compares Studio's new map with finding 124's own, not with itself.
- **The GPU peak** is the largest sample, or null without one.

No code changed. No defect was found that the run itself met. The one below is pinned with a strict xfail.

## Verified, no change needed

- **The record's steps all exited 0.** The sweep at PHerc. 211 took 5,896 s and at PHerc. 343 1,087 s. The repeat
  gave finding 124's map again exactly, with a largest difference of 0.0.
- **The folders are the ones `depth_sweep.py` reads.**
  - The sweep writes `SWEEP_DIR/d±D/wNNN.npy` and `maps/343/d±D/forward.npy`, with `printf 'd%+d'` matching
    `shift_dir`.
  - D = 0 is read from findings 124's, 134's and 127's own maps, as `carry_arm` and `compare343` expect.

## Observations for the owner (not changed)

- **A failed step leaves the GPU sampler running.**
  - `run_depth_sweep.sh` starts `nvidia-smi -l 5` before the first sweep, and stops it only after the repeat. It has
    no `EXIT` trap.
  - If a sweep or the repeat fails, `step` exits with the sampler still writing to `gpu.csv` every 5 seconds, and
    no `gpu_peak.json` is written.
  - `run_dense_read.sh`, `run_snap_passes.sh` and `run_studio_fast.sh` stop theirs with
    `trap 'kill "$SMI" 2>/dev/null' EXIT`. The scripts whose sampler lives inside one function stop it there, failed
    or not.
  - `test_a_failed_step_stops_the_gpu_sampler` is a strict xfail that shows it; it passes once a trap is added.
- **The up-front checks do not cover the files only `compare` reads.** These are PHerc. 343's reversed map, sidecar
  and ink image, the final windings, and the band's distance field. A missing one would stop the run at its last
  step, after the sweeps' GPU time. The run had them all.

## Verification

- **The touched module.** `test_studio_depth_sweep.py` gives 41 passed and 1 xfailed, against 26 passed before.
- **Ruff and mypy.**
  - Ruff 0.9.10 `check` is clean over the repository, as the CPU workflow runs it, and `format` is clean on the
    touched module.
  - Mypy is clean over the whole repository, 1,110 files, with `--python-executable ./.venv/bin/python`.
- **The standard suite**, 235 modules, gives the same 278 failing ids as round #224's run. It does not run the
  touched module.
- **The 310 test modules outside the suite** give the same 24 failing ids as round #224's run.
  - 3,483 passed: round #224's 3,468 and the 15 new passing cases.
  - 5 xfailed: round #224's 4 and the new strict xfail.
  - One of the 24 failing ids is the free-disk case round #196 described.
- **The doc audit**, run alone, lists the same unresolved references as on `2aa4ded`.
- **The smoke test** gives 8 passed, 3 skipped and none failed.

Every other failing id is this container's: it has no villa checkout.

## A note on this round's work

- **`run_depth_sweep.sh` is unchanged.** Its mutants were run in a worktree.
  - The tests write their stand-ins under `tmp_path`: Python, Studio's interpreter and `nvidia-smi`.
  - The repeat's test runs the script's own Python comparison with this environment's Python.
  - The xfail's test kills the stand-in sampler it starts, whatever the outcome.
- **#485 is now reviewed**, in rounds #224 and #225.
- **Still not reviewed from the owner's merges since round #182:** #488, #489, #493, #496, #505, #517 and #524.
- **Still not reviewed from before:** #437 and the rest of #433 (both need villa), #422, #424 and #428, the rest of
  #390, #396 and #411, and the parts of #421 and #423 that rounds #170 and #171 listed.
- **The mutants are a sample.** All 17 were run again with the new tests, and all 17 are killed.
