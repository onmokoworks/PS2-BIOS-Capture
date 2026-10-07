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


def test_speed_excludes_restored_and_duplicate_bytes_and_freezes(tmp_path):
    frames = list(map(decode, encode(bytes(range(200)))))
    Transfer(tmp_path).accept(frames[1])
    now = [100.0]
    transfer = Transfer(tmp_path, clock=lambda: now[0])
    now[0] = 102.0
    restored = transfer.accept(frames[1])
    assert restored.restored_bytes == 68 and restored.new_bytes_per_second == 0
    now[0] = 104.0
    duplicate = transfer.accept(frames[1])
    assert duplicate.new_bytes == 0 and duplicate.elapsed_seconds == 4
    now[0] = 106.0
    complete = transfer.accept(frames[0])
    assert complete.complete and complete.new_bytes == 132
    assert complete.new_bytes_per_second == 22 and complete.elapsed_seconds == 6
    now[0] = 200.0
    assert transfer.progress().new_bytes_per_second == 22
    assert transfer.progress().elapsed_seconds == 6


def test_speed_before_first_frame_and_at_zero_elapsed(tmp_path):
    now = [10.0]
    transfer = Transfer(tmp_path, clock=lambda: now[0])
    now[0] = 12.0
    waiting = transfer.progress()
    assert waiting.elapsed_seconds == 2 and waiting.new_bytes_per_second == 0
    instant = Transfer(tmp_path / 'instant', clock=lambda: 0.0)
    result = instant.accept(decode(next(encode(b'test'))))
    assert result.complete and result.new_bytes_per_second == 0


def test_receive_map_tracks_gaps_resume_and_duplicates(tmp_path):
    frames = list(map(decode, encode(bytes(range(200)))))
    transfer = Transfer(tmp_path)
    last = transfer.accept(frames[1])
    assert len(last.coverage) == 100 and last.current_block == 66
    assert last.coverage[:66] == (0,)*66
    assert last.coverage[66:] == (2,)*34
    assert transfer.accept(frames[1]).coverage == last.coverage
    resumed = Transfer(tmp_path)
    complete = resumed.accept(frames[0])
    assert complete.coverage == (2,)*100 and complete.current_block == 0
