# Live validation — 2026-10-07 JST

Phase 2 fixed-data transfer succeeded on a physical SCPH-50000 with DVD
player 3.02J. A YADE v1.0.7 disc booted the SOURCE_KIND=0 payload, linked at
0x00300000. The original NTSC non-interlaced disc caused
`Video Format Not Supported` through the user's PS2-to-HDMI adapter.
The `VIDEO_INTERLACED=1 HOLD_VBLANKS=12` disc displayed the cell grid.

The native desktop tool enumerated `UGREEN 15390` through DirectShow and
received directly from device index 1 after the user closed OBS. The desktop
preview, received/missing counters, completion status and automatic output
were verified. The capture device was released after successful completion;
the desktop window remains available for the user.

- 497/497 frames accepted; no frame CRC failures recorded during reception.
- Reconstructed size: 65,536 bytes.
- Source and reconstructed CRC32: **4B07E436**.
- Exact byte comparison with the C/Python xorshift32 fixed pattern: **PASS**.
- Output: `captures/TEST-4b061895-4b07e436.bin` (private/ignored).
- Host regression tests excluding the previously verified 4 MiB slow test:
  **32 passed, 1 deselected**.

The native tool uses `receiver/live.py` for session/checkpoint/output handling
and `receiver/gui.py` for its Tk interface and capture worker. It supports
live DirectShow capture and optional recorded video/PNG input. Completed
objects are stored locally after source CRC validation. Existing completed
files are reused only if their bytes match; different contents are not
overwritten. The GUI additions depend on requirements-gui.txt.

This completes the fixed-data GS-to-capture phase for this hardware chain.
ROM0 prefix 64 KiB and full 4 MiB remain unverified on hardware. No BIOS was
read, saved, or distributed in this test. Older validation documents describe
the earlier host-only status and are retained as historical records.
