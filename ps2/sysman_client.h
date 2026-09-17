#ifndef PS2V_SYSMAN_CLIENT_H
#define PS2V_SYSMAN_CLIENT_H
int pv_sysman_init(void);
int SysmanReadMemory(const void *address, void *buffer, unsigned int size);
int pv_rom0_snapshot(void *buffer, unsigned int size);
#endif
