# 1. Use Python 3.13 (matching your requires-python)
FROM python:3.13-slim

# 2. Install system dependencies (libsndfile is required for audio processing)
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 3. Install 'uv' by copying it from the official Astral image
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

# 4. Set environment variables
# HF_HOME: Where Hugging Face models will be saved
# UV_COMPILE_BYTECODE: Compiles Python to run faster
ENV HF_HOME="/app/model_cache"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

WORKDIR /app

# 5. Install Dependencies
# We copy ONLY pyproject.toml first to cache dependencies
COPY pyproject.toml .

# Run uv sync. This creates a virtual environment at /app/.venv
# --no-dev: Skips development dependencies (if you had any)
# --no-install-project: Installs libraries but not your code yet
RUN uv sync --no-dev --no-install-project

# 6. Add the virtual environment to the PATH
# This "activates" the environment for all future commands
ENV PATH="/app/.venv/bin:$PATH"

# 7. Pre-download the AI Model
# We run this NOW so the model is saved inside the Docker image
RUN python -c "from verifyvoice import ModelLoader; \
    print('⏳ Pre-downloading WavLM model...'); \
    ModelLoader(model_name='WavLM', attention_heads=8); \
    print('✅ Model downloaded to /app/model_cache')"

# 8. Copy the rest of your application code
COPY . .

# 9. Create storage directories
RUN mkdir -p storage/audio storage/embeddings

EXPOSE 8000

# 10. Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]