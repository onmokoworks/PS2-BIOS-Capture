"""Capture-independent session handling used by the desktop tool."""
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import tempfile
import time
from .protocol import DecodeError, crc32
from .store import Store


@dataclass(frozen=True)
class Progress:
    received: int
    total: int
    source_size: int
    source_crc: int
    object_type: int
    complete: bool
    output: str = ''
    test_matches: bool | None = None
    received_bytes: int = 0
    last_index: int | None = None
    last_offset: int | None = None
    last_length: int = 0
    last_hex: str = ''
    last_was_new: bool = False
    first_missing_offset: int | None = None
    profile: int = 0
    version: int = 1
    restored_bytes: int = 0
    new_bytes: int = 0
    restored_frames: int = 0
    new_frames: int = 0
    elapsed_seconds: float = 0.0
    new_bytes_per_second: float = 0.0
    coverage: tuple[int, ...] = ()
    current_block: int | None = None


def fresh_directory(directory):
    """Keep old backups intact and isolate every fresh reception attempt."""
    root = Path(directory) / 'fresh'
    root.mkdir(parents=True, exist_ok=True)
    return Path(tempfile.mkdtemp(prefix=datetime.now().strftime('%Y%m%d-%H%M%S-'), dir=root))


class Transfer:
    def __init__(self, directory, *, clock=time.monotonic):
        self.clock = clock
        self.started_at = clock()
        self.completed_at = None
        self.directory = Path(directory)
        self.store = None
        self.output = None
        self.test_matches = None
        self.received_bytes = 0
        self.restored_bytes = 0
        self.restored_frames = 0
        self.last_frame = None
        self.last_was_new = False
        self.first_missing = 0
        self.block_size = 1
        self.block_bytes = []

    def track_coverage(self, frame):
        if not frame.payload:
            return
        end = frame.offset+len(frame.payload)
        for index in range(frame.offset//self.block_size, (end-1)//self.block_size+1):
            self.block_bytes[index] += min(end, (index+1)*self.block_size)-max(frame.offset, index*self.block_size)

    def accept(self, frame):
        if self.store is None:
            key = f'{frame.object_type}-{frame.session:08x}-{frame.size}-{frame.source_crc:08x}'
            if frame.version != 1:
                key = f'v{frame.version}-g{frame.profile}-' + key
            self.store = Store(self.directory / 'checkpoints' / key)
            self.received_bytes = sum(len(f.payload) for f in self.store.frames.values())
            self.restored_bytes = self.received_bytes
            self.restored_frames = len(self.store.frames)
            self.block_size = max(1, (frame.size+127)//128)
            self.block_bytes = [0]*((frame.size+self.block_size-1)//self.block_size)
            for saved in self.store.frames.values():
                self.track_coverage(saved)
        self.last_was_new = self.store.add(frame)
        self.last_frame = frame
        if self.last_was_new:
            self.received_bytes += len(frame.payload)
            self.track_coverage(frame)
        while self.first_missing in self.store.frames:
            self.first_missing += 1
        if self.store.complete and self.output is None:
            data = self.store.result()
            self.directory.mkdir(parents=True, exist_ok=True)
            label = 'TEST' if frame.object_type == 0 else 'ROM0'
            path = self.directory / f'{label}-{frame.session:08x}-{frame.source_crc:08x}.bin'
            if path.exists():
                if path.read_bytes() != data:
                    raise DecodeError('output already exists with different contents')
            else:
                self.store.write(path)
            if frame.object_type == 0 and len(data) == 65536 and crc32(data) == 0x4b07e436:
                from tools.test_pattern import pattern
                self.test_matches = data == pattern()
                if not self.test_matches:
                    raise DecodeError('fixed test pattern mismatch')
            self.output = path
            self.completed_at = self.clock()
        return self.progress()

    def progress(self):
        end = self.completed_at if self.completed_at is not None else self.clock()
        elapsed = max(0.0, end-self.started_at)
        if self.store is None or self.store.identity is None:
            return Progress(0, 0, 0, 0, 0, False, elapsed_seconds=elapsed)
        meta = self.store.identity
        last = self.last_frame
        new_bytes = self.received_bytes-self.restored_bytes
        coverage = tuple(0 if count == 0 else
                         2 if count == min(self.block_size, last.size-index*self.block_size) else 1
                         for index, count in enumerate(self.block_bytes))
        return Progress(len(self.store.frames), meta[5], meta[6], meta[8], meta[1],
                        self.output is not None, str(self.output or ''), self.test_matches,
                        self.received_bytes, last.index if last else None,
                        last.offset if last else None, len(last.payload) if last else 0,
                        last.payload[:32].hex(' ').upper() if last else '', self.last_was_new,
                        self.first_missing*last.capacity if self.first_missing < meta[5] else None,
                        last.profile, last.version, self.restored_bytes,
                        self.received_bytes-self.restored_bytes, self.restored_frames,
                        len(self.store.frames)-self.restored_frames,
                        elapsed, new_bytes/elapsed if elapsed > 0 else 0.0,
                        coverage, last.offset//self.block_size if last.payload else None)
