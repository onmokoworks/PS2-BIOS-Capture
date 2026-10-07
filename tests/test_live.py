from pathlib import Path
import pytest
from receiver.live import Transfer, fresh_directory
from receiver.protocol import encode, decode, DecodeError
from tools.test_pattern import pattern


def test_live_complete_and_resume(tmp_path):
    data = pattern()
    packets = list(encode(data, 0x2345))
    transfer = Transfer(tmp_path)
    for packet in packets[1:]:
        result = transfer.accept(decode(packet))
    assert not result.complete
    assert not list(tmp_path.glob('*.bin'))
    resumed = Transfer(tmp_path)
    result = resumed.accept(decode(packets[0]))
    assert result.complete and result.test_matches
    assert Path(result.output).read_bytes() == data
    again = Transfer(tmp_path)
    assert again.accept(decode(packets[0])).output == result.output


def test_live_does_not_overwrite(tmp_path):
    data = b'example'
    frame = decode(next(encode(data)))
    transfer = Transfer(tmp_path)
    result = transfer.accept(frame)
    Path(result.output).write_bytes(b'personal existing file')
    with pytest.raises(DecodeError, match='different contents'):
        Transfer(tmp_path).accept(frame)
    assert Path(result.output).read_bytes() == b'personal existing file'


def test_byte_progress_out_of_order_duplicate_and_resume(tmp_path):
    data = bytes(range(200)) + b'last'
    first, last = map(decode, encode(data, 12))
    transfer = Transfer(tmp_path)
    result = transfer.accept(last)
    assert result.received_bytes == len(last.payload) == 72
    assert result.last_offset == 132 and result.last_length == 72
    assert result.last_hex == last.payload[:32].hex(' ').upper()
    assert result.last_was_new and result.first_missing_offset == 0
    repeated = transfer.accept(last)
    assert repeated.received_bytes == 72 and not repeated.last_was_new
    resumed = Transfer(tmp_path)
    final = resumed.accept(first)
    assert final.received_bytes == len(data)
    assert final.first_missing_offset is None and final.complete
    assert final.last_offset == 0
    assert final.restored_bytes == 72 and final.new_bytes == 132
    assert final.restored_frames == 1 and final.new_frames == 1


def test_completed_resume_is_not_new_reception(tmp_path):
    frame = decode(next(encode(b'previous reception')))
    original = Transfer(tmp_path).accept(frame)
    resumed = Transfer(tmp_path).accept(frame)
    assert resumed.complete and resumed.output == original.output
    assert resumed.restored_bytes == len(frame.payload)
    assert resumed.new_bytes == resumed.new_frames == 0
    assert resumed.restored_frames == 1


def test_fresh_reception_keeps_previous_data(tmp_path):
    data = bytes(range(200))
    frames = list(map(decode, encode(data)))
    previous = Transfer(tmp_path)
    for frame in frames:
        old = previous.accept(frame)
    first_directory = fresh_directory(tmp_path)
    other_directory = fresh_directory(tmp_path)
    assert first_directory != other_directory
    fresh = Transfer(first_directory)
    partial = fresh.accept(frames[0])
    assert not partial.complete and partial.restored_bytes == 0
    assert partial.new_bytes == len(frames[0].payload)
    completed = fresh.accept(frames[1])
    assert completed.complete and completed.new_bytes == len(data)
    assert Path(old.output).read_bytes() == Path(completed.output).read_bytes() == data
