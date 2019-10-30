FROM python:3.7-slim

RUN useradd -m -U -u 1000 user
RUN apt-get update && apt-get install -y protobuf-compiler
USER user

RUN pip install -U --user platformio && \
    mkdir -p ~/workspace && \
    mkdir -p ~/.platformio 

WORKDIR /home/user/workspace

ENTRYPOINT ["/home/user/.local/bin/pio"] 
