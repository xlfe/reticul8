FROM python:3.7-slim

RUN pip install -U platformio && \
    mkdir -p /workspace && \
    mkdir -p /.platformio && \
    chmod a+rwx /.platformio && \
    apt-get update && apt-get install -y protobuf-compiler


USER 1000

WORKDIR /workspace

ENTRYPOINT ["platformio"] 
