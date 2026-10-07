"""Exercise the GUI capture worker without a display or a physical camera."""
import queue
import threading
from types import SimpleNamespace
import pytest

pytest.importorskip('PIL')
pytest.importorskip('tkinter')
from receiver import gui
from receiver.codec import render
from receiver.protocol import encode


def test_worker_continues_after_completion_and_accepts_next_session(tmp_path, monkeypatch):
    first = [render(packet) for packet in encode(bytes(range(200)), 11)]
    second = [render(packet) for packet in encode(b'next object', 22)]
    images = first + first + second + second
    closed = []

    def stream(_):
        try:
            yield from images
        finally:
            closed.append(True)

    monkeypatch.setattr(gui, 'png_frames', stream)
    app = object.__new__(gui.App)
    app.args = SimpleNamespace(images='synthetic', video=None)
    app.stop = threading.Event()
    app.events = queue.Queue()
    app.preview = None
    app.receive(0, tmp_path)
    events = list(app.events.queue)
    completed = [value for kind, value in events if kind == 'complete']
    assert len(completed) == 2  # Duplicates never repeat completion notifications.
    assert completed[0].source_size == 200 and completed[1].source_size == 11
    assert app.preview is images[-1]
    assert [kind for kind, _ in events].count('done') == 1 and closed == [True]
    assert not [value for kind, value in events if kind == 'error']
    assert len(list(tmp_path.glob('*.bin'))) == 2


def test_worker_releases_stream_when_manually_stopped(tmp_path, monkeypatch):
    app = object.__new__(gui.App)
    app.args = SimpleNamespace(images='synthetic', video=None)
    app.stop = threading.Event()
    app.events = queue.Queue()
    app.preview = None
    closed = []

    def stream(_):
        try:
            yield render(next(encode(b'first', 1)))
            app.stop.set()
            yield render(next(encode(b'second', 2)))
        finally:
            closed.append(True)

    monkeypatch.setattr(gui, 'png_frames', stream)
    app.receive(0, tmp_path)
    assert closed == [True] and len(list(tmp_path.glob('*.bin'))) == 1
    assert any(kind == 'status' and '停止しました' in value for kind, value in app.events.queue)
