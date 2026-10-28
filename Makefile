# Vesuvius Autoresearch — common dev tasks.
#
# All targets run inside the project's uv-managed venv. If `uv` is not on
# PATH, install it: `curl -LsSf https://astral.sh/uv/install.sh | sh`.

.PHONY: help install smoke test reeval shift clean clean-cache check-deps status

help:
	@echo "Common targets:"
	@echo "  make install      uv sync — install / update project dependencies"
	@echo "  make smoke        run scripts/smoke_test.py (CPU-only, ~20s)"
	@echo "  make test         alias for smoke"
	@echo "  make reeval       re-evaluate best_model.pt under today's code path"
	@echo "  make shift        spawn an autoresearch bandit shift in background"
	@echo "  make check-deps   verify GPU + key imports"
	@echo "  make status       read-only setup/process check (no ML dependencies or CUDA)"
	@echo "  make clean        remove old launchers' stdout logs (keeps run.log and sprint_logs/)"
	@echo "  make clean-cache  also remove __pycache__ and valid_coords_*.npy"

install:
	uv sync

smoke:
	CUDA_VISIBLE_DEVICES="" uv run python scripts/smoke_test.py

test: smoke

status:
	@python3 scripts/workspace_status.py

reeval:
	uv run python scripts/reevaluate_best_model.py

# Spawn a shift via nohup so it survives terminal disconnect. The loop
# auto-detects DAY (07-19) vs NIGHT (19-07) from the system clock (local time).
shift:
	@bash start.sh

check-deps:
	@uv run python -c "import torch; print('torch:', torch.__version__, 'cuda:', torch.cuda.is_available())"
	@uv run python -c "import scripts.training.train, vesuvius_autoresearch.core.vesuvius_loader, vesuvius_autoresearch.core.model_wrappers, run_autoresearch_loop; print('main modules import OK')"
	@nvidia-smi --query-gpu=name,memory.total --format=csv,noheader 2>/dev/null || echo "(no GPU detected; CPU-only mode)"

# Not run.log: it is the cycles' training output, git-ignored and so on this machine
# only. scripts/epoch_boundary_overhead.py and cycle_length_gain.py read it for each
# cycle's step count, and a running cycle is writing it.
clean:
	rm -f shift_stdout_*.log dayshift_stdout.log nightshift_stdout.log /tmp/reeval.log /tmp/fiber_gen.log

clean-cache: clean
	find . -name __pycache__ -type d -exec rm -rf {} + 2>/dev/null || true
	find . -maxdepth 2 -name "valid_coords_*.npy" -delete 2>/dev/null || true
