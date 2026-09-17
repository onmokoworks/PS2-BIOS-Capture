from dataclasses import replace
import random
import cv2
import numpy as np
import pytest
from receiver.protocol import encode, decode, crc32, DecodeError
from receiver.codec import render, decode_image
from receiver.store import Store
from receiver.capture import png_frames, video_frames


@pytest.mark.parametrize('size', [0, 1, 131, 132, 133, 4096, 65536])
def test_roundtrip(size):
    data = random.Random(724).randbytes(size)
    store = Store()
    for packet in encode(data):
        store.add(decode_image(render(packet)))
    assert store.result() == data


def distort(image, mode):
    if mode in ('blur', 'combined'):
        image = cv2.GaussianBlur(image, (5, 5), .7)
    if mode in ('brightness', 'combined'):
        image = np.clip(image.astype(float) * .72 + 18, 0, 255).astype(np.uint8)
    if mode in ('color', 'combined'):
        image = np.clip(image.astype(float)*[1.08, .86, .96] + [5, 9, -4], 0, 255).astype(np.uint8)
    if mode in ('crop', 'combined'):
        image = image[5:-4, 7:-6]
    if mode in ('scale', 'combined'):
        image = cv2.resize(image, (653, 471), interpolation=cv2.INTER_LINEAR)
    return image


@pytest.mark.parametrize('mode', ['blur', 'brightness', 'color', 'crop', 'scale', 'combined'])
def test_degraded(mode):
    data = random.Random(90).randbytes(4096)
    store = Store()
    for packet in encode(data):
        store.add(decode_image(distort(render(packet), mode)))
    assert store.result() == data


def test_png_drop_restart(tmp_path):
    data = random.Random(42).randbytes(4097)
    packets = list(encode(data, 323))
    images = tmp_path / 'frames'
    images.mkdir()
    for i, packet in enumerate(packets):
        assert cv2.imwrite(str(images / f'{i:08d}.png'), cv2.cvtColor(render(packet), cv2.COLOR_RGB2BGR))
    store = Store(tmp_path / 'state')
    for i, image in enumerate(png_frames(images)):
        if i % 3:
            store.add(decode_image(image))
    assert not store.complete
    with pytest.raises(DecodeError):
        store.write(tmp_path / 'premature.bin')
    assert not (tmp_path / 'premature.bin').exists()
    store = Store(tmp_path / 'state')
    for i in reversed(range(len(packets))):
        frame = decode_image(render(packets[i]))
        assert store.add(frame) == (i % 3 == 0)
    store.write(tmp_path / 'output.bin')
    assert (tmp_path / 'output.bin').read_bytes() == data
    with pytest.raises(FileExistsError):
        store.write(tmp_path / 'output.bin')


def test_crc_and_validation():
    assert crc32(b'123456789') == 0xcbf43926
    packet = next(encode(b'hello'))
    for i in range(len(packet)):
        damaged = bytearray(packet)
        damaged[i] ^= 1
        with pytest.raises(DecodeError):
            decode(damaged)
    frame = decode(packet)
    for fields in [dict(count=2), dict(offset=1), dict(encoded_size=6), dict(size=0x10000001),
                   dict(index=1), dict(object_type=2)]:
        with pytest.raises(DecodeError):
            decode(replace(frame, **fields).pack())


def test_wrong_source_crc_and_mixed_session(tmp_path):
    frame = decode(next(encode(b'hello')))
    store = Store()
    store.add(replace(frame, source_crc=123))
    with pytest.raises(DecodeError, match='source CRC'):
        store.write(tmp_path / 'bad.bin')
    assert not (tmp_path / 'bad.bin').exists()
    good = Store()
    good.add(frame)
    with pytest.raises(DecodeError, match='different session'):
        good.add(replace(frame, session=123))
    with pytest.raises(DecodeError, match='conflicting'):
        good.add(replace(frame, payload=b'world'))


def test_no_signal_and_transition():
    with pytest.raises(DecodeError):
        decode_image(np.zeros((480, 640, 3), np.uint8))
    packets = list(encode(random.Random(12).randbytes(400)))
    first, second = map(render, packets[:2])
    first[110:] = second[110:]
    with pytest.raises(DecodeError):
        decode_image(first)


def test_video_adapter(tmp_path):
    data = random.Random(50).randbytes(1024)
    filename = str(tmp_path / 'capture.avi')
    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), 30, (640, 448))
    assert writer.isOpened(), 'OpenCV MJPEG writer unavailable'
    for packet in encode(data):
        image = cv2.resize(render(packet), (640, 448))
        for _ in range(3):
            writer.write(cv2.cvtColor(image, cv2.COLOR_RGB2BGR))
    writer.release()
    store = Store()
    for image in video_frames(filename):
        try:
            store.add(decode_image(image))
        except DecodeError:
            pass
    assert store.result() == data


@pytest.mark.slow
def test_full_4mib():
    data = random.Random(0x50533256).randbytes(4*1024*1024)
    store = Store()
    for packet in encode(data, 0x12345678):
        store.add(decode_image(render(packet)))
    assert store.result() == data
