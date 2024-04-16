from typing import List

import cv2
from PyQt5.QtGui import QPixmap


class ImageInfo:

    def __init__(self, original_image_path, frame_clean, text_mask, detect_result, to_translate, ocr_results, translation_results, frame_translated, bboxes, draw_colors):
        self.original_image_path = original_image_path
        self.original_frame = cv2.imread(original_image_path)
        self.frame_clean = frame_clean
        self.text_mask = text_mask
        self.detect_result = detect_result
        self.ocr_results = ocr_results
        self.translation_results = translation_results
        self.translated_frame = frame_translated
        self.bboxes = bboxes
        self.draw_colors = draw_colors
        self.text_areas: List[ImageTextInfo] = self.to_translate_to_rects(to_translate)
        self.image_dimensions = self.set_image_dimensions()
        self.text_areas_resized = self.set_text_areas_resized()


    def set_image_dimensions(self):
        im = cv2.imread(self.original_image_path)
        h = im.shape[0]
        w = im.shape[1]

        h_ratio = h / 910
        w_ratio = w / 640

        return ImageDimensions(w, h, w_ratio, h_ratio)

    def set_text_areas_resized(self):
        text_areas = []
        ratio = max(self.image_dimensions.width_ratio, self.image_dimensions.height_ratio)
        for i in range(0, len(self.text_areas)):
            text_area = self.text_areas[i]
            text_areas.append(ImageTextInfo(
                tuple(round(x / ratio) for x in text_area.rect),
                text_area.ocr_text,
                text_area.translated_text
            ))
        return text_areas

    def to_translate_to_rects(self, to_translate):
        res = []
        for i in range(0, len(to_translate)):
            res.append(ImageTextInfo.from_to_translate(
                to_translate[i],
                self.ocr_results[i].text,
                self.translation_results[i].text
            ))
        return res

    # Takes the resized rects from the ui and resizes them back to original dimensions
    # Also creates the to_translate format of List[rect, frame]
    def get_resized_to_translate(self):
        resized_rects = []
        for text_info in self.text_areas_resized:
            ratio = max(self.image_dimensions.width_ratio, self.image_dimensions.height_ratio)
            x1, y1, x2, y2 = text_info.rect
            x1 *= ratio
            y1 *= ratio
            x2 *= ratio
            y2 *= ratio
            resized_rects.append(ImageTextInfo(
                (x1, y1, x2, y2),
                text_info.ocr_text,
                text_info.translated_text
            ))
        self.text_areas = resized_rects

        to_translate = []
        for text_info in resized_rects:
            x1, y1, x2, y2 = text_info.rect
            x1, y1, x2, y2 = [round(x1), round(y1), round(x2), round(y2)]
            to_translate.append([text_info.rect, self.original_frame[y1:y2, x1:x2].copy()])
        return to_translate


class ImageDimensions:
    def __init__(self, w, h, w_ratio, h_ratio):
        self.width = w
        self.height = h
        self.width_ratio = w_ratio
        self.height_ratio = h_ratio


class ImageTextInfo:
    def __init__(self, rect: tuple, ocr_text="", translated_text=""):
        self.rect = rect
        self.ocr_text = ocr_text
        self.translated_text = translated_text

    # takes an entry from to_translate
    @classmethod
    def from_to_translate(cls, to_translate_entry, ocr_res, trans_res):
        x1, y1, x2, y2 = to_translate_entry[0]
        return cls((x1, y1, x2 - x1, y2 - y1), ocr_res, trans_res)
