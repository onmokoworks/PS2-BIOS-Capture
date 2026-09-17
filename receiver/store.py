"""Single-session disk checkpoint; only validated packets are retained."""
from pathlib import Path
from .protocol import DecodeError, crc32, decode


class Store:
    def __init__(self, directory=None):
        self.directory = Path(directory) if directory else None
        self.frames = {}
        self.identity = None
        if self.directory:
            self.directory.mkdir(parents=True, exist_ok=True)
            for path in sorted(self.directory.glob('*.pkt')):
                self.add(decode(path.read_bytes()), persist=False)

    def add(self, frame, persist=True):
        # Do not trust caller-constructed Frame instances either.
        frame = decode(frame.pack())
        if self.identity is not None and frame.identity != self.identity:
            raise DecodeError('different session/object')
        old = self.frames.get(frame.index)
        if old is not None:
            if old != frame:
                raise DecodeError('conflicting duplicate')
            return False
        if self.directory and persist:
            target = self.directory / f'{frame.index:08d}.pkt'
            temporary = target.with_suffix('.tmp')
            temporary.write_bytes(frame.pack())
            temporary.replace(target)
        self.identity = frame.identity
        self.frames[frame.index] = frame
        return True

    @property
    def complete(self):
        return self.identity is not None and len(self.frames) == self.identity[5]

    def missing(self):
        return [] if self.identity is None else [i for i in range(self.identity[5]) if i not in self.frames]

    def result(self):
        if not self.complete:
            raise DecodeError('incomplete transfer')
        data = b''.join(self.frames[i].payload for i in range(self.identity[5]))
        if len(data) != self.identity[6] or crc32(data) != self.identity[8]:
            raise DecodeError('source CRC/size')
        return data

    def write(self, filename):
        data = self.result()
        # Exclusive creation avoids overwriting a user's earlier backup.
        with Path(filename).open('xb') as stream:
            stream.write(data)
