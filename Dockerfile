FROM python:3.13-alpine3.20

COPY apk_mirrors /etc/apk/repositories

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

RUN --mount=from=ghcr.io/astral-sh/uv,source=/uv,target=/bin/uv \
    --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv venv /opt/venv && uv sync --frozen

COPY . /app
