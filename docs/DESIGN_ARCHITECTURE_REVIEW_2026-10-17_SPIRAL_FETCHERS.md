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
  - Five curl fetchers wrote straight to the final name, and skipped any non-empty file on the next run:
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
- **Two runs of one fetcher overwrote each other.**
  - Two instances, or one name listed twice, truncated and moved each other's files and wiped each other's logs. Each
    fetcher now holds a lock in its directory (`flock`), and refuses to start beside another instance.
  - The fetchers driven by `xargs` de-duplicate their list.
- **Two fetchers wrote into directories they never created.**
  - `fetch_metas.sh` writes `metas/<name>.json` and `fetch_masks.sh` writes `masks/<cube>_mask.nrrd`. Neither ran
    `mkdir`, and curl does not create directories.
  - From a fresh directory every request was a miss: the old `fetch_metas.sh` reported `fetched=0 misses=3` against
    three listed patches.
  - Both now create their output directory.
- **The fetchers reported a cut-short run as done.**
  - When a worker died, GNU `xargs` stopped with exit 125, leaving the rest of the list unfetched and unlogged, and the
    script still printed `DONE ... misses=0`.
  - The three `xargs` fetchers now print `INCOMPLETE (xargs exit N)` and exit with that status.
  - A missing input list stops the fetcher before it touches its logs.
- **The miss logs accumulated across runs.**
  - `metas_misses.txt`, `patch_misses.txt` and `patch_no_generations.txt` were appended to and never reset. A re-run
    retries every miss, so a miss fetched on the second run still counted in `misses=`.
  - `patch_no_generations.txt` gained a duplicate line per patch on every run.
  - Each run now starts its logs empty.
- **`run_after_sweep.sh` fetched a stale list.**
  - `select_spiral_patches.py` declines to write `patches_in_roi.txt` while the metadata sweep is incomplete, and
    exits 0 doing so. A list from an earlier run then passed the chain's non-empty check and was fetched. A killed
    sweep ends the chain's wait just as a finished one does.
  - The chain now removes the old list before the selection, and stops if the selection fails or writes none.
  - It also runs the selection with `SPIRAL_DATA` set to its own directory. Before, the selection read the
    hardcoded data directory while the chain fetched into its own, which differ for a copy run anywhere else.
- **In-place runs would write into the repository.**
  - The scripts take the dataset root from their own directory. Run from the repository rather than from a copy,
    `spiral_s1` alone writes ~48 GB into `repro/spiral_s1/`: 89,237 metas, ~38,600 patch directories and the
    lasagna inputs. Of that, only the `.npy` files were already ignored (by the global rule).
  - `.gitignore` now ignores everything in both directories except scripts, documentation, `spiral-scroll.json`, and
    the two input lists the fetchers read.
- **`fetch_cubes.sh` dropped a last line without a newline**, and requested an empty cube name for a blank line.
  Both are handled.
- **`scripts/characterise_label_cubes.py` read every file in `masks/`.** It now reads `*_mask.nrrd` only, so it
  skips a `.part` left by an interrupted run.
- **`status.sh`** no longer counts `.part` files as fetched metas, and nor does `run_after_sweep.sh`'s summary.
- **Documentation.**
  - The input lists are named. `fetch_metas.sh` reads `patch_dirs.txt`, an 89,237-line listing of the server's
    `verified_patches/`, and the cube fetchers read `all_cubes.txt`. Neither is in the repository, and no script
    here writes them.
  - The `spiral_s1` README carries a dated correction of its "resumable" claim.
  - `run_baseline.sh`'s comment names `run_smoke.sh`, and the run tag as its other difference.
  - `fetch_patches.sh` skips complete files, not complete directories.

## Verified, no change needed

- **The readers.**
  - `select_spiral_patches.py` and `size_spiral_roi.py` glob `metas/*.json`, so a `.part` is never read as a meta.
  - The cube readers open files by exact name, and the patch readers open `x/y/z.tif` by name.
  - The villa fitter's reading of `verified_patches/` could not be checked here: `spiral-fitting/` is not in this
    checkout of villa.
- **The fit drivers.** `run_smoke.sh` and `run_baseline.sh` match the README's account. They differ only in
  `optimizer_num_training_steps` and the run tag.
- **The other fetchers.**
  - `fetch_lasagna.sh`'s `wget -c -O` resumed a partial file correctly against a local server, with and without
    range support.
  - `repro/ink_ablation/fetch_checkpoints.sh` was made atomic in the previous round.
  - `repro/spiral_render/run_interp_vs_labels.sh` fetches into a fresh work directory it refuses to reuse, and stops
    on the first failure.

## Observations for the owner (not changed)

- **Partial files from earlier runs are not repaired.** These fixes stop new partial files. A truncated file left
  under its final name by a run before them is still non-empty, so it is still skipped.
  - For the masks, `characterise_label_cubes.py` stops on it with an `NRRDError`.
  - Elsewhere it would only show where the file is read.
  - Checking sizes against the server's `content-length`, as was done for the lasagna channels, would find any. The
    winding-model shard manifests carry sha256 values that could be checked too. The data host was not reachable
    from this review (proxy 403).
- **The input lists are not committed.** `patch_dirs.txt` and `all_cubes.txt` are not in the repository, so neither
  study's fetch can be re-run from a clone. The ignore rules leave the owner's copies visible, so they can be
  committed.
- **Hardcoded paths.** `run_after_sweep.sh`, `run_smoke.sh`, `run_baseline.sh`, `select_spiral_patches.py` and
  `characterise_label_cubes.py` name `/home/jon/...` directories, as other analyses here do.
- **A short body sent with success** is not caught by the `.part` rename. curl's `--fail` and its own length check
  cover the usual cases.

## Verification

Environment: CPython 3.10 venv, bash 5, GNU coreutils and util-linux `flock`. No network access to
`dl.ash2txt.org`.

- Each fetcher was simulated, old and new, with a stand-in `curl` on `PATH`. It writes `full:<name>` on success, or
  writes `TRUNC` and kills its caller to stand in for an interrupted transfer.
  - `fetch_metas.sh` from a fresh directory: old `fetched=0 misses=3`, new `fetched=3 misses=0`.
  - `fetch_patches.sh` killed on `p2/x.tif`, then re-run: old `TRUNC`, new `full:x.tif`, no `.part` left.
  - `fetch_winding_model.sh` killed on the top-level manifest after a good run: old `TRUNC`, new keeps the good one.
  - `fetch_masks.sh` from a fresh directory: old `masks=0`, new `masks=2`.
  - `fetch_cubes.sh` killed on `c2_volume.nrrd`, then re-run: old `TRUNC`, new `full:c2_volume.nrrd`.
- **New behaviour, simulated:**
  - a second `fetch_patches.sh` beside a running one: `another fetch_patches.sh is running`, rc 1;
  - a worker killed mid-run: `INCOMPLETE (xargs exit 125)`, rc 125;
  - a missing `patches_in_roi.txt`: rc 1, and the existing `patch_misses.txt` is untouched;
  - a cube list with a blank line and no final newline fetches both cubes;
  - `run_after_sweep.sh` with two of three metas and a stale list: `Not writing the fetch list`, then
    `no fetch list written; stopping`, rc 1, and nothing fetched. With all three: `wrote 3 names`, then
    `DONE dirs=3`.
- `characterise_label_cubes.py` over two valid masks and a `.part`: old `NRRDError`, new writes `mask_stats.json`.
- `bash -n` on every script. Ruff clean on the changed Python file.
- `git check-ignore`:
  - ignored: `metas/`, `verified_patches/`, `lasagna_inputs/`, `winding_model/`, the JSON inputs,
    `patches_in_roi.txt`, the miss logs, the lock files, the `.part` files and the cube directories;
  - visible: the tracked scripts and documents, `patch_dirs.txt`, `all_cubes.txt`, and any new `.py` or `.md` there.
  - `git ls-files -ci --exclude-standard` lists no tracked file under `repro/`.
- An independent review of the first commit found that `run_after_sweep.sh` still fetched a stale list when the
  sweep was incomplete, the case it was meant to fix. It also found the concurrency, `xargs`, list-format and
  directory-mismatch issues. All are fixed above.
- The standard suite: see the PR.
