FROM ubuntu:latest

ENV TZ="Europe/Kiev"
RUN ln -snf /usr/share/zoneinfo/${TZ} /etc/localtime && echo ${TZ} > /etc/timezone
RUN sed -i 's/^deb http:\/\/archive\./deb http:\/\/ua\.archive\./' /etc/apt/sources.list

RUN apt update \
    && apt upgrade --yes \
    && apt autoremove --yes \
    && apt install --yes --no-install-recommends \
        bash htop git tzdata sudo unzip openssl iputils-ping net-tools \
    && rm -rf /var/lib/apt/lists/*

RUN git config --global http.sslVerify false \
    && git config --global http.postBuffer 1048576000
RUN git clone -b 4.0release https://github.com/ossrs/srs.git

WORKDIR /srs/trunk

RUN apt update \
    && apt install --yes gcc g++ libffi-dev libjpeg-dev zlib1g-dev build-essential libtool automake patch perl \
    && ./configure --srt=on --jobs=$(nproc) && make -j$(nproc) \
    && apt autoremove --yes gcc g++ libffi-dev libjpeg-dev zlib1g-dev build-essential libtool automake patch perl \
    && rm -rf /var/lib/apt/lists/*

COPY srs_prod/hik-docker.conf ./conf/hik-docker.conf
