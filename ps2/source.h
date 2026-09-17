#ifndef PS2V_SOURCE_H
#define PS2V_SOURCE_H
#include "wire.h"
/* kind=0 TEST 64 KiB; kind=1 ROM0 prefix64K; kind=2 full ROM0 */
int pv_source_open(pv_object *object, int kind);
void pv_source_close(pv_object *object);
#endif
