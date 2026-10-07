SOURCE_KIND ?= 0
HOLD_VBLANKS ?= 6
VIDEO_INTERLACED ?= 0
INTERACTIVE ?= 0
EE_BIN = ps2-video-backup.elf
EE_OBJS = main.o wire.o source.o sysman_client.o control.o menu.o ps2v_sysman_irx.o
EE_LIBS = -ldraw -lgraph -lpacket -ldma -lpad -lpatches -lkernel
EE_CFLAGS += -Wall -Wextra -Werror -DSOURCE_KIND=$(SOURCE_KIND) -DHOLD_VBLANKS=$(HOLD_VBLANKS) -DVIDEO_INTERLACED=$(VIDEO_INTERLACED) -DINTERACTIVE=$(INTERACTIVE)
.PHONY: all clean FORCE
all: $(EE_BIN)
main.o: FORCE
$(EE_BIN): FORCE
main.o: source.h wire.h control.h menu.h
control.o: control.h
menu.o: menu.h control.h wire.h
wire.o: wire.h
source.o: source.h wire.h sysman_client.h
sysman_client.o: sysman_client.h rpc_contract.h
ps2v_sysman_irx.o: FORCE
FORCE:
iop/ps2v_sysman.irx: FORCE
	$(MAKE) -C iop
ps2v_sysman_irx.c: iop/ps2v_sysman.irx
	bin2c $< $@ ps2v_sysman_irx
clean:
	$(MAKE) -C iop clean
	rm -f $(EE_BIN) $(EE_OBJS) ps2v_sysman_irx.c
include $(PS2SDK)/samples/Makefile.pref
include $(PS2SDK)/samples/Makefile.eeglobal
