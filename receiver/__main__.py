import argparse
from collections import Counter
import sys
import time
from .capture import png_frames, video_frames
from .codec import decode_image
from .protocol import DecodeError, crc32
from .store import Store


def main():
    parser = argparse.ArgumentParser(description='PS2V COLOR4 receiver')
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument('--images')
    source.add_argument('--video')
    source.add_argument('--camera', type=int)
    parser.add_argument('--backend', choices=['auto', 'dshow', 'msmf', 'v4l2'], default='auto')
    parser.add_argument('--state', required=True, help='private checkpoint directory; reuse to resume')
    parser.add_argument('--output', required=True, help='new output file (never overwritten)')
    args = parser.parse_args()
    stream = None
    try:
        store = Store(args.state)
        errors = Counter()
        stream = png_frames(args.images) if args.images else video_frames(
            args.camera if args.camera is not None else args.video, args.backend)
        last = time.monotonic()
        if not store.complete:
            for image in stream:
                try:
                    store.add(decode_image(image))
                except DecodeError as error:
                    errors[str(error)] += 1
                if store.complete:
                    break
                if time.monotonic() - last > 2:
                    total = store.identity[5] if store.identity else '?'
                    print(f'valid={len(store.frames)}/{total}, rejected={sum(errors.values())}', file=sys.stderr)
                    last = time.monotonic()
        if not store.complete:
            print(f'incomplete: valid={len(store.frames)} missing={store.missing()[:32]} errors={dict(errors)}', file=sys.stderr)
            return 2
        store.write(args.output)
        print(f'complete: {len(store.result())} bytes CRC32={crc32(store.result()):08x}')
        return 0
    except KeyboardInterrupt:
        print('stopped; validated packets retained', file=sys.stderr)
        return 130
    except (OSError, DecodeError) as error:
        print(str(error), file=sys.stderr)
        return 1
    finally:
        if stream is not None:
            stream.close()


if __name__ == '__main__':
    raise SystemExit(main())
