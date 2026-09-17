/* SPDX-License-Identifier: MIT */
#include <kernel.h>
#include <dma.h>
#include <graph.h>
#include <draw.h>
#include <draw2d.h>
#include <packet.h>
#include <gs_psm.h>
#include <time.h>
#include "source.h"
#ifndef SOURCE_KIND
#define SOURCE_KIND 0
#endif
#ifndef HOLD_VBLANKS
#define HOLD_VBLANKS 6
#endif
#if HOLD_VBLANKS < 2
#error HOLD_VBLANKS must be at least 2
#endif
static qword_t *cursor;
static void gs_rectangle(void *unused, int x, int y, int w, int h, const uint8_t rgb[3])
{
    rect_t r = {0};
    (void)unused;
    /* Cancel draw2d's START_OFFSET/END_OFFSET bias; exclusive pixel bounds. */
    r.v0.x = x + 0.4375f; r.v0.y = y + 0.4375f;
    r.v1.x = x+w - 0.5625f; r.v1.y = y+h - 0.5625f;
    r.color.r = rgb[0]; r.color.g = rgb[1]; r.color.b = rgb[2];
    r.color.a = 0x80; r.color.q = 1.0f;
    cursor = draw_rect_filled(cursor, 0, &r);
}
static void fail(void)
{
    graph_disable_output();
    graph_set_bgcolor(160,0,160);
    graph_set_output(0,0,0,0,1,0x80);
    for (;;) graph_wait_vsync();
}
int main(void)
{
    framebuffer_t frames[2] = {0};
    zbuffer_t z = {0};
    packet_t *commands;
    pv_object source = {0};
    uint8_t bytes[PV_PACKET];
    uint32_t source_crc, session, index = 0;
    int i, back = 0, first = 1;
    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    graph_set_mode(GRAPH_MODE_NONINTERLACED, GRAPH_MODE_NTSC, GRAPH_MODE_FRAME, 0);
    graph_set_screen(0, 0, 320, 224);
    graph_disable_output(); graph_set_bgcolor(0,0,0);
    for (i=0; i<2; ++i) {
        int address = graph_vram_allocate(320,224,GS_PSM_32,GRAPH_ALIGN_PAGE);
        if (address < 0) fail();
        frames[i].width = 320; frames[i].height = 224; frames[i].psm = GS_PSM_32;
        frames[i].address = address;
    }
    z.enable = DRAW_DISABLE; z.mask = 1; z.zsm = GS_ZBUF_32;
    commands = packet_init(4096, PACKET_NORMAL);
    if (!commands || pv_source_open(&source, SOURCE_KIND) || pv_object_crc(&source, &source_crc)) fail();
    session = source_crc ^ (uint32_t)clock() ^ source.size ^ source.type;
    draw_disable_blending();
    for (;;) {
        if (pv_packet(&source, session, source_crc, index, bytes)) fail();
        cursor = draw_setup_environment(commands->data, 0, &frames[back], &z);
        cursor = draw_primitive_xyoffset(cursor, 0, 2048, 2048);
        pv_render(bytes, gs_rectangle, 0);
        cursor = draw_finish(cursor);
        FlushCache(0);
        dma_channel_send_normal(DMA_CHANNEL_GIF, commands->data, cursor-commands->data, 0, 0);
        dma_channel_wait(DMA_CHANNEL_GIF, 0);
        draw_wait_finish();
        graph_wait_vsync();
        graph_set_framebuffer(0, frames[back].address, 320, GS_PSM_32, 0, 0);
        if (first) {
            /* Enable only read circuit 1, no flicker filter/read circuit 2. */
            graph_set_output(1,0,GRAPH_VALUE_ALPHA,GRAPH_RC1_ALPHA,GRAPH_BLEND_BGCOLOR,0x80);
            first = 0;
        }
        for (i=1; i<HOLD_VBLANKS; ++i) graph_wait_vsync();
        back ^= 1;
        if (++index == pv_frame_count(source.size)) index = 0;
    }
}
