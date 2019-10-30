FROM python:3.7-slim

RUN useradd -m -U -u 1000 user
RUN apt-get update && apt-get install -y protobuf-compiler cmake g++
USER user

RUN pip install -U --user platformio protobuf setuptools "pyserial>=3.0" "future>=0.15.2" "cryptography>=2.1.4" "pyparsing>=2.0.3,<2.4.0" && \
    mkdir -p ~/workspace && \
    mkdir -p ~/.platformio 

WORKDIR /home/user/workspace

ENTRYPOINT ["/home/user/.local/bin/pio"] 
