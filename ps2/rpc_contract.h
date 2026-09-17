#ifndef PS2V_RPC_CONTRACT_H
#define PS2V_RPC_CONTRACT_H
/* A separate service ID: do not bind an already loaded BIOSDrain sysman. */
#define PV_RPC_ID 0x50533256
#define PV_RPC_READ 1
#define PV_ROM0 0xbfc00000u
#define PV_ROM0_SIZE 0x400000u
#define PV_BLOCK 0x4000u
typedef struct {
    unsigned int address;
    unsigned int destination;
    unsigned int size;
} pv_read_request;
#endif
