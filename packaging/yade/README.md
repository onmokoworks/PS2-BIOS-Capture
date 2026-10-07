# YADE disc packaging — SCPH-50000 / DVD player 3.02J

YADE v1.0.7 lists DVD player 3.02J as supported. Japanese versions display
`3.02` without a trailing J. This provides a disc boot candidate independent
of the original CTurt FreeDVDBoot compatibility list.

Upstream: https://github.com/MFDGaming/YADE/releases/tag/v1.0.7

Use the official `exploit_3.02J.iso` (SHA256 pinned in `tools/package_yade.py`).
The loader reads BOOT.ELF from sector 516 using a compiled fixed read length.
Keep the complete original ISO layout and BOOT file length unchanged. Replace
the file content with a smaller stripped ELF and zero padding. All bytes
outside BOOT.ELF remain unchanged, including the DVD exploit and sector tables.

Build the TEST payload with the SDK's linker script and add
`-Wl,-Ttext=0x00300000` to the link flags, then strip it. This locates LOAD at
3 MiB, above YADE's 1 MiB staging buffer and the DVD helper code, below YADE's
loader at 0x01ffe800. Do not use the ordinary ELF linked at 1 MiB.

With the normal PS2DEV environment:

```sh
make -C ps2 SOURCE_KIND=0 EE_BIN=ps2v-test-yade.elf \
  EE_LDFLAGS="-L${PS2SDK}/ee/lib -Wl,-zmax-page-size=128 -Wl,-Ttext=0x00300000"
mips64r5900el-ps2-elf-strip --strip-all \
  -o ps2v-test-yade-stripped.elf ps2/ps2v-test-yade.elf
python -m pip install pycdlib
python -m tools.package_yade exploit_3.02J.iso \
  ps2v-test-yade-stripped.elf ps2v-yade-3.02J-test.iso
```

This ISO boots the fixed 64 KiB test pattern directly, with no USB storage or
network. It is an experimental disc candidate: build, ELF bounds, ISO extent,
extracted payload, and preservation of every byte outside BOOT are checked on
the host. Physical PS2 boot and analogue capture still require testing.

Burn the ISO as an image to a blank DVD and close the session. The test payload
should display four finders, four calibration patches and a cycling cell grid.
Compare the receiver's output with `python -m tools.test_pattern expected.bin`;
the expected test source CRC32 is 4B07E436. Only after this succeeds should ROM0
testing proceed.

## HDMI converter compatibility

If the standard PS2 menu is visible but starting the TEST disc produces
`Video Format Not Supported`, a converter/capture device may reject 240p.
The baseline payload remains NTSC non-interlaced. Build a separate compatibility
payload with `VIDEO_INTERLACED=1 HOLD_VBLANKS=12` in the make command above.
It uses NTSC interlaced FIELD mode with a 640x448 active framebuffer (480i
timing), doubles each logical pixel in both axes, and keeps the same PS2V
protocol. Each scanline pair contains the same symbols, so either individual
field retains the complete logical grid. The receiver handles the geometry
from its four finders. Captured transitions between packets still require CRC
rejection and retransmission.

Host tests verify full-frame and separate even/odd-field reconstruction.
This does not establish HDMI converter compatibility on hardware. A direct
PS2-to-HDMI adapter may still pass 480i through unchanged; the capture device
must accept it or a scaler must convert it to a supported HDMI format.

YADE is Apache-2.0; retain its license when distributing a derived disc image.
The payload uses this project's MIT code and PS2SDK dependencies; see
`ps2/LICENSES`. No BIOS or Sony DVD player executable is included.
