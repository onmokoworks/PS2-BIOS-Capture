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
#include "control.h"
#include "menu.h"
#ifndef INTERACTIVE
#define INTERACTIVE 0
#endif
#if INTERACTIVE
#include <sifrpc.h>
#include <loadfile.h>
#include <libpad.h>
static unsigned char pad_buffer[256] __attribute__((aligned(64)));
static unsigned previous_buttons;
static int pad_setup(void)
{
    SifInitRpc(0);
    if (SifLoadModule("rom0:SIO2MAN",0,0) < 0 || SifLoadModule("rom0:PADMAN",0,0) < 0) return -1;
    padInit(0);
    return padPortOpen(0,0,pad_buffer) ? 0 : -1;
}
static int pad_connected(void)
{
    int state = padGetState(0,0);
    return state == PAD_STATE_STABLE || state == PAD_STATE_FINDCTP1;
}
static void pad_settings(pv_settings *settings)
{
    struct padButtonStatus buttons;
    unsigned held;
    if (!pad_connected() || !padRead(0,0,&buttons)) { previous_buttons = 0; return; }
    held = 0xffffu ^ buttons.btns;
    pv_settings_buttons(settings, held & ~previous_buttons);
    previous_buttons = held;
}
#endif
#ifndef SOURCE_KIND
#define SOURCE_KIND 0
#endif
#ifndef HOLD_VBLANKS
#define HOLD_VBLANKS 6
#endif
#ifndef VIDEO_INTERLACED
#define VIDEO_INTERLACED 0
#endif
#if VIDEO_INTERLACED != 0 && VIDEO_INTERLACED != 1
#error VIDEO_INTERLACED must be 0 or 1
#endif
#define SCREEN_SCALE (VIDEO_INTERLACED ? 2 : 1)
#define SCREEN_WIDTH (320 * SCREEN_SCALE)
#define SCREEN_HEIGHT (224 * SCREEN_SCALE)
#if HOLD_VBLANKS < 2
#error HOLD_VBLANKS must be at least 2
#endif
static qword_t *cursor;
static void gs_rectangle(void *unused, int x, int y, int w, int h, const uint8_t rgb[3])
{
    rect_t r = {0};
    (void)unused;
    /* Duplicate logical pixels in both fields in the 480i compatibility mode. */
    x *= SCREEN_SCALE; y *= SCREEN_SCALE;
    w *= SCREEN_SCALE; h *= SCREEN_SCALE;
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
static void present(packet_t *commands, framebuffer_t *frame)
{
    cursor = draw_finish(cursor);
    FlushCache(0);
    dma_channel_send_normal(DMA_CHANNEL_GIF, commands->data, cursor-commands->data, 0, 0);
    dma_channel_wait(DMA_CHANNEL_GIF, 0);
    draw_wait_finish();
    graph_wait_vsync();
    graph_set_framebuffer(0, frame->address, SCREEN_WIDTH, GS_PSM_32, 0, 0);
    graph_set_output(1,0,GRAPH_VALUE_ALPHA,GRAPH_RC1_ALPHA,GRAPH_BLEND_BGCOLOR,0x80);
}
int main(void)
{
    framebuffer_t frames[2] = {0};
    zbuffer_t z = {0};
    packet_t *commands;
    pv_object source = {0};
    uint8_t bytes[PV_MAX_PACKET];
    uint32_t source_crc = 0, session = 0, index = 0;
    int i, back = 0;
#if INTERACTIVE
    pv_settings settings;
    int pad_ok, loaded_source = -1;
    unsigned active_profile = 0;
#endif
    dma_channel_initialize(DMA_CHANNEL_GIF, 0, 0);
    graph_set_mode(VIDEO_INTERLACED ? GRAPH_MODE_INTERLACED : GRAPH_MODE_NONINTERLACED,
                   GRAPH_MODE_NTSC,
                   VIDEO_INTERLACED ? GRAPH_MODE_FIELD : GRAPH_MODE_FRAME, 0);
    graph_set_screen(0, 0, SCREEN_WIDTH, SCREEN_HEIGHT);
    graph_disable_output(); graph_set_bgcolor(0,0,0);
    for (i=0; i<2; ++i) {
        int address = graph_vram_allocate(SCREEN_WIDTH,SCREEN_HEIGHT,GS_PSM_32,GRAPH_ALIGN_PAGE);
        if (address < 0) fail();
        frames[i].width = SCREEN_WIDTH; frames[i].height = SCREEN_HEIGHT; frames[i].psm = GS_PSM_32;
        frames[i].address = address;
    }
    z.enable = DRAW_DISABLE; z.mask = 1; z.zsm = GS_ZBUF_32;
    commands = packet_init(12288, PACKET_NORMAL);
    if (!commands) fail();
#if INTERACTIVE
    pv_settings_init(&settings,SOURCE_KIND);
    pad_ok = pad_setup() == 0;
#else
    if (pv_source_open(&source, SOURCE_KIND) || pv_object_crc(&source, &source_crc)) fail();
    session = source_crc ^ (uint32_t)clock() ^ source.size ^ source.type;
#endif
    draw_disable_blending();
    for (;;) {
#if INTERACTIVE
        if (!settings.transmitting) {
            cursor = draw_setup_environment(commands->data, 0, &frames[back], &z);
            cursor = draw_primitive_xyoffset(cursor, 0, 2048, 2048);
            pv_menu(&settings,pad_ok && pad_connected(),gs_rectangle,0);
            present(commands,&frames[back]);
            back ^= 1;
            if (pad_ok) pad_settings(&settings);
            continue;
        }
        if (loaded_source != (int)settings.source_kind) {
            if (source.context) pv_source_close(&source);
            if (pv_source_open(&source,settings.source_kind) || pv_object_crc(&source,&source_crc)) fail();
            loaded_source = settings.source_kind;
            session = source_crc ^ (uint32_t)clock() ^ source.size ^ source.type;
            index = 0;
            active_profile = settings.profile;
        }
        if (active_profile != settings.profile) {
            active_profile = settings.profile;
            session += 0x9e3779b9u;
            index = 0;
        }
        if (pv_packet_profile(&source,session,source_crc,index,active_profile,2,bytes)) fail();
#else
        if (pv_packet(&source, session, source_crc, index, bytes)) fail();
#endif
        cursor = draw_setup_environment(commands->data, 0, &frames[back], &z);
        cursor = draw_primitive_xyoffset(cursor, 0, 2048, 2048);
#if INTERACTIVE
        pv_render_profile(bytes,active_profile,gs_rectangle,0);
        pv_overlay(&settings,gs_rectangle,0);
#else
        pv_render(bytes, gs_rectangle, 0);
#endif
        present(commands,&frames[back]);
#if INTERACTIVE
        for (i=1; i<(int)pv_settings_vblanks(&settings) && settings.transmitting; ++i) {
            graph_wait_vsync();
            if (pad_ok) pad_settings(&settings);
        }
        back ^= 1;
        if (settings.transmitting && active_profile == settings.profile &&
            ++index == pv_count(source.size,active_profile)) {
            index = 0;
            pv_settings_round(&settings);
        }
#else
        for (i=1; i<HOLD_VBLANKS; ++i) graph_wait_vsync();
        back ^= 1;
        if (++index == pv_frame_count(source.size)) index = 0;
#endif
    }
}
