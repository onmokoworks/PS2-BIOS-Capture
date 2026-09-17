/* Host harness for the exact portable C compiled into the PS2 ELF. */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "wire.h"
static unsigned char pixels[224][320][3];
static int read_mem(void *ctx, uint32_t off, void *out, uint32_t n)
{
    memcpy(out, (unsigned char *)ctx+off, n); return 0;
}
static void rectangle(void *ctx, int x, int y, int w, int h, const uint8_t rgb[3])
{
    int xx, yy; (void)ctx;
    for (yy=y; yy<y+h; ++yy) for (xx=x; xx<x+w; ++xx)
        memcpy(pixels[yy][xx],rgb,3);
}
int main(int argc, char **argv)
{
    uint32_t crc, index;
    uint8_t packet[PV_PACKET];
    unsigned char *data;
    pv_object object;
    FILE *in, *out;
    long size;
    if (argc == 3 && strcmp(argv[1], "--pattern") == 0) {
        data = malloc(65536); if (!data) return 5;
        pv_test_data(data, 65536);
        out = fopen(argv[2], "wb"); if (!out) return 8;
        if (fwrite(data, 1, 65536, out) != 65536) return 9;
        fclose(out); free(data); return 0;
    }
    if (argc != 5) return 2;
    in = fopen(argv[1], "rb"); if (!in) return 3;
    fseek(in,0,SEEK_END); size=ftell(in); rewind(in);
    if (size < 0 || size > 16*1024*1024) return 4;
    data = malloc((size_t)size+1); if (!data) return 5;
    if (fread(data,1,(size_t)size,in)!=(size_t)size) return 6;
    fclose(in);
    object.type=0; object.size=(uint32_t)size; object.context=data; object.read=read_mem;
    index=(uint32_t)strtoul(argv[2],0,10);
    if (pv_object_crc(&object,&crc) || pv_packet(&object,0x12345678u,crc,index,packet)) return 7;
    out=fopen(argv[3],"wb"); if (!out) return 8;
    if (fwrite(packet,1,sizeof(packet),out)!=sizeof(packet)) return 9;
    fclose(out);
    pv_render(packet,rectangle,0);
    out=fopen(argv[4],"wb"); if (!out) return 10;
    fprintf(out,"P6\n320 224\n255\n");
    if (fwrite(pixels,1,sizeof(pixels),out)!=sizeof(pixels)) return 11;
    fclose(out); free(data);
    return 0;
}
