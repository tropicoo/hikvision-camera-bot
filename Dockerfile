# Multi-arch image: works on x86_64 and on Raspberry Pi 4/5 (64-bit OS, arm64).
FROM python:3.13-alpine3.22

ENV VIRTUAL_ENV=/opt/venv
ENV PATH="/opt/venv/bin:$PATH"
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_PROJECT_ENVIRONMENT=/opt/venv
ENV UV_PYTHON_DOWNLOADS=never

RUN apk add --no-cache \
        ffmpeg \
        tzdata \
        jpeg-dev \
        htop \
        bash

WORKDIR /app

RUN --mount=from=ghcr.io/astral-sh/uv:0.8,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv venv /opt/venv && uv sync --frozen --no-dev

COPY . /app

# The bot refreshes the heartbeat file every 30 seconds while its event loop works.
HEALTHCHECK --interval=60s --timeout=10s --start-period=120s --retries=3 \
    CMD python -c "import os, sys, time; sys.exit(time.time() - os.path.getmtime('/tmp/hikcamerabot.heartbeat') > 120)"

CMD ["python", "./bot.py"]
