# 1. Use Python 3.13 (matching your requires-python)
FROM python:3.13-slim

# 2. Install system dependencies (libsndfile is required for audio processing)
# gcc and build-essential are required to compile webrtcvad for Python 3.13
RUN apt-get update && apt-get install -y \
    libsndfile1 \
    ffmpeg \
    gcc \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 3. Set environment variables
# HF_HOME: Where Hugging Face models will be saved
ENV HF_HOME="/app/model_cache"
# Prevent Python from writing pyc files to disc
ENV PYTHONDONTWRITEBYTECODE=1
# Prevent Python from buffering stdout and stderr
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# 4. Install Dependencies
COPY requirements.txt .

# Remove 'torch' from requirements.txt to prevent it from overriding our CPU install
RUN sed -i '/torch/d' requirements.txt

# Install CPU-only torch explicitly first
RUN pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
# We use --extra-index-url so if any package (like verifyvoice) needs torch, 
# it can see the CPU version is valid and available.
RUN pip install --no-cache-dir -r requirements.txt --extra-index-url https://download.pytorch.org/whl/cpu

# 5. Pre-download the AI Model
# We run this NOW so the model is saved inside the Docker image
RUN python -c "from verifyvoice import ModelLoader; \
    print('⏳ Pre-downloading WavLM model...'); \
    ModelLoader(model_name='WavLM', attention_heads=8); \
    print('✅ Model downloaded to /app/model_cache')"

# 6. Copy the rest of your application code
COPY . .

# 7. Create storage directories
RUN mkdir -p storage/audio storage/embeddings

EXPOSE 8000

# 8. Start the app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]