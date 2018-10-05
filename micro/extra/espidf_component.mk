RETICUL8_DIR := $(PROJECT_PATH)/components/reticul8
NANOPB_DIR := $(RETICUL8_DIR)/nanopb
PGEN_DIR := $(NANOPB_DIR)/generator/proto

include $(abspath $(NANOPB_DIR)/extra/nanopb.mk)
# nanopb
COMPONENT_EXTRA_INCLUDES += $(NANOPB_DIR)
COMPONENT_SRCDIRS += ../components/reticul8/nanopb
PROTOC_OPTS += -I$(PGEN_DIR)

$(RETICUL8_DIR)/python/reticul8/%_pb2.py: $(PGEN_DIR)/%.proto
	$(PROTOC) $(PROTOC_OPTS) --proto_path=$(PGEN_DIR) --python_out=$(RETICUL8_DIR)/python/reticul8/ $<

# reticul8 - protoc
$(RETICUL8_DIR)/micro/reticul8.pb.c: $(RETICUL8_DIR)/reticul8.proto
	$(PROTOC) $(PROTOC_OPTS) --nanopb_out=$(RETICUL8_DIR)/micro/ --proto_path=$(RETICUL8_DIR) reticul8.proto

$(RETICUL8_DIR)/python/reticul8/reticul8_pb2.py: $(RETICUL8_DIR)/reticul8.proto
	$(PROTOC) $(PROTOC_OPTS) --python_out=$(RETICUL8_DIR)/python/reticul8/ --proto_path=$(RETICUL8_DIR) reticul8.proto

COMPONENT_SRC += $(RETICUL8_DIR)/micro/reticul8.pb.c
build:  $(RETICUL8_DIR)/micro/reticul8.pb.c \
        $(RETICUL8_DIR)/python/reticul8/nanopb_pb2.py \
        $(RETICUL8_DIR)/python/reticul8/plugin_pb2.py \
        $(RETICUL8_DIR)/python/reticul8/reticul8_pb2.py


# reticul8
COMPONENT_EXTRA_INCLUDES += $(RETICUL8_DIR)/micro
COMPONENT_SRCDIRS += ../components/reticul8/micro/

