#!/bin/bash

mkdir -p .platformio
docker build . -t net.xlfe/reticul8
git submodule update --init

PROTOC="docker run -it --entrypoint /usr/bin/protoc -v $(pwd):/home/user/workspace --user $(id -u):$(id -g) net.xlfe/reticul8"

mkdir -p java/src/
# nanopb 
${PROTOC} --python_out=nanopb/generator/proto --proto_path=nanopb/generator/proto nanopb/generator/proto/*.proto
${PROTOC} --java_out=java/src/ --proto_path=nanopb/generator/proto nanopb.proto

# reticul8 
${PROTOC} -Inanopb/generator/proto \
	--python_out=python/reticul8 \
       	--nanopb_out=micro/src/ \
	--java_out=java/src/ \
	--plugin=protoc-gen-nanopb=nanopb/generator/protoc-gen-nanopb \
	--proto_path=. \
	reticul8.proto

mv -f micro/src/reticul8.pb.h micro/include/

EXTRA_DEVS="$1"

function pio() {
	docker run -it \
		-v $(pwd):/home/user/workspace \
		-v $(pwd)/.platformio:/home/user/.platformio \
		--user $(id -u):$(id -g) \
		--workdir /home/user/workspace/micro \
		${EXTRA_DEVS} net.xlfe/reticul8 $@
}

echo "now try some pio commands, like:\n
# pio run -t menuconfig
# pio run -t upload"

