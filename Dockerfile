# Use a slim Python base
FROM python:3.10-slim

# Install system deps (ffmpeg + codecs + libs) and git
RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
    ffmpeg \
    git \
    libsndfile1 \
    libavcodec-extra \
  && apt-get clean \
  && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Upgrade pip and install PyTorch CPU wheels from the official PyTorch wheel index,
# then install remaining Python dependencies (we remove torch/torchaudio from reqs to avoid duplicate install).
RUN python -m pip install --upgrade pip setuptools wheel \
 && pip install --no-cache-dir --extra-index-url https://download.pytorch.org/whl/cpu torch torchaudio \
 && sed '/^torch/Id;/^torchaudio/Id' requirements.txt > /tmp/req_trimmed.txt \
 && pip install --no-cache-dir -r /tmp/req_trimmed.txt \
 && pip install --no-cache-dir gunicorn

# Copy app code
COPY . .

# Expose port Cloud Run expects
EXPOSE 8080

# Use gunicorn (production-ready) and allow longer timeout for long audio jobs
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "whisper_server:app", "--timeout", "300", "--workers", "1", "--threads", "2"]
