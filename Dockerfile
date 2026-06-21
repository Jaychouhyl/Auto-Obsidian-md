FROM python:3.12-slim

ARG INSTALL_WHISPER=false

ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        ffmpeg \
        git \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml README.md /app/
COPY src /app/src

RUN python -m pip install --upgrade pip \
    && python -m pip install pypdf yt-dlp \
    && if [ "$INSTALL_WHISPER" = "true" ]; then python -m pip install openai-whisper; fi

ENTRYPOINT ["python", "-m", "obsidian_ingest.cli"]
CMD ["doctor", "--config", "/app/config.docker.toml"]
