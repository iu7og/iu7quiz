# IU7Quiz Environment

FROM python:3.8-alpine
LABEL maintainer="IU7OG"

ENV PYTHONBUFFERED 1

RUN apk add --update --no-cache tzdata \
    && cp /usr/share/zoneinfo/Europe/Moscow /etc/localtime \
    && echo "Europe/Moscow" > /etc/timezone
RUN apk add --update --no-cache --virtual .tmp-build-deps \
    snappy snappy-dev krb5-dev g++

COPY image/requirements.txt /requirements.txt
COPY image/standard.rc /standard.rc
RUN python -m pip install -r /requirements.txt

RUN apk del .tmp-build-deps

RUN mkdir /bot
WORKDIR /bot
COPY ./bot /bot

RUN adduser -D quizer
USER quizer