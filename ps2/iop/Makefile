IOP_BIN = ps2v_sysman.irx
IOP_OBJS = main.o imports.o
IOP_OBJS_DIR ?= obj/
IOP_CFLAGS += -Wall -Wextra -Werror
all: $(IOP_BIN)
$(IOP_OBJS_DIR)main.o: ../rpc_contract.h
clean:
	rm -f $(IOP_BIN) $(IOP_OBJS) ps2v_sysman.notiopmod.elf ps2v_sysman.notiopmod.stripped.elf
include $(PS2SDK)/Defs.make
include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.iopglobal
