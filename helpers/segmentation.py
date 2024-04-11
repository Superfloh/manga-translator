import time

import cv2
import numpy as np
from PyQt5.QtGui import QPixmap

from translator.cleaners.deepfillv2 import DeepFillV2Cleaner
from translator.core.plugin import Cleaner


class Segmentation:

    def __init__(self, translated_image_container, cleaner: Cleaner = DeepFillV2Cleaner()):
        self.cleaner = cleaner
        self.translated_image_container = translated_image_container

    def filter_results(self, results, min_confidence=0.1):
        bounding_boxes = np.array(results.boxes.xyxy.cpu(), dtype="int")
        classes = np.array(results.boxes.cls.cpu(), dtype="int")
        confidence = np.array(results.boxes.conf.cpu(), dtype="float")
        raw_results: list[tuple[tuple[int, int, int, int], str, float]] = []

        for box, obj_class, conf in zip(bounding_boxes, classes, confidence):
            if conf >= min_confidence:
                raw_results.append((box, results.names[obj_class], conf))

        raw_results.sort(key=lambda a: 1 - a[2])

        results = raw_results
        return results

    async def process_ml_results(self, detect_result, seg_result, frame):
        print("process")
        text_mask = np.zeros_like(frame, dtype=frame.dtype)

        detect_result = detect_result[0][0]
        seg_result = seg_result[0][0]

        if seg_result.masks is not None:  # Fill in segmentation results
            for seg in list(map(lambda a: a.astype("int"), seg_result.masks.xy)):
                cv2.fillPoly(text_mask, [seg], (255, 255, 255))

        detect_result = self.filter_results(detect_result)
        print("filter done")

        for bbox, cls, conf in detect_result:  # fill in text free results
            if cls == "text_free":
                (x1, y1, x2, y2) = bbox
                text_mask = cv2.rectangle(
                    text_mask, (x1, y1), (x2, y2), (255, 255, 255), -1
                )

        start = time.time()

        print("starting cleaner")
        frame_clean, text_mask = await self.cleaner(
            frame=frame, mask=text_mask, detection_results=detect_result
        )  # segmentation_results.boxes.xyxy.cpu().numpy()

        print(f"Inpainting => {time.time() - start} seconds")

        cv2.imwrite("clean.jpg", frame_clean)
        cv2.imwrite("frame.jpg", frame)

        pixmap = QPixmap('./clean.jpg')
        pixmap = pixmap.scaledToWidth(650)
        self.translated_image_container.setPixmap(pixmap)

        return frame, frame_clean, text_mask, detect_result
