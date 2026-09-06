# Use NVIDIA PyTorch base image for GPU support
#
# SYSTEM REQUIREMENTS, measured 2026-09-06 rather than estimated:
#   * ~60 GB of free disk to BUILD. The nvcr.io CUDA base plus `uv sync` of 248
#     packages (Torch, CUDA wheels) consumed roughly that much before the build
#     was aborted; budget it before starting, on pain of filling the host.
#   * An NVIDIA GPU at run time.
#   * The base image pulls anonymously from nvcr.io (verified 2026-09-06).
#
# For a small, fully self-contained reproduction that needs NO GPU, no network
# and ~200 MB, use ScrollGT's image instead: github.com/jonmarrs/scrollgt.
#
# NOT verified end to end: this Dockerfile has never been built to completion
# here. What has been checked is that every file it copies exists, its CMD
# target exists, the base image is pullable, and `uv lock --check` passes so
# `uv sync --frozen` resolves. Treat it as "no known breakage", not "verified".
FROM nvcr.io/nvidia/pytorch:24.03-py3

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast dependency management
RUN curl -LsSf https://astral.sh/uv/install.sh | sh
ENV PATH="/root/.local/bin:${PATH}"

# Copy project files
COPY pyproject.toml uv.lock ./
COPY README.md SUBMISSION.md ./
COPY *.py ./

# Synchronize dependencies
RUN uv sync --frozen

# Default command: Run the Mission-Critical Audit
CMD ["uv", "run", "vesuvius_model.py"]
