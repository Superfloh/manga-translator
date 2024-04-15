from typing import List

import cv2
from PyQt5.QtGui import QPixmap


class ImageInfo:

    def __init__(self, original_image_path, frame_clean, text_mask, detect_result, to_translate):
        self.original_image_path = original_image_path
        self.pixmap = QPixmap(original_image_path)
        self.frame_clean = frame_clean
        self.text_mask = text_mask
        self.detect_result = detect_result
        self.text_areas: List[ImageTextInfo] = self.to_translate_to_rects(to_translate)
        self.image_dimensions = self.set_image_dimensions()
        self.text_areas_resized = self.set_text_areas_resized()

    def set_image_dimensions(self):
        im = cv2.imread(self.original_image_path)
        h = im.shape[0]
        w = im.shape[1]

        h_ratio = h / 910
        w_ratio = w / 640

        if w_ratio > h_ratio:
            self.pixmap = self.pixmap.scaledToWidth(640)
        else:
            self.pixmap = self.pixmap.scaledToHeight(910)

        return ImageDimensions(w, h, w_ratio, h_ratio)

    def set_text_areas_resized(self):
        text_areas = []
        ratio = max(self.image_dimensions.width_ratio, self.image_dimensions.height_ratio)
        for i in range(0, len(self.text_areas)):
            text_area = self.text_areas[i]
            text_areas.append(ImageTextInfo(tuple(round(x/ratio) for x in text_area.rect)))
        return text_areas

    def to_translate_to_rects(self, to_translate):
        res = []
        for i in range(0, len(to_translate)):
            res.append(ImageTextInfo.from_to_translate(to_translate[i]))
        return res


class ImageDimensions:
    def __init__(self, w,h,w_ratio, h_ratio):
        self.width = w
        self.height = h
        self.width_ratio = w_ratio
        self.height_ratio = h_ratio


class ImageTextInfo:
    def __init__(self, rect: tuple):
        self.rect = rect
        self.ocr_text = ""
        self.translated_text = ""

    # takes an entry from to_translate
    @classmethod
    def from_to_translate(cls, to_translate_entry):
        x1, y1, x2, y2 = to_translate_entry[0]
        return cls((x1, y1, x2-x1, y2-y1))
