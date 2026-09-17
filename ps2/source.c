/* SPDX-License-Identifier: MIT */
#include "source.h"
#include <malloc.h>
#include <stdlib.h>
#include <string.h>
#include "sysman_client.h"
typedef struct { uint8_t *data; uint32_t size; } snapshot;
static int read_snapshot(void *context, uint32_t offset, void *out, uint32_t size)
{
    snapshot *s = context;
    if (offset > s->size || size > s->size-offset) return -1;
    memcpy(out, s->data+offset, size);
    return 0;
}
int pv_source_open(pv_object *object, int kind)
{
    snapshot *s;
    if (kind < 0 || kind > 2) return -1;
    s = calloc(1, sizeof(*s));
    if (!s) return -1;
    s->size = kind == 2 ? 0x400000u : 0x10000u;
    s->data = memalign(64, s->size);
    if (!s->data) { free(s); return -1; }
    if (kind == 0) pv_test_data(s->data, s->size);
    else if (pv_sysman_init() || pv_rom0_snapshot(s->data, s->size)) {
        free(s->data); free(s); return -1;
    }
    object->type = kind ? 1 : 0;
    object->size = s->size; object->context = s; object->read = read_snapshot;
    return 0;
}
void pv_source_close(pv_object *object)
{
    snapshot *s = object->context;
    if (s) { free(s->data); free(s); }
    memset(object, 0, sizeof(*object));
}
