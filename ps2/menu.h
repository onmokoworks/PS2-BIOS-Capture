#ifndef PS2V_MENU_H
#define PS2V_MENU_H
#include "wire.h"
#include "control.h"
void pv_menu(const pv_settings *settings, int connected, pv_rect_fn rect, void *ctx);
void pv_overlay(const pv_settings *settings, pv_rect_fn rect, void *ctx);
#endif
