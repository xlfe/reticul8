
docker build . -t local/pio
git submodule update --init

DOCKER_OPT="-v $(pwd):/home/user/workspace --user $(id -u):$(id -g)"
PROTOC="docker run -it --entrypoint /usr/bin/protoc ${DOCKER_OPT} local/pio"

function no() {
mkdir -p menuconfig
	#--entrypoint /home/user/workspace/.cache/packages/framework-espidf/tools/idf.py \
docker run -it \
	--entrypoint /bin/bash \
	-w /home/user/workspace/.cache/packages/framework-espidf/ \
	${DOCKER_OPT} \
	-e IDF_BUILD_ARTIFACTS_DIR=/home/user/workspace/menuconfig/ \
	local/pio
}

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

function none(){
docker run -it \
	${DOCKER_OPT} \
	-e COMPILE_TIME=`date '+%s'` \
	-e PLATFORMIO_CORE_DIR=/home/user/workspace/.cache \
	local/pio \
	run -d /home/user/workspace/micro -e esp32dev 
}
