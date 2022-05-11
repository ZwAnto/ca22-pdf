FROM python:3.8.13-slim-buster

RUN apt-get update && apt-get install -y curl git locales
RUN locale-gen fr_FR.UTF-8
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH /root/.local/bin:$PATH