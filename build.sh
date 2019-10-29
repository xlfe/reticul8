
docker build . -t local/pio
docker run -it -v $(pwd)/micro/:/workspace -e PLATFORMIO_CORE_DIR=/workspace/.cache local/pio run -e esp32dev 
