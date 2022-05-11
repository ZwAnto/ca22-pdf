FROM python:3.8.13-slim-buster

RUN apt-get update && apt-get install -y curl git
RUN curl -sSL https://install.python-poetry.org | python3 -

ENV PATH /root/.local/bin:$PATH