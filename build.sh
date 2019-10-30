
PROTOC_OPTS=-Inanopb/generator/proto 

docker build . -t local/pio

PROTOC="docker run -it --entrypoint /usr/bin/protoc -v $(pwd):/home/user/workspace --user $(id -u):$(id -g) local/pio"

# nanopb - compile java protobufs
$PROTOC --java_out=java/src/ --proto_path=nanopb/generator/proto nanopb.proto

# reticul8 protobufs
$PROTOC ${PROTOC_OPTS} \ 
	--python_out=python/reticul8 \
       	--nanopb_out=micro/src/ \
	--java_out=java/src/ \
	reticul8.proto

	#--proto_path=. \

docker run -it -v $(pwd):/workspace -e COMPILE_TIME=`date '+%s'` -e PLATFORMIO_CORE_DIR=/workspace/.cache local/pio run -d micro -e esp32dev 
