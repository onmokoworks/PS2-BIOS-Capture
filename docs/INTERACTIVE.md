# Interactive disc settings

The payload starts in a controller menu, with TEST 64K selected. It acquires
the selected object only when START is pressed. Build with
`INTERACTIVE=1 VIDEO_INTERLACED=1`. The baseline v1 sender remains available.

|Port 1 controller|Action|
|---|---|
|SELECT|AUTO / MANUAL|
|UP / DOWN|Manual display time, 0.1-second steps, 0.1–1.0 seconds|
|LEFT / RIGHT|Manual grid: 36×20, 48×26, 72×40|
|L1 / R1 while paused|TEST 64K / ROM0 64K / ROM0 4M|
|START or CROSS|Start / pause|

AUTO uses the standard grid, sending successive complete rounds at 0.1,
0.2 and 0.3 seconds. It does not measure PC reception quality: the channel
has no return path. Fast rounds acquire data, slower rounds fill losses.
Manual timing changes preserve the session. A density change starts a new
session at frame 0 because packet boundaries change. The PC automatically
recognizes that profile and keeps its checkpoint separate. Pausing retains
the snapshot; changing the source reacquires it on the next START.

|Profile|Logical cell|Grid|RAW bytes/frame|Ideal bytes/s at 0.1s|
|---:|---:|---:|---:|---:|
|0|8×8|36×20|132|1,320|
|1|6×6|48×26|264|2,640|
|2|4×4|72×40|672|6,720|

Six NTSC VBlanks correspond to about 0.1 seconds; drawing may add overhead.
Dense cells may cause more analogue decoding errors. The 480i adapter doubles
each logical pixel, retaining all symbols in either field. The small GS
status overlay occupies y=2..8 and y=216..222, outside markers and data.

## Packaging and status

Follow `packaging/yade/README.md`, adding `INTERACTIVE=1 VIDEO_INTERLACED=1`
to the relocated build. Strip the ELF, then pass it to tools.package_yade.
The prepared `ps2v-yade-3.02J-menu.iso` includes the application and loader,
no BIOS. Runtime settings require no reburning once this software version is
on the disc. Code updates still require updating the boot medium.

On 2026-10-07 JST: 50 host tests passed in 42.64 seconds. They include the
existing 4 MiB loopback, all three profile render/decode roundtrips, drop and
resume, C/Python packet and pixel agreement, controller setting bounds, AUTO
rounds, and GIF command-buffer bounds. EE ELF and embedded IOP IRX link with
-Wall -Wextra -Werror. The stripped payload is 187,508 bytes, within the
loader's fixed BOOT capacity. ISO structure and payload extraction are checked.

Physical controller/menu input, dense grids, ROM0 64 KiB and full ROM0 remain
unverified; PCSX2 was not used for this revision. The earlier fixed 480i
payload has completed a physical byte-exact 64 KiB test-data transfer.
