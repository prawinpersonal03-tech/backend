# Use Python base image
FROM python:3.10-slim

# Install system packages (FFmpeg required for Whisper)
RUN apt-get update && apt-get install -y ffmpeg git && apt-get clean

# Create working directory
WORKDIR /app

# Copy requirements first (better caching)
COPY requirements.txt .

# Install Python packages
RUN pip install --no-cache-dir -r requirements.txt

# Copy all backend files
COPY . .

# Expose the port Cloud Run will use
EXPOSE 8080

# Start the Flask app
CMD ["python", "whisper_server.py"]
