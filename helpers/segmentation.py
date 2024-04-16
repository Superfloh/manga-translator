import cv2

from helpers.imageInfo import ImageInfo
from helpers.segmentation_copy import process_frame_v2, translate_text, draw_text
from translator.color_detect.models import get_color_detection_model
from translator.core.plugin import TranslatorResult, OcrResult
from translator.ocr.easy_ocr import EasyOcr
from translator.ocr.google_vision_ocr import GoogleVisionOcr
from translator.ocr.huggingface_ja import JapaneseOcr
from translator.ocr.tessaract_ocr import TesseractOcr
from translator.pipelines import FullConversion
from translator.translators.deepl import DeepLTranslator
from translator.utils import get_model_path


class Segmentation:

    def __init__(self, ocr_index=0, translator_index=0, language_index=0):
        self.language = self.get_language(language_index)
        print("created segmentor with language " + self.language)
        self.translator = self.get_translator(translator_index)
        self.ocr = self.get_ocr(ocr_index)
        self.segmentor = FullConversion(
            translator=self.translator,
            ocr=self.ocr,
        )
        self.color_detect_model = get_color_detection_model(
            weights_path=get_model_path("color_detection.pt"), device="cpu"
        )
        self.color_detect_model.eval()

    # "Japanese", "Google Vision", "Tesseract", "Easy OCR"
    def get_ocr(self, index):
        if index == 0:
            return JapaneseOcr()
        if index == 1:
            return GoogleVisionOcr()
        if index == 2:
            return TesseractOcr()
        if index == 3:
            return EasyOcr()

    def get_translator(self, index):
        if index == 0:
            return DeepLTranslator("")

    def get_language(self, index):
        if index == 0:
            return "ja"
        if index == 1:
            return "zh"

    async def process_frame_full(self, image_path):
        image = cv2.imread(image_path)
        detect_result = self.segmentor.detection_model([image], device=self.segmentor.yolo_device, verbose=False),
        seg_result = self.segmentor.segmentation_model([image], device=self.segmentor.yolo_device, verbose=False),

        frame, frame_clean, text_mask, detect_result = await self.segmentor.process_ml_results(
            detect_result=detect_result[0][0],
            seg_result=seg_result[0][0],
            frame=image
        )

        # detect_result: list of tuple3 (rect, 'text_bubble', confidence)
        cleaned_frame, detect_result, to_translate = await process_frame_v2(
            frame.copy(),
            frame_clean,
            text_mask,
            detect_result
        )

        # bboxes = List[rects]
        # ocr_results = List[{text: ocr text}]
        # translation_results = List[String]
        bboxes, ocr_results, translation_results, draw_colors = await translate_text(
            to_translate,
            self.translator,
            self.ocr,
            self.color_detect_model,
            "cpu",
            self.language
        )

        translated_frame = await draw_text(cleaned_frame.copy(), bboxes, translation_results, draw_colors)

        return ImageInfo(
            image_path,
            cleaned_frame.copy(),
            text_mask,
            detect_result,
            to_translate,
            ocr_results,
            translation_results,
            translated_frame,
            bboxes,
            draw_colors
        )

    # to_translate:
    # - tuple: rect, img
    # - contains the coordinates of a rect and the contained extracted speech-bubble

    # translation results changed, redraw them
    async def redraw_frame(self, image_info: ImageInfo):
        translated_frame = await draw_text(
            image_info.frame_clean.copy(),
            image_info.bboxes,
            map(lambda area: TranslatorResult(area.translated_text), image_info.text_areas_resized),
            image_info.draw_colors
        )
        return translated_frame

    async def re_translate_frame(self, image_info: ImageInfo):
        res = []
        for x in image_info.text_areas_resized:
            res.append(OcrResult(x.ocr_text, self.language))
        return await self.translator(res)
