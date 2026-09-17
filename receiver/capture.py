"""Capture adapters yield RGB frames. Protocol has no dependency on these."""
from pathlib import Path
import cv2


def png_frames(directory):
    paths = sorted(Path(directory).glob('*.png'))
    if not paths:
        raise OSError('no PNG frames')
    for path in paths:
        image = cv2.imread(str(path))
        if image is None:
            raise OSError(f'cannot read {path}')
        yield cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def video_frames(source, backend='auto'):
    api = {'auto': cv2.CAP_ANY, 'dshow': cv2.CAP_DSHOW,
           'msmf': cv2.CAP_MSMF, 'v4l2': cv2.CAP_V4L2}[backend]
    capture = cv2.VideoCapture(source, api)
    try:
        if not capture.isOpened():
            raise OSError(f'cannot open capture: {source}')
        while True:
            ok, image = capture.read()
            if not ok:
                break
            yield cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    finally:
        capture.release()
