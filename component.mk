SHELL := /bin/bash

#Used for build timestamp
CPPFLAGS += -D"__COMPILE_TIME__ =`date '+%s'`"

# Optional list of git submodule paths (relative to COMPONENT_PATH) used by the component.
# These will be checked (and initialised if necessary) by the build process. This variable is
# ignored if the component is outside the IDF_PATH directory.
COMPONENT_SUBMODULES := PJON nanopb zlib


# pjon

COMPONENT_ADD_INCLUDEDIRS += PJON/src


# zlib

CPPFLAGS += -DNO_GZIP
COMPONENT_ADD_INCLUDEDIRS += zlib_micro
COMPONENT_SRCDIRS += zlib_micro


# nanopb

include $(abspath $(COMPONENT_PATH)/nanopb/extra/nanopb.mk)
PGEN_DIR := $(COMPONENT_PATH)/nanopb/generator/proto
COMPONENT_ADD_INCLUDEDIRS += nanopb
COMPONENT_SRCDIRS += nanopb
PROTOC_OPTS += -I$(abspath $(COMPONENT_PATH)/nanopb/generator/proto)

$(COMPONENT_PATH)/python/reticul8/%_pb2.py: $(PGEN_DIR)/%.proto
	$(PROTOC) $(PROTOC_OPTS) --proto_path=$(PGEN_DIR) --python_out=$(COMPONENT_PATH)/python/reticul8/ $<


# reticul8 - protoc

$(COMPONENT_PATH)/micro/reticul8.pb.c: $(COMPONENT_PATH)/reticul8.proto
	$(PROTOC) $(PROTOC_OPTS) --nanopb_out=$(COMPONENT_PATH)/micro/ --proto_path=$(COMPONENT_PATH) reticul8.proto

$(COMPONENT_PATH)/python/reticul8/reticul8_pb2.py: $(COMPONENT_PATH)/reticul8.proto
	$(PROTOC) $(PROTOC_OPTS) --python_out=$(COMPONENT_PATH)/python/reticul8 --proto_path=$(COMPONENT_PATH) reticul8.proto

$(COMPONENT_PATH)/java/src/net/xlfe/reticul8/Reticul8.java: $(COMPONENT_PATH)/reticul8.proto
	$(PROTOC) $(PROTOC_OPTS) --java_out=$(COMPONENT_PATH)/java/src/ --proto_path=$(COMPONENT_PATH) reticul8.proto

build:  $(COMPONENT_PATH)/micro/reticul8.pb.c \
        $(COMPONENT_PATH)/java/src/net/xlfe/reticul8/Reticul8.java \
        $(COMPONENT_PATH)/python/reticul8/nanopb_pb2.py \
        $(COMPONENT_PATH)/python/reticul8/plugin_pb2.py \
        $(COMPONENT_PATH)/python/reticul8/reticul8_pb2.py


# reticul8

COMPONENT_ADD_INCLUDEDIRS += micro
COMPONENT_SRCDIRS += micro

COMPONENT_SRC += $(COMPONENT_PATH)/micro/reticul8.pb.c
