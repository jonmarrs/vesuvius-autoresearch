# Design and architecture review — the spiral_s1 and scroll1_cubes fetchers

Date: 2026-10-17. Baseline: `c35fe2a8` (main after #107). Villa pin `ccb431818`.
Reviewer: Claude (Anthropic), at the owner's request.

Scope: `repro/spiral_s1/`, the scripts that fetched the Scroll 1 spiral-fitting dataset and ran its smoke and
baseline fits, and `repro/scroll1_cubes/`, the instance-label cube fetchers behind
`reports/scan_quality_reachability.md`. No earlier review covered either. Both were committed as records of runs
made from a copy in the owner's data directory, and are kept runnable. The other shell fetchers were checked for the
same defect.

## What changed

- **An interrupted download was kept for good.**
  - Six curl fetchers wrote straight to the final name, and skipped any non-empty file on the next run:
    `fetch_metas.sh`, `fetch_patches.sh` and `fetch_winding_model.sh` in `spiral_s1`, and `fetch_cubes.sh` and
    `fetch_masks.sh` in `scroll1_cubes`.
  - A run killed mid-transfer (Ctrl-C, OOM, a reboot) leaves a partial file that is non-empty too. The README called
    them "resumable (skips non-empty files)", so the partial file was skipped from then on.
  - Simulated with a stand-in `curl`: after a killed run and a re-run, `p2/x.tif` and `c2/c2_volume.nrrd` still
    held the five bytes written before the kill.
  - `fetch_winding_model.sh` fetched its top-level `manifest.json` again on every run, with no retry and no cleanup.
    A run killed there replaced a good manifest with a partial one.
  - Each file now goes to a `.part` and is moved into place only on success. A failure removes the `.part`.
  - `fetch_lasagna.sh` uses `wget -c`, which resumes a partial file rather than skipping it, and was left alone.
- **Two fetchers wrote into directories they never created.**
  - `fetch_metas.sh` writes `metas/<name>.json` and `fetch_masks.sh` writes `masks/<cube>_mask.nrrd`. Neither ran
    `mkdir`, and curl does not create directories.
  - From a fresh directory every request was a miss: the old `fetch_metas.sh` reported `fetched=0 misses=3` against
    three listed patches.
  - Both now create their output directory.
- **The miss logs accumulated across runs.**
  - `metas_misses.txt`, `patch_misses.txt` and `patch_no_generations.txt` were appended to and never reset. A re-run
    retries every miss, so a miss fetched on the second run still counted in `misses=`.
  - `patch_no_generations.txt` gained a duplicate line per patch on every run.
  - Each run now starts its logs empty. The final count of `fetch_patches.sh` no longer reads a missing file.
- **`run_after_sweep.sh` could fetch a stale list.**
  - Without `set -e`, a failed `select_spiral_patches.py` fell through to the non-empty check, which a
    `patches_in_roi.txt` from an earlier run passes.
  - The chain now stops when the selection fails.
- **In-place runs would write into the repository.**
  - The scripts take the dataset root from their own directory. Run from the repository rather than from a copy,
    `spiral_s1` alone writes ~48 GB into `repro/spiral_s1/` (89,237 metas, ~38,600 patch directories and the
    lasagna inputs), none of it ignored.
  - `.gitignore` now ignores everything there except the scripts, their documentation, `spiral-scroll.json`, and the
    two hand-made input lists.
- **`scripts/characterise_label_cubes.py` read every file in `masks/`.**
  - A leftover partial mask, or now a `.part`, ended it with `NRRDError: Invalid NRRD magic line`.
  - It now reads `*_mask.nrrd` only.
- **The input lists are named.**
  - `fetch_metas.sh` reads `patch_dirs.txt` and the cube fetchers read `all_cubes.txt`. Neither is in the
    repository, and no script here writes them.
  - The scripts' headers and the `spiral_s1` README now say so, with a dated correction to its "resumable" claim.

## Verified, no change needed

- **`status.sh`.** It counts metas as before, now excluding `.part` files mid-run.
- **The readers.** `select_spiral_patches.py` globs `metas/*.json`, so a `.part` is never read as a meta. It already
  skips an unparseable one and reports the sweep as incomplete. The patch readers open `x/y/z.tif` by name.
- **The fit drivers.** `run_smoke.sh` and `run_baseline.sh` match the README's account. Only
  `optimizer_num_training_steps` differs between them.
- **The other fetchers.**
  - `repro/ink_ablation/fetch_checkpoints.sh` was made atomic in the previous round.
  - `repro/spiral_render/run_interp_vs_labels.sh` fetches into a fresh work directory it refuses to reuse, and stops
    on the first failure.

## Observations for the owner (not changed)

- **The input lists are not committed.** `patch_dirs.txt` and `all_cubes.txt` are not in the repository, so neither
  study's fetch can be re-run from it. If the owner's copies are committed (the ignore rules leave them visible), the
  fetchers become runnable from a clone. The data host was not reachable from this review (proxy 403), so they could
  not be rebuilt here.
- **Hardcoded paths.** `run_after_sweep.sh`, `run_smoke.sh`, `run_baseline.sh`, `select_spiral_patches.py` and
  `characterise_label_cubes.py` name `/home/jon/...` directories, as other analyses here do.
- **Size checks.** Only `fetch_lasagna.sh`'s four large channels were checked against the server's `content-length`.
  The `.part` rename stops a killed transfer being kept; it cannot catch a server that sends a short body with
  success. curl's `--fail` and its length check cover the usual cases.

## Verification

Environment: CPython 3.10 venv, bash 5, GNU coreutils. No network access to `dl.ash2txt.org`.

- Each fetcher was simulated, old and new, with a stand-in `curl` on `PATH`. It writes `full:<name>` on success, or
  writes `TRUNC` and kills its caller to stand in for an interrupted transfer.
  - `fetch_metas.sh` from a fresh directory: old `fetched=0 misses=3`, new `fetched=3 misses=0`.
  - `fetch_patches.sh` killed on `p2/x.tif`, then re-run: old `TRUNC`, new `full:x.tif`, no `.part` left.
  - `fetch_winding_model.sh` killed on the top-level manifest after a good run: old `TRUNC`, new keeps the good one.
  - `fetch_masks.sh` from a fresh directory: old `masks=0`, new `masks=2`.
  - `fetch_cubes.sh` killed on `c2_volume.nrrd`, then re-run: old `TRUNC`, new `full:c2_volume.nrrd`.
- `characterise_label_cubes.py` over two valid masks and a `.part`: old `NRRDError`, new writes `mask_stats.json`.
- `bash -n` on every script. Ruff clean on the changed Python file.
- `git check-ignore`:
  - ignored: `metas/`, `verified_patches/`, `lasagna_inputs/`, the JSON inputs, `patches_in_roi.txt`, the miss logs
    and the cube directories;
  - visible: the tracked scripts and documents, `patch_dirs.txt` and `all_cubes.txt`.
- The standard suite: see the PR.
