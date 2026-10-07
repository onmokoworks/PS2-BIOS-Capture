import os
from pathlib import Path
import random
import shutil
import subprocess
import cv2
import numpy as np
import pytest
from receiver.protocol import encode
from receiver.codec import render, decode_image
from tools.test_pattern import pattern


@pytest.fixture(scope='module')
def executable(tmp_path_factory):
    cc = os.environ.get('CC') or shutil.which('cc') or shutil.which('gcc')
    if not cc:
        pytest.skip('set CC to a host C compiler to verify C/Python equivalence')
    root = Path(__file__).resolve().parents[1]
    out = tmp_path_factory.mktemp('c') / ('reference.exe' if os.name == 'nt' else 'reference')
    subprocess.run([cc, '-std=c99', '-O2', '-Wall', '-Wextra', '-Werror',
                    '-I'+str(root/'ps2'), str(root/'ps2/wire.c'),
                    str(root/'tests/c_reference.c'), '-o', str(out)], check=True)
    return out


@pytest.mark.parametrize('size,index', [(0,0),(1,0),(132,0),(133,1),(65536,0),(65536,496)])
def test_c_python_identical(executable, tmp_path, size, index):
    data = random.Random(78).randbytes(size)
    source, packet, ppm = [tmp_path/n for n in ('input.bin','packet.pkt','frame.ppm')]
    source.write_bytes(data)
    subprocess.run([str(executable),str(source),str(index),str(packet),str(ppm)],check=True)
    expected = list(encode(data,0x12345678))[index]
    assert packet.read_bytes() == expected
    actual = cv2.cvtColor(cv2.imread(str(ppm)),cv2.COLOR_BGR2RGB)
    assert np.array_equal(actual,render(expected))
    assert decode_image(actual).pack() == expected


def test_fixed_pattern(executable, tmp_path):
    output = tmp_path / 'fixed.bin'
    subprocess.run([str(executable), '--pattern', str(output)], check=True)
    assert output.read_bytes() == pattern()


@pytest.mark.parametrize('profile', [0, 1, 2])
def test_c_profiles(executable, tmp_path, profile):
    data = random.Random(78).randbytes(4097)
    source, packet, ppm = [tmp_path/n for n in ('input.bin','packet.pkt','frame.ppm')]
    source.write_bytes(data)
    subprocess.run([str(executable),str(source),'1',str(packet),str(ppm),str(profile)],check=True)
    expected = list(encode(data,0x12345678,profile=profile,version=2))[1]
    assert packet.read_bytes() == expected
    actual = cv2.cvtColor(cv2.imread(str(ppm)),cv2.COLOR_BGR2RGB)
    assert np.array_equal(actual,render(expected))
    assert decode_image(actual).pack() == expected
