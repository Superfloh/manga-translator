import asyncio

import os
import pathlib
import sys

from typing import List

from PyQt5.QtGui import QPixmap, QImage
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QFileDialog
)

from helpers.drawer import ImageDrawer
from helpers.imageInfo import ImageInfo
from helpers.segmentation import Segmentation
from qt.main_window_ui import Ui_MainWindow
from PyQt5.QtCore import Qt
from qasync import QEventLoop, asyncSlot
import pickle


class Window(QMainWindow, Ui_MainWindow):

    @asyncSlot()
    async def start(self):
        print("async started")
        image_info = await self.segmentation.process_frame_full('./images/testing/1_jap.jpg')
        self.imageDrawer.image_data.append(image_info)
        self.imageDrawer.draw()

    @asyncSlot()
    async def redraw(self):
        if len(self.imageDrawer.image_data) > self.imageDrawer.loaded_image_index:
            image_info = self.imageDrawer.image_data[self.imageDrawer.loaded_image_index]
            translated_frame = await self.segmentation.redraw_frame(image_info)
            self.imageDrawer.image_data[self.imageDrawer.loaded_image_index].translated_frame = translated_frame
            self.imageDrawer.draw()
            print("redrawn image")

    @asyncSlot()
    async def re_translate(self):
        if len(self.imageDrawer.image_data) > self.imageDrawer.loaded_image_index:
            trans_res = await self.segmentation.re_translate_frame(self.imageDrawer.image_data[self.imageDrawer.loaded_image_index])
            index = 0
            for x in trans_res:
                self.imageDrawer.image_data[self.imageDrawer.loaded_image_index].text_areas_resized[index].translated_text = x.text
                index += 1
            await self.redraw()
            self.imageDrawer.update_selected_rect_info()

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

        self.redraw_button.clicked.connect(self.redraw)
        self.retranslate_button.clicked.connect(self.re_translate)

        self.imageDrawer = ImageDrawer(self)
        self.segmentation = Segmentation()

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


