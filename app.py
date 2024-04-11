import asyncio
import logging
import os
import pathlib
import sys
import traceback

import cv2
from PyQt5 import QtGui
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox, QLabel, QFileDialog
)
from PyQt5.uic import loadUi
from ultralytics import YOLO

from helpers.drawer import pointInRect, clear_pixmap, get_resized_image, positive_rect
from helpers.segmentation import Segmentation
from qt.main_window_ui import Ui_MainWindow
from PyQt5.QtCore import Qt, pyqtSlot, QRect
from asyncqt import QEventLoop, asyncSlot


class Window(QMainWindow, Ui_MainWindow):

    rects = [(100, 100, 100, 100)]

    def draw(self):
        clear_pixmap(self.original_image_pixmap)
        self.draw_images()
        self.draw_rects()
        self.update_image_containers()

    def draw_images(self):
        if self.current_original_image:
            self.original_image_pixmap = get_resized_image(
                self.current_original_image,
            )
        else:
            self.original_image_pixmap = QPixmap(640, 910)
            self.original_image_pixmap.fill(Qt.black)

    def draw_rects(self):
        painterInstance = QtGui.QPainter(self.original_image_pixmap)
        painterInstance.setRenderHint(QPainter.Antialiasing)
        pen_rect = QtGui.QPen(self.rect_color)
        pen_rect.setWidth(self.rect_border)

        pen_selected_rect = QtGui.QPen(self.selected_rect_color)
        pen_selected_rect.setWidth(self.rect_border)

        # top left (x1, y2) and (width, height)
        i = 0
        for x1, y1, w, h in self.rects:
            if i != self.selected_rect_index or self.editing_rect:
                painterInstance.setPen(pen_rect)
                painterInstance.drawRect(x1, y1, w, h)
            else:
                painterInstance.setPen(pen_selected_rect)
                painterInstance.drawRect(x1, y1, w, h)
            i += 1

        if self.editing_rect:
            painterInstance.setPen(pen_selected_rect)
            painterInstance.drawRect(self.editing_rect[0], self.editing_rect[1], self.editing_rect[2], self.editing_rect[3])

    def update_image_containers(self):
        self.original_image_container.setPixmap(self.original_image_pixmap)
        self.translated_image_container.setPixmap(self.translated_image_pixmap)

    def place_or_drag_rect(self, event: QtGui.QMouseEvent) -> None:
        x2 = event.pos().x()
        y2 = event.pos().y()
        print("click, x=" + str(x2) + ", y=" + str(y2))
        fits = True
        rect_index = 0
        for i in range(0, len(self.rects)):
            print(str(self.rects[i]) + " in: " + str(pointInRect((x2, y2), self.rects[i])))
            if pointInRect((x2, y2), self.rects[i]):
                fits = False
                rect_index = i

        if fits:
            self.drawing_rect = True
            self.editing_rect = (x2, y2, 0, 0)
        else:
            print("starting drag")
            self.moving_rect = True
            self.editing_rect = self.rects[rect_index]
            self.editing_rect_initial_pos = self.rects[rect_index]
            self.editing_rect_offset = [self.rects[rect_index][0] - x2, self.rects[rect_index][1] - y2]
            del self.rects[rect_index]


    @asyncSlot()
    async def start(self):
        print("async started")
        input_frames = [cv2.imread('./images/testing/1_jap.jpg')]
        self.segmentation_model = YOLO("./models/segmentation.pt")
        self.detection_model = YOLO("./models/detection.pt")
        detect_result = self.detection_model(input_frames, device="cpu", verbose=False),
        segmentation_result = self.segmentation_model(input_frames, device="cpu", verbose=False),
        print("models done")
        segmentation = Segmentation(self.translated_image_container)
        await segmentation.process_ml_results(detect_result, segmentation_result, input_frames[0])

    def mouse_released(self, event):
        print("released")
        if self.moving_rect or self.drawing_rect:
            self.drawing_rect = False
            self.moving_rect = False
            if abs(self.editing_rect[2]) > 30 and abs(self.editing_rect[3]) > 30:
                self.rects.append(positive_rect(self.editing_rect))
                self.selected_rect_index = len(self.rects)-1
            self.editing_rect = None
            self.draw()

    def mouse_moved(self, event):
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
                x2-self.editing_rect[0],
                y2-self.editing_rect[1]
            )
            self.draw()



    def enter_translated_image(self, event):
        self.mouse_in_translated_image = True
        print("in trans")

    def leave_translated_image(self, event):
        self.mouse_in_translated_image = False
        print("out trans")

    def enter_original_image(self, event):
        self.mouse_in_original_image = True
        print("in orig")

    def leave_original_image(self, event):
        self.mouse_in_original_image = False
        print("out orig")

    def load_images(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", options=options)
        if folder:
            self.loaded_images = []
            files = os.listdir(folder)
            for file in files:
                file_path = os.path.join(folder, file)
                suffix = pathlib.Path(file_path).suffix
                if os.path.isfile(file_path) and (suffix == ".jpg" or suffix == ".png" or suffix == ".jpeg"):
                    self.loaded_images.append(file_path)
        print("selected files")
        print(self.loaded_images)

        if len(self.loaded_images) > 0:
            self.current_original_image = self.loaded_images[0]
            self.draw()

    def __init__(self, loop=None, parent=None):
        super().__init__(parent)
        self.setupUi(self)
        self.loop = loop or asyncio.get_event_loop()

        # loaded images
        self.loaded_images = []
        self.loaded_image_index = 0
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

        # segment button
        self.segment_button.clicked.connect(self.start)

        # open image button
        self.load_images_button.clicked.connect(self.load_images)

        # original image container
        self.original_image_pixmap = QPixmap(643, 910)
        self.original_image_container.setPixmap(self.original_image_pixmap)

        self.original_image_container.mousePressEvent = self.place_or_drag_rect
        self.original_image_container.enterEvent = self.enter_original_image
        self.original_image_container.leaveEvent = self.leave_original_image

        # translated image container
        self.translated_image_pixmap = QPixmap(643, 910)
        self.translated_image_container.setPixmap(self.translated_image_pixmap)

        self.translated_image_container.enterEvent = self.enter_translated_image
        self.translated_image_container.leaveEvent = self.leave_translated_image



        self.centralwidget.mouseReleaseEvent = self.mouse_released
        # self.centralwidget.mouseMoveEvent = self.mouse_moved
        self.original_image_container.mouseMoveEvent = self.mouse_moved
        # self.translated_image_container.paintEvent = self.paintEvent


        #init
        self.draw_rects()




if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        loop = QEventLoop(app)
        asyncio.set_event_loop(loop)
        win = Window(loop)
        win.show()
        with loop:
            loop.run_forever()
    except:
        logging.error(traceback.format_exc())