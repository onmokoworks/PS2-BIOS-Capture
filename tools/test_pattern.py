"""Generate the BIOS-free fixed data transmitted by SOURCE_KIND=0."""
import argparse
from pathlib import Path


def pattern(size=65536):
    state = 0x50533256
    data = bytearray(size)
    for i in range(size):
        state ^= (state << 13) & 0xffffffff
        state ^= state >> 17
        state ^= (state << 5) & 0xffffffff
        data[i] = state & 255
    return bytes(data)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('output', type=Path)
    args = parser.parse_args()
    with args.output.open('xb') as stream:
        stream.write(pattern())
