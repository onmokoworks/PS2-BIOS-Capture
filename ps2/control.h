#ifndef PS2V_CONTROL_H
#define PS2V_CONTROL_H
#define PV_UP 0x0010u
#define PV_RIGHT 0x0020u
#define PV_DOWN 0x0040u
#define PV_LEFT 0x0080u
#define PV_START 0x0008u
#define PV_SELECT 0x0001u
#define PV_L1 0x0400u
#define PV_R1 0x0800u
#define PV_CROSS 0x4000u
typedef struct {
    unsigned automatic, tenths, profile, source_kind, transmitting, round;
} pv_settings;
void pv_settings_init(pv_settings *settings, unsigned source_kind);
void pv_settings_buttons(pv_settings *settings, unsigned pressed);
unsigned pv_settings_tenths(const pv_settings *settings);
unsigned pv_settings_vblanks(const pv_settings *settings);
void pv_settings_round(pv_settings *settings);
#endif
