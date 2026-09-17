"""Image-independent, strict PS2V v1 RAW packet codec."""
from dataclasses import dataclass
import struct
import zlib

HEADER = struct.Struct('<4sBBBB10I')
HEADER_SIZE, PACKET_SIZE, PAYLOAD = 48, 180, 132
MAX_SOURCE = 16 * 1024 * 1024


class DecodeError(ValueError):
    pass


def crc32(data):
    return zlib.crc32(data) & 0xffffffff


@dataclass(frozen=True)
class Frame:
    object_type: int
    session: int
    index: int
    count: int
    offset: int
    size: int
    encoded_size: int
    source_crc: int
    payload: bytes

    @property
    def identity(self):
        return (1, self.object_type, 4, 0, self.session, self.count,
                self.size, self.encoded_size, self.source_crc)

    def pack(self):
        head = HEADER.pack(b'PS2V', 1, self.object_type, 4, 0,
                           self.session, self.index, self.index ^ 0xffffffff,
                           self.count, len(self.payload), self.offset, self.size,
                           self.encoded_size, self.source_crc, 0)
        packet = head[:44] + struct.pack('<I', crc32(head[:44] + self.payload)) + self.payload
        return packet.ljust(PACKET_SIZE, b'\0')


def decode(packet):
    if len(packet) != PACKET_SIZE:
        raise DecodeError('packet size')
    (magic, version, obj, mode, flags, session, index, inverse, count,
     length, offset, size, encoded, source_crc, frame_crc) = HEADER.unpack_from(packet)
    if (magic, version, mode, flags) != (b'PS2V', 1, 4, 0) or obj not in (0, 1):
        raise DecodeError('unsupported protocol/object')
    if size > MAX_SOURCE or encoded != size:
        raise DecodeError('source size/encoding')
    expected_count = max(1, (size + PAYLOAD - 1) // PAYLOAD)
    if count != expected_count or index >= count or inverse != index ^ 0xffffffff:
        raise DecodeError('index/count/inverse')
    if offset != index * PAYLOAD or length != min(PAYLOAD, size - offset):
        raise DecodeError('offset/length')
    payload = bytes(packet[48:48 + length])
    if crc32(packet[:44] + payload) != frame_crc:
        raise DecodeError('frame CRC')
    if any(packet[48 + length:]):
        raise DecodeError('nonzero padding')
    return Frame(obj, session, index, count, offset, size, encoded, source_crc, payload)


def encode(data, session=1, object_type=0):
    if len(data) > MAX_SOURCE or object_type not in (0, 1) or not 0 <= session <= 0xffffffff:
        raise ValueError('unsupported source/session')
    count = max(1, (len(data) + PAYLOAD - 1) // PAYLOAD)
    checksum = crc32(data)
    for index in range(count):
        offset = index * PAYLOAD
        yield Frame(object_type, session, index, count, offset, len(data), len(data),
                    checksum, bytes(data[offset:offset + PAYLOAD])).pack()
