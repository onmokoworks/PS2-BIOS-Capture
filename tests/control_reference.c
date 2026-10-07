#include <assert.h>
#include "control.h"
#include "menu.h"
static unsigned rects;
static void rectangle(void *context,int x,int y,int w,int h,const uint8_t rgb[3])
{
    (void)context; (void)rgb;
    assert(x>=0 && y>=0 && x+w<=320 && y+h<=224);
    ++rects;
}
int main(void)
{
    pv_settings s;
    unsigned i;
    pv_settings_init(&s,0);
    assert(!s.transmitting && s.automatic && pv_settings_vblanks(&s)==6);
    pv_settings_buttons(&s,PV_UP|PV_RIGHT);
    assert(s.profile==0 && s.tenths==2);
    pv_settings_buttons(&s,PV_SELECT);
    assert(!s.automatic && pv_settings_vblanks(&s)==12);
    for(i=0;i<100;++i) pv_settings_buttons(&s,PV_DOWN);
    assert(s.tenths==1 && pv_settings_vblanks(&s)==6);
    for(i=0;i<100;++i) pv_settings_buttons(&s,PV_UP|PV_RIGHT);
    assert(s.tenths==10 && s.profile==2 && pv_settings_vblanks(&s)==60);
    pv_settings_buttons(&s,PV_START);
    pv_settings_buttons(&s,PV_R1);
    assert(s.transmitting && s.source_kind==0);
    pv_settings_buttons(&s,PV_START);
    pv_settings_buttons(&s,PV_R1);
    pv_settings_buttons(&s,PV_R1);
    assert(!s.transmitting && s.source_kind==2);
    pv_settings_buttons(&s,PV_SELECT);
    assert(s.automatic && s.profile==0 && pv_settings_vblanks(&s)==6);
    pv_settings_round(&s); assert(pv_settings_vblanks(&s)==12);
    pv_settings_round(&s); assert(pv_settings_vblanks(&s)==18);
    pv_settings_round(&s); assert(pv_settings_vblanks(&s)==6);
    for(i=0;i<3;++i) {
        s.profile=i;
        rects=0; pv_menu(&s,1,rectangle,0);
        assert(rects*3+32<12288);
        rects=0; pv_overlay(&s,rectangle,0);
        assert((rects+pv_grid_get(i)->cols*pv_grid_get(i)->rows+17)*3+32<12288);
    }
    return 0;
}
