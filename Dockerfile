FROM python:3-alpine

RUN apk update && apk add --no-cache bash gcc python3-dev musl-dev git openssh-client

# We copy just the requirements.txt first to leverage Docker cache
COPY ./requirements.txt /app/requirements.txt

WORKDIR /app

RUN  apk update && apk add -qU openssh
RUN apk add libmagic libffi-dev openssl-dev python3-dev jpeg-dev \
            zlib-dev cairo-dev pango-dev gdk-pixbuf-dev ttf-freefont ffmpeg
RUN pip install --upgrade pip setuptools wheel && pip install -r requirements.txt

COPY . /app

CMD ["python", "bot.py"]
