"""COLOR4 renderer and calibrated finder-based decoder; no capture IO."""
import itertools
import cv2
import numpy as np
from .protocol import PACKET_SIZE, DecodeError, decode

PALETTE = np.array([[32, 32, 32], [224, 224, 224],
                    [224, 192, 32], [32, 64, 224]], dtype=np.uint8)
FINDERS = np.array([[24, 20], [296, 20], [24, 204], [296, 204]], np.float32)


def render(packet):
    if len(packet) != PACKET_SIZE:
        raise ValueError('packet size')
    image = np.zeros((224, 320, 3), np.uint8)
    for cx, cy in FINDERS.astype(int):
        image[cy-8:cy+8, cx-8:cx+8] = 255
        image[cy-4:cy+4, cx-4:cx+4] = 0
        image[cy-2:cy+2, cx-2:cx+2] = 255
    for k, color in enumerate(PALETTE):
        image[12:28, 64+48*k:96+48*k] = color
    raw = np.frombuffer(packet, np.uint8)
    symbols = ((raw[:, None] >> np.array([6, 4, 2, 0])) & 3).reshape(20, 36)
    image[32:192, 16:304] = PALETTE[symbols].repeat(8, axis=0).repeat(8, axis=1)
    return image


def locate(image):
    gray = cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)
    _, mask = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    if hierarchy is None:
        raise DecodeError('finders missing')
    points = []
    for i, contour in enumerate(contours):
        child = hierarchy[0, i, 2]
        if child < 0 or hierarchy[0, child, 2] < 0:
            continue
        x, y, w, h = cv2.boundingRect(contour)
        area = cv2.contourArea(contour)
        if w < 8 or h < 8 or not .4 < w / h < 2.5 or area < .65 * (w-1)*(h-1):
            continue
        child_area = cv2.contourArea(contours[child])
        if not .12 < child_area / max(area, 1) < .65:
            continue
        points.append((x + (w-1)/2, y + (h-1)/2))
    # The MVP assumes an upright capture, with at most modest perspective.
    if not 4 <= len(points) <= 12:
        raise DecodeError('finder candidates')
    return points


def sample(image, points):
    points = sorted(points, key=lambda p: p[1])
    ordered = sorted(points[:2]) + sorted(points[2:])
    target = FINDERS - .5  # pixel center convention for even-sized markers
    transform = cv2.getPerspectiveTransform(np.array(ordered, np.float32), target)
    normalized = cv2.warpPerspective(image, transform, (320, 224))
    palette = np.array([normalized[16:24, 72+48*k:88+48*k].mean(axis=(0, 1))
                        for k in range(4)])
    distances = np.linalg.norm(palette[:, None] - palette[None, :], axis=2)
    if np.min(distances + np.eye(4)*1000) < 30:
        raise DecodeError('palette collapsed')
    # Average the central 3x3 pixels; avoid analog cell edges.
    cells = normalized[32:192, 16:304].reshape(20, 8, 36, 8, 3)
    colors = cells[:, 3:6, :, 3:6].mean(axis=(1, 3))
    symbols = ((colors[:, :, None, :] - palette)**2).sum(axis=3).argmin(axis=2)
    groups = symbols.reshape(-1, 4)
    return ((groups[:, 0] << 6) | (groups[:, 1] << 4) |
            (groups[:, 2] << 2) | groups[:, 3]).astype(np.uint8).tobytes()


def decode_image(image):
    if image is None or image.ndim != 3 or image.shape[2] != 3 or image.dtype != np.uint8:
        raise DecodeError('expected RGB uint8 image')
    last = 'finders'
    for points in itertools.combinations(locate(image), 4):
        try:
            return decode(sample(image, points))
        except DecodeError as error:
            last = str(error)
    raise DecodeError(last)
