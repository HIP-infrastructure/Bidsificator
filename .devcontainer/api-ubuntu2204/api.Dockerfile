#FROM amd64/ubuntu:22.04
FROM ubuntu:22.04

USER root

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install --no-install-recommends -y \ 
    python3 python3-pip python3.10-venv && \
    python3 -m venv .env

# Note : Need to comment Qt6 installation for now in requirements since 
# there is some incompatibility between setuptools-70.0.0 and Qt6 
# (Only when testing API, not for the main app)
COPY ./requirements.txt .
RUN pip install -r requirements.txt