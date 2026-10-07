/* SPDX-License-Identifier: MIT — small uppercase 5x7 bitmap font. */
#include "menu.h"
#include <stdio.h>
#include <string.h>
static const char chars[] = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789.:/-";
static const uint8_t glyphs[][5] = {
 {126,17,17,17,126},{127,73,73,73,54},{62,65,65,65,34},{127,65,65,34,28},
 {127,73,73,73,65},{127,9,9,9,1},{62,65,73,73,122},{127,8,8,8,127},
 {0,65,127,65,0},{32,64,65,63,1},{127,8,20,34,65},{127,64,64,64,64},
 {127,2,12,2,127},{127,4,8,16,127},{62,65,65,65,62},{127,9,9,9,6},
 {62,65,81,33,94},{127,9,25,41,70},{38,73,73,73,50},{1,1,127,1,1},
 {63,64,64,64,63},{31,32,64,32,31},{63,64,56,64,63},{99,20,8,20,99},
 {7,8,112,8,7},{97,81,73,69,67},
 {62,81,73,69,62},{0,66,127,64,0},{66,97,81,73,70},{33,65,69,75,49},
 {24,20,18,127,16},{39,69,69,69,57},{60,74,73,73,48},{1,113,9,5,3},
 {54,73,73,73,54},{6,73,73,41,30},
 {0,96,96,0,0},{0,54,54,0,0},{32,16,8,4,2},{8,8,8,8,8}
};
static void text(pv_rect_fn rect, void *ctx, int x, int y, unsigned scale, const char *s)
{
    static const uint8_t white[] = {224,224,224};
    for (; *s; ++s, x += 6*scale) {
        const char *found = strchr(chars,*s);
        unsigned col,row;
        if (!found) continue;
        for (col=0; col<5; ++col) for (row=0; row<7; ++row)
            if (glyphs[found-chars][col] & (1u<<row))
                rect(ctx,x+col*scale,y+row*scale,scale,scale,white);
    }
}
void pv_menu(const pv_settings *s, int connected, pv_rect_fn rect, void *ctx)
{
    static const uint8_t black[] = {0,0,0};
    static const char *sources[] = {"TEST 64K","ROM0 64K","ROM0 4M"};
    const pv_grid *g = pv_grid_get(s->profile);
    char line[64];
    unsigned tenths = pv_settings_tenths(s);
    rect(ctx,0,0,320,224,black);
    text(rect,ctx,16,12,2,"PS2 VIDEO BACKUP");
    text(rect,ctx,16,48,2,s->automatic ? "MODE: AUTO" : "MODE: MANUAL");
    sprintf(line,"GRID: %uX%u",g->cols,g->rows); text(rect,ctx,16,72,2,line);
    sprintf(line,"TIME: %u.%uS",tenths/10,tenths%10); text(rect,ctx,16,96,2,line);
    sprintf(line,"SRC: %s",sources[s->source_kind]); text(rect,ctx,16,120,2,line);
    text(rect,ctx,16,158,1,"SELECT AUTO/MAN  UP/DOWN TIME");
    text(rect,ctx,16,170,1,"LEFT/RIGHT GRID  L1/R1 SOURCE");
    text(rect,ctx,16,194,2,connected ? "START SEND" : "CONNECT PAD1");
    text(rect,ctx,16,215,1,"ROM0 READ ONLY ON START");
}
void pv_overlay(const pv_settings *s, pv_rect_fn rect, void *ctx)
{
    char line[64];
    unsigned tenths = pv_settings_tenths(s);
    sprintf(line,"%s %u.%uS GRID%u",s->automatic ? "AUTO" : "MAN",tenths/10,tenths%10,s->profile);
    text(rect,ctx,16,2,1,line);
    text(rect,ctx,16,216,1,"START PAUSE  SELECT MODE");
}
