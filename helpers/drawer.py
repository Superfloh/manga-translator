import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import QRect
from PyQt5.QtGui import QPixmap


def pointInRect(point, rect):
    x1, y1, w, h = rect
    x2, y2 = x1 + w, y1 + h
    x, y = point
    if (x1 < x and x < x2):
        if (y1 < y and y < y2):
            return True
    return False


def positive_rect(rect):
    x1, y1, w, h = rect
    if w < 0:
        x1 += w
        w *= -1
    if h < 0:
        y1 += h
        h *= -1
    return x1, y1, w, h


def clear_pixmap(pixmap):
    painterInstance = QtGui.QPainter(pixmap)
    painterInstance.eraseRect(QRect(0, 0, 2000, 2000))
    painterInstance.end()


def get_resized_image(image):
    # max height: 910
    # max width: 640
    im = cv2.imread(image)
    h = im.shape[0]
    w = im.shape[1]

    h_ratio = h/910
    w_ratio = w/640

    pixmap = QPixmap(image)

    if w_ratio > h_ratio:
        pixmap = pixmap.scaledToWidth(640)
    else:
        pixmap = pixmap.scaledToHeight(910)
    return pixmap