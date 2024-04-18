from typing import List

import cv2
from PyQt5 import QtGui
from PyQt5.QtCore import QRect, Qt
from PyQt5.QtGui import QPixmap, QPainter, QColor, QFont, QImage
from PyQt5.QtWidgets import QApplication

from helpers.imageInfo import ImageInfo, ImageTextInfo


class ImageDrawer:
    rects = [(0, 0, 100, 100)]

    def __init__(self, window):
        self.window = window

        # Images
        self.image_data: List[ImageInfo] = []
        self.loaded_image_index = 0  # index of the currently shown image in the UI

        # rects
        self.selected_rect_index = -1

        # settings
        self.rect_border = 10
        self.rect_color = QColor(255, 0, 0, 180)
        self.selected_rect_color = QColor(255, 110, 110, 200)

        # selection
        self.show_result = True
        self.show_clean = False
        self.show_mask = False

        self.window.original_image_container.mousePressEvent = self.select_rect

        self.window.original_text_input.textChanged.connect(self.original_text_changed)
        self.window.translation_text_input.textChanged.connect(self.translated_text_changed)

    def set_show(self, show_result=False, show_clean=False, show_mask=False):
        self.show_result = show_result
        self.show_clean = show_clean
        self.show_mask = show_mask
        self.draw()

    def select_rect(self, event):
        if len(self.image_data) > self.loaded_image_index:
            x2 = event.pos().x()
            y2 = event.pos().y()
            rect_index = -1
            for i in range(0, len(self.image_data[self.loaded_image_index].text_areas_resized)):
                rect = self.image_data[self.loaded_image_index].text_areas_resized[i].rect
                if pointInRect((x2, y2), rect):
                    rect_index = i
            if rect_index > -1:
                self.selected_rect_index = rect_index
                self.update_selected_rect_info()
                self.draw()

    def update_selected_rect_info(self):
        selected = self.image_data[self.loaded_image_index].text_areas_resized[self.selected_rect_index]
        rect = selected.rect
        self.window.selected_rect_label.setText("Index: " +
                                                str(self.selected_rect_index) +
                                                " (" + str(rect[0]) + ", " +
                                                str(rect[1]) + ", " + str(rect[2]) +
                                                ", " + str(rect[3]) + ")")
        self.window.original_text_input.setText(selected.ocr_text)
        self.window.translation_text_input.setText(selected.translated_text)

    def draw_original_image_data(self):

        if len(self.image_data) > self.loaded_image_index:

            # draw the original image
            image_info = self.image_data[self.loaded_image_index]
            self.window.original_image_pixmap = QPixmap(image_info.original_image_path).scaledToWidth(640)

            # draw the translated image
            height, width, channel = image_info.translated_frame.shape
            bytes_per_line = 3 * width
            if self.show_result:
                q_img = QImage(image_info.translated_frame.data, width, height, bytes_per_line, QImage.Format_RGB888)
            elif self.show_clean:
                q_img = QImage(image_info.frame_clean.data, width, height, bytes_per_line, QImage.Format_RGB888)
            elif self.show_mask:
                q_img = QImage(image_info.text_mask.data, width, height, bytes_per_line, QImage.Format_RGB888)
            else:
                return

            self.window.translated_image_pixmap = QPixmap(q_img).scaledToWidth(640)

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
                painter_instance.setFont(QFont("times", 22))
                painter_instance.drawText(x1 - 5, y1 - 5, str(x1) + ", " + str(y1))

            painter_instance.end()
            self.update_image_containers()
        return

    def draw(self):
        self.draw_original_image_data()

    def update_image_containers(self):
        self.window.original_image_container.setPixmap(self.window.original_image_pixmap.scaledToWidth(640))
        self.window.translated_image_container.setPixmap(self.window.translated_image_pixmap.scaledToWidth(640))

    def original_text_changed(self):
        if len(self.image_data) > self.loaded_image_index and self.selected_rect_index >= 0:
            self.image_data[self.loaded_image_index].text_areas_resized[
                self.selected_rect_index].ocr_text = self.window.original_text_input.toPlainText()

    def translated_text_changed(self):
        if len(self.image_data) > self.loaded_image_index and self.selected_rect_index >= 0:
            self.image_data[self.loaded_image_index].text_areas_resized[
                self.selected_rect_index].translated_text = self.window.translation_text_input.toPlainText()
            print("translated changed to " + self.image_data[self.loaded_image_index].text_areas_resized[
                self.selected_rect_index].translated_text)


def pointInRect(point, rect):
    x1, y1, w, h = rect
    x2, y2 = x1 + w, y1 + h
    x, y = point
    if (x1 < x and x < x2):
        if (y1 < y and y < y2):
            return True
    return False
