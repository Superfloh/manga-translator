import asyncio
import logging
import os
import pathlib
import sys
import traceback

import cv2
from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtGui import QPixmap, QPainter, QBrush, QColor
from PyQt5.QtWidgets import (
    QApplication, QDialog, QMainWindow, QMessageBox, QLabel, QFileDialog
)
from PyQt5.uic import loadUi
from ultralytics import YOLO

from helpers.drawer import pointInRect, clear_pixmap, get_resized_image, positive_rect, ImageDrawer
from helpers.segmentation import Segmentation
from qt.main_window_ui import Ui_MainWindow
from PyQt5.QtCore import Qt, pyqtSlot, QRect
from asyncqt import QEventLoop, asyncSlot


class Window(QMainWindow, Ui_MainWindow):

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
        self.setupUi(self)
        self.loop = loop or asyncio.get_event_loop()

        # segment button
        self.segment_button.clicked.connect(self.start)

        # open image button
        self.load_images_button.clicked.connect(self.load_images)

        # original image container
        self.original_image_pixmap = QPixmap(643, 910)
        self.original_image_container.setPixmap(self.original_image_pixmap)

        # translated image container
        self.translated_image_pixmap = QPixmap(643, 910)
        self.translated_image_container.setPixmap(self.translated_image_pixmap)

        # self.centralwidget.mouseMoveEvent = self.mouse_moved

        # TODO: prevent images from being re-drawn every tick
        # self.translated_image_container.paintEvent = self.paintEvent

        self.imageDrawer = ImageDrawer(self)




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