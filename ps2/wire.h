#ifndef PS2V_WIRE_H
#define PS2V_WIRE_H
#include <stdint.h>
#include <stddef.h>
#define PV_PACKET 180u
#define PV_PAYLOAD 132u
#define PV_MAX_PACKET 720u
typedef struct { unsigned cols, rows, cell; } pv_grid;
const pv_grid *pv_grid_get(unsigned profile);
unsigned pv_packet_size(unsigned profile);
unsigned pv_capacity(unsigned profile);
uint32_t pv_count(uint32_t size, unsigned profile);
typedef struct {
    uint8_t type;
    uint32_t size;
    void *context;
    int (*read)(void *context, uint32_t offset, void *out, uint32_t length);
} pv_object;
uint32_t pv_crc_update(uint32_t state, const void *data, size_t size);
uint32_t pv_crc(const void *data, size_t size);
int pv_object_crc(const pv_object *object, uint32_t *crc);
uint32_t pv_frame_count(uint32_t size);
int pv_packet(const pv_object *object, uint32_t session, uint32_t source_crc,
              uint32_t index, uint8_t out[PV_PACKET]);
typedef void (*pv_rect_fn)(void *context, int x, int y, int w, int h,
                           const uint8_t rgb[3]);
void pv_render(const uint8_t packet[PV_PACKET], pv_rect_fn rectangle, void *context);
int pv_packet_profile(const pv_object *object, uint32_t session, uint32_t source_crc,
                      uint32_t index, unsigned profile, unsigned version, uint8_t *out);
void pv_render_profile(const uint8_t *packet, unsigned profile, pv_rect_fn rectangle, void *context);
void pv_test_data(uint8_t *out, uint32_t size);
#endif
