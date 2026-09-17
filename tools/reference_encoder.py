import argparse
from pathlib import Path
import secrets
import cv2
from receiver.codec import render
from receiver.protocol import encode


def main():
    parser = argparse.ArgumentParser(description='Binary -> PS2V reference PNG sequence')
    parser.add_argument('input', type=Path)
    parser.add_argument('directory', type=Path)
    parser.add_argument('--session', type=lambda v: int(v, 0), default=None)
    args = parser.parse_args()
    args.directory.mkdir(parents=True, exist_ok=False)
    session = secrets.randbits(32) if args.session is None else args.session
    for i, packet in enumerate(encode(args.input.read_bytes(), session)):
        image = cv2.cvtColor(render(packet), cv2.COLOR_RGB2BGR)
        if not cv2.imwrite(str(args.directory / f'{i:08d}.png'), image):
            raise OSError('PNG write failed')
    print(f'{i+1} frames, session={session:08x}')


if __name__ == '__main__':
    main()
