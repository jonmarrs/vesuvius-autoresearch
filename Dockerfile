# Use NVIDIA PyTorch base image for GPU support
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
