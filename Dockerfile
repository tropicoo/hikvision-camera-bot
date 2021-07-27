FROM python:3.9-alpine

RUN apk add --no-cache \
        ffmpeg \
        tzdata \
        jpeg-dev \
        htop \
        bash

COPY ./requirements.txt /app/requirements.txt

WORKDIR /app
RUN apk add --no-cache --virtual .build-deps \
    linux-headers libffi-dev zlib-dev build-base && \
    pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt && \
    apk --purge del .build-deps

COPY . /app

CMD ["python", "bot.py"]
