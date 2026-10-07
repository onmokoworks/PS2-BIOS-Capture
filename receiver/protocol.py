"""Image-independent, strict PS2V v1 RAW packet codec."""
from dataclasses import dataclass
import struct
import zlib

HEADER = struct.Struct('<4sBBBB10I')
HEADER_SIZE, PACKET_SIZE, PAYLOAD = 48, 180, 132
MAX_SOURCE = 16 * 1024 * 1024
GRIDS = {0: (36, 20, 8), 1: (48, 26, 6), 2: (72, 40, 4)}


def packet_size(profile):
    cols, rows, _ = GRIDS[profile]
    return cols * rows // 4


def payload_capacity(profile):
    return packet_size(profile) - HEADER_SIZE


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
    version: int = 1
    profile: int = 0

    @property
    def capacity(self):
        return payload_capacity(self.profile)

    @property
    def identity(self):
        return (self.version, self.object_type, 4, self.profile, self.session, self.count,
                self.size, self.encoded_size, self.source_crc)

    def pack(self):
        head = HEADER.pack(b'PS2V', self.version, self.object_type, 4, self.profile,
                           self.session, self.index, self.index ^ 0xffffffff,
                           self.count, len(self.payload), self.offset, self.size,
                           self.encoded_size, self.source_crc, 0)
        packet = head[:44] + struct.pack('<I', crc32(head[:44] + self.payload)) + self.payload
        return packet.ljust(packet_size(self.profile), b'\0')


def decode(packet):
    if len(packet) < HEADER_SIZE:
        raise DecodeError('packet size')
    (magic, version, obj, mode, flags, session, index, inverse, count,
     length, offset, size, encoded, source_crc, frame_crc) = HEADER.unpack_from(packet)
    if magic != b'PS2V' or version not in (1, 2) or mode != 4 or obj not in (0, 1):
        raise DecodeError('unsupported protocol/object')
    if flags not in GRIDS or (version == 1 and flags != 0) or len(packet) != packet_size(flags):
        raise DecodeError('profile/packet size')
    capacity = payload_capacity(flags)
    if size > MAX_SOURCE or encoded != size:
        raise DecodeError('source size/encoding')
    expected_count = max(1, (size + capacity - 1) // capacity)
    if count != expected_count or index >= count or inverse != index ^ 0xffffffff:
        raise DecodeError('index/count/inverse')
    if offset != index * capacity or length != min(capacity, size - offset):
        raise DecodeError('offset/length')
    payload = bytes(packet[48:48 + length])
    if crc32(packet[:44] + payload) != frame_crc:
        raise DecodeError('frame CRC')
    if any(packet[48 + length:]):
        raise DecodeError('nonzero padding')
    return Frame(obj, session, index, count, offset, size, encoded, source_crc, payload, version, flags)


def encode(data, session=1, object_type=0, profile=0, version=1):
    if len(data) > MAX_SOURCE or object_type not in (0, 1) or not 0 <= session <= 0xffffffff:
        raise ValueError('unsupported source/session')
    if profile not in GRIDS or version not in (1, 2) or (version == 1 and profile != 0):
        raise ValueError('unsupported version/profile')
    capacity = payload_capacity(profile)
    count = max(1, (len(data) + capacity - 1) // capacity)
    checksum = crc32(data)
    for index in range(count):
        offset = index * capacity
        yield Frame(object_type, session, index, count, offset, len(data), len(data),
                    checksum, bytes(data[offset:offset + capacity]), version, profile).pack()
