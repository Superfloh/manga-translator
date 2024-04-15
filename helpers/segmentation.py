import threading
import time
import traceback

import cv2
import numpy as np
import torch
from PyQt5.QtGui import QPixmap
from typing import Union

from helpers.imageInfo import ImageInfo
from helpers.segmentation_copy import process_frame_v2
from translator.cleaners.deepfillv2 import DeepFillV2Cleaner
from translator.color_detect.models import get_color_detection_model
from translator.color_detect.utils import apply_transforms
from translator.core.plugin import Cleaner, Ocr, Translator, Drawer, Drawable
from translator.drawers.horizontal import HorizontalDrawer
from translator.ocr.huggingface_ja import JapaneseOcr
from translator.pipelines import FullConversion
from translator.translators.deepl import DeepLTranslator
from translator.utils import has_white, mask_text_and_make_bubble_mask, get_bounds_for_text, TranslatorGlobals, \
    get_model_path, apply_mask


class Segmentation:

    def __init__(self):
        self.translator = DeepLTranslator()
        self.ocr = JapaneseOcr()
        self.segmentor = FullConversion(
            translator=self.translator,
            ocr=self.ocr,
        )

    # - process_m1_results
    # 	- takes model results and returns clean frame, text mast, filtered detect result
    #
    # - detect_result
    # 	- bbox, cls, conf
    # 	- bbox contains all text boxes x1, y1, x2, y2
    # 	- cls = "text_bubble", "free_text"
    # 	- conf = confidence, 0-1
    async def pre_process_frame(self, image_path):
        image = cv2.imread(image_path)
        detect_result = self.segmentor.detection_model([image], device=self.segmentor.yolo_device, verbose=False),
        seg_result = self.segmentor.segmentation_model([image], device=self.segmentor.yolo_device, verbose=False),

        frame, frame_clean, text_mask, detect_result = await self.segmentor.process_ml_results(
            detect_result=detect_result[0][0],
            seg_result=seg_result[0][0],
            frame=image
        )
        # detect_result: list of tuple3 (rect, 'text_bubble', confidence)

        return await self.process_frame(frame, frame_clean, text_mask, detect_result, image_path)

    # to_translate:
    # - tuple: rect, img
    # - contains the coordinates of a rect and the contained extracted speech-bubble
    async def process_frame(self, input_frame, frame_clean, text_mask, detect_result, image_path):
        cleaned_frame, detect_result, to_translate = await process_frame_v2(input_frame, frame_clean, text_mask, detect_result)
        return ImageInfo(image_path, cleaned_frame, text_mask, detect_result, to_translate)
