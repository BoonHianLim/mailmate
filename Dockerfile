# Base image with CUDA + Ubuntu
FROM nvidia/cuda:12.6.0-cudnn-runtime-ubuntu22.04 AS base

ENV DEBIAN_FRONTEND=noninteractive

# Install system packages
RUN bash -c '\
    for i in {1..5}; do \
    echo "Attempt $i to update and install packages..."; \
    apt-get update && apt-get install -y --no-install-recommends \
    software-properties-common \
    build-essential libsndfile1 \
    git curl ffmpeg libportaudio2 \
    python3 python3-venv python3-pip g++ \
    && break || sleep 10; \
    done; \
    rm -rf /var/lib/apt/lists/* \
    '
# ---------- Assistant Environment ----------
# Create virtual environment for assistant
RUN python3 -m venv /venv/assistant

# Copy assistant requirements
COPY ./assistant/requirements.txt /tmp/assistant-requirements.txt

# Install Python dependencies for assistant
RUN /venv/assistant/bin/pip install --no-cache-dir -r /tmp/assistant-requirements.txt && \
    /venv/assistant/bin/pip install --no-cache-dir funasr modelscope huggingface_hub pywhispercpp torch torchaudio edge-tts azure-cognitiveservices-speech py3-tts

# Install MeloTTS
RUN git clone https://github.com/myshell-ai/MeloTTS.git /opt/MeloTTS && \
    /venv/assistant/bin/pip install --no-cache-dir -e /opt/MeloTTS && \
    /venv/assistant/bin/python -m unidic download && \
    /venv/assistant/bin/python /opt/MeloTTS/melo/init_downloads.py

# Optionally install whisper
ARG INSTALL_WHISPER=false
RUN if [ "$INSTALL_WHISPER" = "true" ]; then \
    /venv/assistant/bin/pip install --no-cache-dir openai-whisper; \
    fi

# Optionally install bark
ARG INSTALL_BARK=false
RUN if [ "$INSTALL_BARK" = "true" ]; then \
    /venv/assistant/bin/pip install --no-cache-dir git+https://github.com/suno-ai/bark.git; \
    fi

# ---------- Another Environment ----------
# Create second venv for "another"
RUN python3 -m venv /venv/another

# Copy and install requirements for the second app
COPY ./requirements.txt /tmp/another-requirements.txt
RUN /venv/another/bin/pip install --no-cache-dir -r /tmp/another-requirements.txt

# ---------- Copy Application Code ----------
# Copy all relevant files
COPY ./assistant /app/assistant
COPY ./fe /app/fe
COPY ./be /app/be
COPY ./start.live.sh /app/start.sh

# Make sure start.sh is executable
RUN chmod +x /app/start.sh

# ---------- Default Entrypoint ----------
# You can switch to either app by changing CMD
# This runs the assistant by default
EXPOSE 8101 8501 12393
WORKDIR /app/
CMD ["./start.sh"]