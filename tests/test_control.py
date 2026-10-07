import os
from pathlib import Path
import shutil
import subprocess
import pytest


def test_controls_and_gif_packet_bounds(tmp_path):
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
    if not cc:
        pytest.skip('host C compiler required')
    root = Path(__file__).resolve().parents[1]
    out = tmp_path/('control.exe' if os.name=='nt' else 'control')
    subprocess.run([cc,'-std=c99','-O2','-Wall','-Wextra','-Werror',
                    '-I'+str(root/'ps2'),str(root/'ps2/control.c'),str(root/'ps2/menu.c'),
                    str(root/'ps2/wire.c'),str(root/'tests/control_reference.c'),'-o',str(out)],check=True)
    subprocess.run([str(out)],check=True)
