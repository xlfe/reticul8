FROM python:3.7-slim

RUN useradd -m -U -u 1000 user
RUN apt-get update && apt-get install -y protobuf-compiler make g++ git libncurses-dev flex bison gperf
USER user

RUN pip install -U --user platformio \
	grpcio-tools nanopb \
	protobuf setuptools "pyserial>=3.0" "future>=0.15.2" "cryptography>=2.1.4" "pyparsing>=2.0.3,<2.4.0" && \
    mkdir -p ~/workspace && \
    mkdir -p ~/.platformio 

WORKDIR /home/user/workspace
ENV PATH="/home/user/.local/bin:${PATH}"
ENV COMPILE_TIME=1234
ENTRYPOINT ["/home/user/.local/bin/pio"]
