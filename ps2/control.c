/* SPDX-License-Identifier: MIT */
#include "control.h"
void pv_settings_init(pv_settings *s, unsigned source_kind)
{
    s->automatic = 1; s->tenths = 2; s->profile = 0;
    s->source_kind = source_kind; s->transmitting = 0; s->round = 0;
}
void pv_settings_buttons(pv_settings *s, unsigned pressed)
{
    if (pressed & PV_SELECT) {
        s->automatic ^= 1; s->round = 0;
        if (s->automatic) s->profile = 0;
    }
    if (!s->automatic) {
        if ((pressed & PV_UP) && s->tenths < 10) ++s->tenths;
        if ((pressed & PV_DOWN) && s->tenths > 1) --s->tenths;
        if ((pressed & PV_RIGHT) && s->profile < 2) ++s->profile;
        if ((pressed & PV_LEFT) && s->profile > 0) --s->profile;
    }
    if (!s->transmitting) {
        if ((pressed & PV_R1) && s->source_kind < 2) ++s->source_kind;
        if ((pressed & PV_L1) && s->source_kind > 0) --s->source_kind;
    }
    if (pressed & (PV_START | PV_CROSS)) s->transmitting ^= 1;
}
unsigned pv_settings_tenths(const pv_settings *s)
{
    static const unsigned schedule[] = {1,2,3};
    return s->automatic ? schedule[s->round%3] : s->tenths;
}
unsigned pv_settings_vblanks(const pv_settings *s)
{
    return 6*pv_settings_tenths(s);
}
void pv_settings_round(pv_settings *s)
{
    if (s->automatic) s->round = (s->round+1)%3;
}
