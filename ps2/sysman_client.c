/* Adapted from BIOSDrain SysmanReadMemory/read loop.
 * Copyright 2022 Ty Lamontagne (Fobes)
 * SPDX-License-Identifier: MIT
 * Full original notice: LICENSES/BIOSDrain-MIT.txt.
 * Changes: read-only separate RPC service, synchronous call, strict range,
 * explicit cache ownership and error propagation. No USB/network/file output.
 */
#include <kernel.h>
#include <sifrpc.h>
#include <loadfile.h>
#include <sbv_patches.h>
#include <graph.h>
#include <stdint.h>
#include "rpc_contract.h"
#include "sysman_client.h"
extern unsigned char ps2v_sysman_irx[];
extern unsigned int size_ps2v_sysman_irx;
static SifRpcClientData_t client __attribute__((aligned(64)));
static pv_read_request request __attribute__((aligned(64)));
static int response[16] __attribute__((aligned(64)));

int pv_sysman_init(void)
{
    int result, module, tries;
    if (client.server) return 0;
    SifInitRpc(0);
    if (sbv_patch_enable_lmb() < 0) return -1;
    module = SifExecModuleBuffer(ps2v_sysman_irx, size_ps2v_sysman_irx, 0, 0, &result);
    if (module < 0 || result != 0) return -1;
    for (tries = 0; tries < 300; ++tries) {
        if (SifBindRpc(&client, PV_RPC_ID, 0) >= 0 && client.server) return 0;
        graph_wait_vsync();
    }
    return -1;
}
int SysmanReadMemory(const void *address, void *buffer, unsigned int size)
{
    unsigned int src = (unsigned int)(uintptr_t)address;
    int result;
    if (!client.server || !size || size > PV_BLOCK || (size & 63) ||
        ((uintptr_t)buffer & 63) || (src & 63) ||
        src < PV_ROM0 || size > PV_ROM0_SIZE || src-PV_ROM0 > PV_ROM0_SIZE-size) return -1;
    request.address = src;
    request.destination = (unsigned int)(uintptr_t)buffer & 0x1fffffffu;
    request.size = size;
    /* No EE writes to this range until the RPC and final IOP DMA complete. */
    SyncDCache(buffer, (unsigned char *)buffer+size);
    response[0] = -1;
    result = SifCallRpc(&client, PV_RPC_READ, 0, &request, sizeof(request),
                        response, sizeof(int), 0, 0);
    if (result < 0) return result;
    InvalidDCache(buffer, (unsigned char *)buffer+size);
    return response[0];
}
int pv_rom0_snapshot(void *buffer, unsigned int size)
{
    unsigned int offset;
    if (size != 0x10000u && size != PV_ROM0_SIZE) return -1;
    for (offset = 0; offset < size; offset += PV_BLOCK) {
        int result = SysmanReadMemory((void *)(uintptr_t)(PV_ROM0+offset),
                                      (unsigned char *)buffer+offset, PV_BLOCK);
        if (result != 0) return result;
    }
    return 0;
}
