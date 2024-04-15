from typing import List

import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor

from helpers.imageInfo import ImageInfo, ImageTextInfo


class ImageDrawer:
    rects = [(0, 0, 100, 100)]

    def __init__(self, window):
        self.window = window

        # Images
        self.image_data: List[ImageInfo] = []
        self.loaded_images = []
        self.loaded_image_index = 0     # index of the currently shown image in the UI
        self.current_original_image = ""

        # rect stuff
        self.moving_rect = False
        self.drawing_rect = False

        self.editing_rect = None
        self.editing_rect_initial_pos = None
        self.editing_rect_offset = [0, 0]
        self.selected_rect_index = 0

        # wheres the mouse
        self.mouse_in_translated_image = False
        self.mouse_in_original_image = False

        # settings
        self.rect_border = 10
        self.rect_color = QColor(255, 0, 0, 180)
        self.selected_rect_color = QColor(255, 110, 110, 200)

        self.window.original_image_container.mousePressEvent = self.place_or_drag_rect
        self.window.original_image_container.enterEvent = self.enter_original_image
        self.window.original_image_container.leaveEvent = self.leave_original_image
        self.window.original_image_container.mouseMoveEvent = self.mouse_moved

        self.window.translated_image_container.enterEvent = self.enter_translated_image
        self.window.translated_image_container.leaveEvent = self.leave_translated_image

        self.window.centralwidget.mouseReleaseEvent = self.mouse_released

    def draw_original_image_data(self):

        if len(self.image_data) > self.loaded_image_index:

            # draw the image
            image_info = self.image_data[self.loaded_image_index]
            self.window.original_image_pixmap = QPixmap(image_info.original_image_path).scaledToWidth(640)

            # draw the rects
            painter_instance = QtGui.QPainter(self.window.original_image_pixmap)
            painter_instance.setRenderHint(QPainter.Antialiasing)

            # pens
            pen_rect = QtGui.QPen(self.rect_color)
            pen_rect.setWidth(self.rect_border)
            pen_selected_rect = QtGui.QPen(self.selected_rect_color)
            pen_selected_rect.setWidth(self.rect_border)

            painter_instance.setPen(pen_rect)
            for i in range(0, len(image_info.text_areas_resized)):
                x1, y1, x2, y2 = image_info.text_areas_resized[i].rect
                if i == self.selected_rect_index:
                    painter_instance.setPen(pen_selected_rect)
                else:
                    painter_instance.setPen(pen_rect)
                painter_instance.drawRect(x1, y1, x2, y2)
            # editing rect
            if self.editing_rect:
                painter_instance.drawRect(self.editing_rect[0], self.editing_rect[1], self.editing_rect[2],
                                          self.editing_rect[3])
            painter_instance.end()
            self.update_image_containers()
        return

    def draw(self):
        clear_pixmap(self.window.original_image_pixmap)
        self.draw_original_image_data()

    def draw_images(self):
        if self.current_original_image:
            self.window.original_image_pixmap = get_resized_image(
                self.current_original_image,
            )
        else:
            self.window.original_image_pixmap = QPixmap(640, 910)
            self.window.original_image_pixmap.fill(Qt.black)

    def draw_rects(self):
        painter_instance = QtGui.QPainter(self.window.original_image_pixmap)
        painter_instance.setRenderHint(QPainter.Antialiasing)
        pen_rect = QtGui.QPen(self.rect_color)
        pen_rect.setWidth(self.rect_border)

        pen_selected_rect = QtGui.QPen(self.selected_rect_color)
        pen_selected_rect.setWidth(self.rect_border)

        # top left (x1, y2) and (width, height)
        i = 0
        for x1, y1, w, h in self.rects:
            if i != self.selected_rect_index or self.editing_rect:
                painter_instance.setPen(pen_rect)
                painter_instance.drawRect(x1, y1, w, h)
            else:
                painter_instance.setPen(pen_selected_rect)
                painter_instance.drawRect(x1, y1, w, h)
            i += 1

        if self.editing_rect:
            painter_instance.setPen(pen_selected_rect)
            painter_instance.drawRect(self.editing_rect[0], self.editing_rect[1], self.editing_rect[2],
                                      self.editing_rect[3])

    def update_image_containers(self):
        self.window.original_image_container.setPixmap(self.window.original_image_pixmap)
        self.window.translated_image_container.setPixmap(self.window.translated_image_pixmap)

    def place_or_drag_rect(self, event: QtGui.QMouseEvent) -> None:

        if len(self.image_data) > self.loaded_image_index:

            x2 = event.pos().x()
            y2 = event.pos().y()
            print("click, x=" + str(x2) + ", y=" + str(y2))
            fits = True
            rect_index = 0
            for i in range(0, len(self.image_data[self.loaded_image_index].text_areas_resized)):
                rect = self.image_data[self.loaded_image_index].text_areas_resized[i].rect
                # print(str(rect) + " in: " + str(pointInRect((x2, y2), rect)))
                if pointInRect((x2, y2), rect):
                    fits = False
                    rect_index = i

            if fits:
                print("starting editing")
                self.drawing_rect = True
                self.editing_rect = (x2, y2, 0, 0)
            else:
                print("starting drag")
                self.moving_rect = True
                self.editing_rect = self.image_data[self.loaded_image_index].text_areas_resized[rect_index].rect
                self.editing_rect_initial_pos = self.editing_rect
                self.editing_rect_offset = [
                    self.image_data[self.loaded_image_index].text_areas_resized[rect_index].rect[0] - x2,
                    self.image_data[self.loaded_image_index].text_areas_resized[rect_index].rect[1] - y2
                ]
                del self.image_data[self.loaded_image_index].text_areas_resized[rect_index]

    def mouse_moved(self, event):
        # print("mouse moved")
        if len(self.image_data) > self.loaded_image_index:
            x2 = event.pos().x()
            y2 = event.pos().y()
            if self.moving_rect and self.mouse_in_original_image:
                x2 += self.editing_rect_offset[0]
                y2 += self.editing_rect_offset[1]
                self.editing_rect = (x2, y2, self.editing_rect[2], self.editing_rect[3])
                self.draw()

            if self.drawing_rect and self.mouse_in_original_image:
                self.editing_rect = (
                    self.editing_rect[0],
                    self.editing_rect[1],
                    x2 - self.editing_rect[0],
                    y2 - self.editing_rect[1]
                )
                self.draw()

    def mouse_released(self, event):
        print("released")
        if self.moving_rect or self.drawing_rect and (len(self.image_data) > self.loaded_image_index):
            self.drawing_rect = False
            self.moving_rect = False
            if abs(self.editing_rect[2]) > 30 and abs(self.editing_rect[3]) > 30:
                self.image_data[self.loaded_image_index].text_areas_resized.append(
                    ImageTextInfo(positive_rect(self.editing_rect))
                )
                self.selected_rect_index = len(self.image_data[self.loaded_image_index].text_areas_resized) - 1
            self.editing_rect = None
            self.draw()


    def enter_translated_image(self, event):
        print("in trans")
        self.mouse_in_translated_image = True

    def leave_translated_image(self, event):
        print("out trans")
        self.mouse_in_translated_image = False

    def enter_original_image(self, event):
        print("in orig")
        self.mouse_in_original_image = True

    def leave_original_image(self, event):
        print("out orig")
        self.mouse_in_original_image = False


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
    # painterInstance.eraseRect(QRect(0, 0, 100, 100))
    painterInstance.end()


def get_resized_image(image):
    # max height: 910
    # max width: 640
    im = cv2.imread(image)
    h = im.shape[0]
    w = im.shape[1]

    h_ratio = h / 910
    w_ratio = w / 640

    pixmap = QPixmap(image)

    if w_ratio > h_ratio:
        pixmap = pixmap.scaledToWidth(640)
    else:
        pixmap = pixmap.scaledToHeight(910)
    return pixmap
