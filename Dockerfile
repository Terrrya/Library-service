FROM python:3.11.2-slim-buster

LABEL maintainer="terrya@ukr.net"

ENV PYTHONUNBUFFERED 1

WORKDIR app/

RUN apt-get update \
    && apt-get -y install libpq-dev gcc

COPY . .

RUN pip install --upgrade pip

RUN pip install -r requirements.txt
