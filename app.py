import asyncio
import logging
import os
import pathlib
import sys
import traceback
from typing import List

import cv2
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor, QImage
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox, QLabel, QFileDialog
)
from PyQt5.uic import loadUi
from ultralytics import YOLO

from helpers.drawer import pointInRect, clear_pixmap, get_resized_image, positive_rect, ImageDrawer
from helpers.googleVision import google_vision_ocr
from helpers.imageInfo import ImageInfo
from helpers.segmentation import Segmentation
from qt.main_window_ui import Ui_MainWindow
from PyQt5.QtCore import Qt, pyqtSlot, QRect
from asyncqt import QEventLoop, asyncSlot
import pickle


class Window(QMainWindow, Ui_MainWindow):

    @asyncSlot()
    async def start(self):
        print("async started")
        segmentation = Segmentation()
        image_info = await segmentation.pre_process_frame('./images/testing/1_jap.jpg')
        #with open('data.pkl', 'wb') as file:
        #    pickle.dump(image_info, file)
        height, width, channel = image_info.frame_clean.shape
        bytesPerLine = 3 * width
        qImg = QImage(image_info.frame_clean.data, width, height, bytesPerLine, QImage.Format_RGB888)
        self.translated_image_pixmap = QPixmap(qImg).scaledToWidth(640)
        # google_vision_ocr('./images/testing/1_jap.jpg')
        self.imageDrawer.image_data.append(image_info)
        self.imageDrawer.draw()
        # self.imageDrawer.draw_image_info(image_info)

    def start2(self):
        with open('data.pkl', 'rb') as file:
            loaded_data = pickle.load(file)
            print("data loaded")
            self.imageDrawer.image_data.append(loaded_data)
            print("data appended")
            self.imageDrawer.draw()
            print("data drawn")

    def load_images(self):
        options = QFileDialog.Options()
        options |= QFileDialog.DontUseNativeDialog
        folder = QFileDialog.getExistingDirectory(self, "Select Folder", options=options)
        if folder:
            loaded_images = []
            files = os.listdir(folder)
            for file in files:
                file_path = os.path.join(folder, file)
                suffix = pathlib.Path(file_path).suffix
                if os.path.isfile(file_path) and (suffix == ".jpg" or suffix == ".png" or suffix == ".jpeg"):
                    loaded_images.append(file_path)
            print("selected files")
            print(loaded_images)

            if len(loaded_images) > 0:
                self.imageDrawer.loaded_images = loaded_images
                self.imageDrawer.current_original_image = loaded_images[0]
                self.imageDrawer.draw()

    def __init__(self, loop=None, parent=None):
        super().__init__(parent)
        self.loop = loop or asyncio.get_event_loop()
        self.setupUi(self)
        self.showMaximized()
        self.loop = loop or asyncio.get_event_loop()

        # image data
        self.image_data: List[ImageInfo] = []
        self.loaded_image_index = 0

        # segment button
        self.segment_button.clicked.connect(self.start)

        # open image button
        self.load_images_button.clicked.connect(self.load_images)

        # original image container
        self.original_image_pixmap = QPixmap(640, 910)
        self.original_image_pixmap.fill(Qt.black)
        self.original_image_container.setPixmap(self.original_image_pixmap)

        # translated image container
        self.translated_image_pixmap = QPixmap(640, 910)
        self.translated_image_pixmap.fill(Qt.black)
        self.translated_image_container.setPixmap(self.translated_image_pixmap)

        # self.centralwidget.mouseMoveEvent = self.mouse_moved

        # TODO: prevent images from being re-drawn every tick
        # self.translated_image_container.paintEvent = self.paintEvent

        self.imageDrawer = ImageDrawer(self)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Delete:
            self.imageDrawer.delete_selected_rect()


def custom_exception_handler(loop, context):
    # first, handle with default handler
    print("eeee")
    loop.default_exception_handler(context)

    exception = context.get('exception')
    print(context)
    loop.stop()

if __name__ == "__main__":
    app = QApplication(sys.argv)
    loop = QEventLoop(app)
    asyncio.set_event_loop(loop)
    win = Window(loop)
    win.show()
    loop.set_exception_handler(custom_exception_handler)
    with loop:
        loop.run_forever()


