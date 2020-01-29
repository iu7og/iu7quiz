# IU7Quiz Environment

FROM python:3.8-alpine
LABEL maintainer="IU7OG"

ENV PYTHONBUFFERED 1

RUN apk add --no-cache tzdata \
    && cp /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
    && echo "Europe/Moscow" > /etc/timezone
RUN apk add --no-cache --virtual .tmp-build-deps \
    snappy snappy-dev krb5-dev g++

COPY ./cfg /cfg
RUN python -m pip install -r /cfg/requirements.txt

RUN apk del .tmp-build-deps

RUN mkdir /bot
WORKDIR /bot
COPY ./bot /bot

RUN adduser -D iu7og
USER iu7og