/* Read path adapted from BIOSDrain sysman/main.c.
 * Copyright 2022 Ty Lamontagne (Fobes)
 * SPDX-License-Identifier: MIT
 * Full original notice: ../LICENSES/BIOSDrain-MIT.txt.
 * Reduced to ROM0 only; validate every request; wait for the LAST DMA before
 * returning RPC success. No memory write RPC or peripheral initializers.
 */
#include <irx.h>
#include <loadcore.h>
#include <thbase.h>
#include <sifcmd.h>
#include <sifman.h>
#include <intrman.h>
#include <sysclib.h>
#include "../rpc_contract.h"
IRX_ID("PS2V_ROM0", 1, 0);
static SifRpcServerData_t server;
static SifRpcDataQueue_t queue;
static unsigned char rpc_buffer[64] __attribute__((aligned(16)));
static unsigned char block[PV_BLOCK] __attribute__((aligned(16)));
static int response[4] __attribute__((aligned(16)));

static void *handler(int fno, void *buffer, int size)
{
    pv_read_request *r = buffer;
    SifDmaTransfer_t dma;
    int old_state, id, tries;
    response[0] = -1;
    if (fno != PV_RPC_READ || size != sizeof(*r)) return response;
    if (!r->size || r->size > PV_BLOCK || (r->size & 63) ||
        (r->address & 63) || (r->destination & 63) ||
        r->address < PV_ROM0 || r->address-PV_ROM0 > PV_ROM0_SIZE-r->size ||
        r->destination < 0x100000u || r->destination > 0x02000000u-r->size) return response;
    memcpy(block, (const void *)r->address, r->size);
    dma.src = block; dma.dest = (void *)r->destination;
    dma.size = r->size; dma.attr = SIF_DMA_FROM_IOP;
    id = 0;
    for (tries = 0; tries < 10000 && !id; ++tries) {
        CpuSuspendIntr(&old_state);
        id = sceSifSetDma(&dma, 1);
        CpuResumeIntr(old_state);
    }
    if (!id) return response;
    /* The source buffer must remain alive and unchanged through completion. */
    while (sceSifDmaStat(id) >= 0) { }
    response[0] = 0;
    return response;
}
static void serve(void *unused)
{
    (void)unused;
    sceSifSetRpcQueue(&queue, GetThreadId());
    sceSifRegisterRpc(&server, PV_RPC_ID, handler, rpc_buffer, 0, 0, &queue);
    sceSifRpcLoop(&queue);
}
int _start(int argc, char **argv)
{
    iop_thread_t thread;
    int id;
    (void)argc; (void)argv;
    memset(&thread, 0, sizeof(thread));
    thread.attr = TH_C; thread.thread = serve;
    thread.priority = 40; thread.stacksize = 0x1000;
    id = CreateThread(&thread);
    if (id < 0) return MODULE_NO_RESIDENT_END;
    if (StartThread(id, 0) < 0) { DeleteThread(id); return MODULE_NO_RESIDENT_END; }
    return MODULE_RESIDENT_END;
}
