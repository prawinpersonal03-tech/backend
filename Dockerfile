# Use official PyTorch CPU image (already contains torch + torchaudio)
FROM pytorch/pytorch:2.2.0-cpu

# Avoid interactive prompts, install ffmpeg + libav* development packages + git
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ffmpeg \
    git \
    libavdevice-dev \
    libavfilter-dev \
    libavformat-dev \
    libavcodec-dev \
    libswresample-dev \
    libswscale-dev \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set working dir
WORKDIR /app

# Copy requirements first for caching benefit
COPY requirements.txt .

# Ensure pip tooling is up-to-date and install Python deps EXCEPT torch/torchaudio
# (The base image already contains torch and torchaudio. We filter them out from requirements.)
RUN python -m pip install --upgrade pip setuptools wheel \
  && sed '/^torch/Id;/^torchaudio/Id' requirements.txt > /tmp/req_trimmed.txt \
  && pip install --no-cache-dir -r /tmp/req_trimmed.txt \
  && pip install --no-cache-dir gunicorn

# Copy app sources
COPY . .

# Expose port Cloud Run expects
EXPOSE 8080

# Run with gunicorn (production server). Increase timeout for long transcriptions.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "whisper_server:app", "--timeout", "300", "--workers", "1", "--threads", "2"]
