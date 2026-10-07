import random
import cv2
import pytest
from receiver.codec import render, decode_image
from receiver.protocol import encode, decode, GRIDS, payload_capacity, DecodeError
from receiver.live import Transfer
from receiver.store import Store


@pytest.mark.parametrize('profile', [0, 1, 2])
@pytest.mark.parametrize('size', [0, 1, 65536])
def test_profiles(profile, size):
    data = random.Random(71).randbytes(size)
    store = Store()
    for packet in encode(data, profile=profile, version=2):
        image = render(packet)
        # Match the actual 480i renderer's doubled pixels.
        image = cv2.resize(image, (640,448), interpolation=cv2.INTER_NEAREST)
        store.add(decode_image(image))
    assert store.result() == data


@pytest.mark.parametrize('profile', [1, 2])
def test_dense_drop_resume(tmp_path, profile):
    data = random.Random(3).randbytes(4097)
    packets = list(encode(data, profile=profile, version=2))
    transfer = Transfer(tmp_path)
    for p in packets[1:]:
        transfer.accept(decode_image(render(p)))
    resumed = Transfer(tmp_path)
    result = resumed.accept(decode_image(render(packets[0])))
    assert result.complete and result.received_bytes == len(data)
    assert result.first_missing_offset is None
    assert result.profile == profile


def test_profile_reject():
    packet = bytearray(next(encode(b'data', version=2, profile=1)))
    packet[7] = 2
    with pytest.raises(DecodeError):
        decode(packet)
