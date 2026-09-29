`autoresearch.md` describes a `run_single.py` that takes `CUDA_VISIBLE_DEVICES`, `FIT_SPIRAL_RUN_TAG` and `FIT_SPIRAL_OUT_DIR` from the environment and writes `<out_dir>/logs/<tag>.{fit,ink,coverage}.log`. The runner in the repo, `runners/run_single.py` (the one the spiral tutorial points to), takes flags instead. Followed as written, the loop fails in these ways:

- **Launched as documented, it exits before starting:** `python runners/run_single.py` → `error: the following arguments are required: --dataset, --ink-volume`.
- **GPU pinning is silently lost.** `fit_command()` starts `torch.distributed.run` only when `--gpus` lists more than one device. With `CUDA_VISIBLE_DEVICES=0,1,2,3` and no `--gpus`, the fit runs as a single process, and nothing warns.
- **Environment config overrides are silently dropped.** `fit_environment()` removes the caller's `FIT_SPIRAL_CONFIG_OVERRIDES` and sets it only from `--config`. A variant passed through the environment therefore runs as the baseline.
- **W&B stays on.** `fit_environment()` sets `WANDB_MODE` itself, so the documented `WANDB_MODE=disabled` has no effect without `--no-wandb`.
- **Output dirs cannot be shared.** `FIT_SPIRAL_OUT_DIR` is replaced by `--output`, which `require_empty_output()` requires to be new or empty.

This changes only the launch instructions: the runner's path, its flags, `--gpus` for pinning, `--config` for overrides, and the fact that logs are whatever the caller redirects. The loop itself is unchanged.

I checked each point by running `runners/run_single.py` at 6e53201ac with the fit, render and score subprocesses stubbed, and recording the command and environment each step received.
