import os
from pathlib import Path
import random
import subprocess
import sys


def test_cli_png_roundtrip(tmp_path):
    root = Path(__file__).resolve().parents[1]
    source, output = tmp_path/'input.bin', tmp_path/'result.bin'
    source.write_bytes(random.Random(991).randbytes(1025))
    subprocess.run([sys.executable, '-m', 'tools.reference_encoder', str(source),
                    str(tmp_path/'images'), '--session', '0x9876'], cwd=root, check=True)
    command = [sys.executable, '-m', 'receiver', '--images', str(tmp_path/'images'),
               '--state', str(tmp_path/'state'), '--output', str(output)]
    subprocess.run(command, cwd=root, check=True)
    assert source.read_bytes() == output.read_bytes()
    assert subprocess.run(command, cwd=root).returncode == 1  # output is never overwritten


def test_live_adapter_contract(monkeypatch):
    import numpy as np
    from receiver import capture
    instances = []
    class FakeCamera:
        def __init__(self, source, backend):
            assert source == 2
            self.released = False
            self.reads = 0
            instances.append(self)
        def isOpened(self):
            return True
        def read(self):
            self.reads += 1
            return True, np.full((2,2,3), [10,20,30], dtype=np.uint8)
        def release(self):
            self.released = True
    monkeypatch.setattr(capture.cv2, 'VideoCapture', FakeCamera)
    stream = capture.video_frames(2)
    assert next(stream)[0,0].tolist() == [30,20,10]
    stream.close()
    assert instances[0].released
