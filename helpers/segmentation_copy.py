import time
import cv2
import numpy as np
import sys
from ultralytics import YOLO
from translator.utils import (
    display_image,
    mask_text_and_make_bubble_mask,
    get_bounds_for_text,
    TranslatorGlobals,
    has_white,
    get_model_path,
    apply_mask
)
from translator.color_detect.utils import apply_transforms
import traceback
import threading
import torch
import asyncio
from typing import Union
from concurrent.futures import ThreadPoolExecutor
from translator.color_detect.models import get_color_detection_model
from translator.core.plugin import Drawable, Translator, Ocr, Drawer, Cleaner, OcrResult
from translator.cleaners.deepfillv2 import DeepFillV2Cleaner
from translator.drawers.horizontal import HorizontalDrawer

async def process_frame_v2(frame, frame_clean, text_mask, detect_result):
    try:

        to_translate = []
        index = 0
        # First pass, mask all bubbles
        for bbox, cls, conf in detect_result:
            index += 1
            try:
                # if conf < 0.65:
                #     continue

                # print(get_ocr(get_box_section(frame, box)))
                color = (0, 0, 255) if cls == 1 else (0, 255, 0)

                (x1, y1, x2, y2) = bbox

                class_name = cls

                bubble = frame[y1:y2, x1:x2]
                bubble_clean = frame_clean[y1:y2, x1:x2]
                bubble_text_mask = text_mask[y1:y2, x1:x2]

                if class_name == "text_bubble":
                    if has_white(bubble_text_mask):
                        text_only, bubble_mask = mask_text_and_make_bubble_mask(
                            bubble, bubble_text_mask, bubble_clean
                        )

                        frame[y1:y2, x1:x2] = bubble_clean
                        text_draw_bounds = get_bounds_for_text(bubble_mask)

                        pt1, pt2 = text_draw_bounds

                        pt1_x, pt1_y = pt1
                        pt2_x, pt2_y = pt2

                        pt1_x += x1
                        pt2_x += x1
                        pt1_y += y1
                        pt2_y += y1


                        to_translate.append([(pt1_x, pt1_y, pt2_x, pt2_y), text_only])

                        # frame = cv2.rectangle(frame,(x1,y1),(x2,y2),color=(255,255,0),thickness=2)
                        # debug_image(text_only,"Text Only")
                else:
                    free_text = frame[y1:y2, x1:x2]
                    if has_white(free_text):
                        text_only, _ = mask_text_and_make_bubble_mask(
                            free_text, bubble_text_mask, bubble_clean
                        )

                        to_translate.append([(x1, y1, x2, y2), text_only])

                    frame[y1:y2, x1:x2] = frame_clean[y1:y2, x1:x2]
            except:
                traceback.print_exc()

        return frame, detect_result, to_translate
    except:
        traceback.print_exc()


async def translate_text(to_translate, translator, ocr, color_detect_model, device="cpu", language="ja"):
    try:
        if len(to_translate) > 0:

            # third pass, draw text
            draw_colors = [(TranslatorGlobals.COLOR_BLACK, TranslatorGlobals.COLOR_BLACK, False) for x in to_translate]

            start = time.time()
            if color_detect_model is not None and len(draw_colors) > 0:
                with torch.no_grad():  # model needs work
                    with torch.inference_mode():

                        images = [apply_transforms(frame_with_text.copy()) for _, frame_with_text in to_translate]

                        draw_colors = [((y[0:3] * 255).astype(np.uint8), (y[3:-1] * 255).astype(np.uint8),
                                        (True if y[-1] > 0.5 else False)) for y in [
                                           x.cpu().numpy()
                                           for x in color_detect_model(
                                                torch.stack(images).to(
                                                    device
                                                )
                                            )
                                       ]]
            else:
                print("Using black since color detect model is 'None'")

            bboxes, images = zip(*to_translate)

            ocr_results = await ocr(list(images))

            # overwrite language
            ocr_results = [OcrResult(res.text, language) for res in ocr_results]

            translation_results = await translator(ocr_results)

            return bboxes, ocr_results, translation_results, draw_colors
    except:
        traceback.print_exc()
        return None
    return [], [], [], []

async def draw_text(frame, bboxes, translation_results, draw_colors, drawer=HorizontalDrawer()):
    to_draw = []
    for bbox, translation, color in zip(bboxes, translation_results, draw_colors):
        (x1, y1, x2, y2) = bbox
        draw_area = frame[y1:y2, x1:x2].copy()

        to_draw.append(Drawable(color=color, frame=draw_area, translation=translation))

    drawn_frames = await drawer(to_draw)

    for bbox, drawn_frame in zip(bboxes, drawn_frames):
        (x1, y1, x2, y2) = bbox
        drawn_frame, drawn_frame_mask = drawn_frame
        frame[y1:y2, x1:x2] = apply_mask(drawn_frame, frame[y1:y2, x1:x2], drawn_frame_mask)

    return frame
