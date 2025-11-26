FROM python:3.10-slim

# Install unzip
RUN apt-get update && apt-get install -y \
    build-essential \
    libasound2-dev \
    libportaudio2 \
    libportaudiocpp0 \
    ffmpeg \
    wget \
    unzip \
    espeak \
    libespeak1 \
    alsa-utils \
    && rm -rf /var/lib/apt/lists/*

# Set workdir
WORKDIR /app

# Copy requirements and install python dependencies
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables (override as needed)
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# Entrypoint
CMD ["python", "-m", "jetvoice.runner"]
