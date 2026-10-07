/* SPDX-License-Identifier: MIT */
#include "wire.h"
#include <string.h>
const pv_grid *pv_grid_get(unsigned profile)
{
    static const pv_grid grids[] = {{36,20,8},{48,26,6},{72,40,4}};
    return profile < 3 ? &grids[profile] : 0;
}
unsigned pv_packet_size(unsigned profile)
{
    const pv_grid *g = pv_grid_get(profile);
    return g ? g->cols*g->rows/4 : 0;
}
unsigned pv_capacity(unsigned profile)
{
    unsigned size = pv_packet_size(profile);
    return size ? size-48 : 0;
}
uint32_t pv_count(uint32_t size, unsigned profile)
{
    unsigned capacity = pv_capacity(profile);
    return capacity ? (size ? 1u+(size-1u)/capacity : 1u) : 0;
}

uint32_t pv_crc_update(uint32_t state, const void *data, size_t size)
{
    const uint8_t *p = data;
    while (size--) {
        unsigned bit;
        state ^= *p++;
        for (bit = 0; bit < 8; ++bit)
            state = (state >> 1) ^ (0xedb88320u & (0u - (state & 1u)));
    }
    return state;
}
uint32_t pv_crc(const void *data, size_t size)
{
    return pv_crc_update(0xffffffffu, data, size) ^ 0xffffffffu;
}
uint32_t pv_frame_count(uint32_t size)
{
    return size ? 1u + (size - 1u) / PV_PAYLOAD : 1u;
}
int pv_object_crc(const pv_object *object, uint32_t *crc)
{
    uint8_t block[1024];
    uint32_t offset = 0, state = 0xffffffffu;
    while (offset < object->size) {
        uint32_t n = object->size - offset;
        if (n > sizeof(block)) n = sizeof(block);
        if (object->read(object->context, offset, block, n)) return -1;
        state = pv_crc_update(state, block, n);
        offset += n;
    }
    *crc = state ^ 0xffffffffu;
    return 0;
}
static void put32(uint8_t *out, uint32_t value)
{
    unsigned i;
    for (i = 0; i < 4; ++i) out[i] = (uint8_t)(value >> (8*i));
}
int pv_packet(const pv_object *object, uint32_t session, uint32_t source_crc,
              uint32_t index, uint8_t out[PV_PACKET])
{
    return pv_packet_profile(object, session, source_crc, index, 0, 1, out);
}
int pv_packet_profile(const pv_object *object, uint32_t session, uint32_t source_crc,
                      uint32_t index, unsigned profile, unsigned version, uint8_t *out)
{
    uint32_t offset, length, checksum;
    unsigned capacity = pv_capacity(profile);
    if (!capacity || (version != 1 && version != 2) || (version == 1 && profile)) return -1;
    if (object->type > 1 || object->size > 16u*1024u*1024u ||
        index >= pv_count(object->size, profile)) return -1;
    offset = index * capacity;
    length = object->size - offset;
    if (length > capacity) length = capacity;
    memset(out, 0, pv_packet_size(profile));
    memcpy(out, "PS2V", 4);
    out[4] = version; out[5] = object->type; out[6] = 4; out[7] = profile;
    put32(out+8, session); put32(out+12, index); put32(out+16, ~index);
    put32(out+20, pv_count(object->size, profile)); put32(out+24, length);
    put32(out+28, offset); put32(out+32, object->size); put32(out+36, object->size);
    put32(out+40, source_crc);
    if (length && object->read(object->context, offset, out+48, length)) return -1;
    checksum = pv_crc_update(0xffffffffu, out, 44);
    checksum = pv_crc_update(checksum, out+48, length) ^ 0xffffffffu;
    put32(out+44, checksum);
    return 0;
}
void pv_render(const uint8_t packet[PV_PACKET], pv_rect_fn rect, void *ctx)
{
    pv_render_profile(packet, 0, rect, ctx);
}
void pv_render_profile(const uint8_t *packet, unsigned profile, pv_rect_fn rect, void *ctx)
{
    static const uint8_t palette[4][3] = {
        {32,32,32}, {224,224,224}, {224,192,32}, {32,64,224}
    };
    static const uint8_t white[3] = {255,255,255}, black[3] = {0,0,0};
    unsigned i;
    const pv_grid *g = pv_grid_get(profile);
    if (!g) return;
    rect(ctx, 0, 0, 320, 224, black);
    for (i = 0; i < 4; ++i) {
        int x = (i & 1) ? 288 : 16, y = (i & 2) ? 196 : 12;
        rect(ctx,x,y,16,16,white);
        rect(ctx,x+4,y+4,8,8,black);
        rect(ctx,x+6,y+6,4,4,white);
        rect(ctx,64+48*i,12,32,16,palette[i]);
    }
    for (i = 0; i < g->cols*g->rows; ++i) {
        unsigned symbol = (packet[i/4] >> (6-2*(i%4))) & 3u;
        rect(ctx,16+g->cell*(i%g->cols),32+g->cell*(i/g->cols),g->cell,g->cell,palette[symbol]);
    }
}
void pv_test_data(uint8_t *out, uint32_t size)
{
    uint32_t state = 0x50533256u, i;
    for (i = 0; i < size; ++i) {
        state ^= state << 13; state ^= state >> 17; state ^= state << 5;
        out[i] = (uint8_t)state;
    }
}
