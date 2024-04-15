import os

import cv2
import numpy
from translator.utils import simplify_lang_code
from translator.core.plugin import (
    Ocr,
    OcrResult,
    PluginArgument,
)

class GoogleVisionOcr(Ocr):
    """Supports all the languages listed"""

    default_language = "ja"

    def __init__(self, language=default_language) -> None:
        super().__init__()
        self.language = language

    async def do_ocr(self, batch: list[numpy.ndarray]):
        from google.cloud import vision
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_vision_api_key.json"
        client = vision.ImageAnnotatorClient()
        results = []
        for x in batch:
            # vision works better with some space
            x = cv2.copyMakeBorder(x, 10, 10, 10, 10, cv2.BORDER_CONSTANT, value=[255,255,255])
            _, encoded_image = cv2.imencode('.jpg', x)
            api_image = vision.Image(content=encoded_image.tobytes())
            response = client.document_text_detection(image=api_image)
            text = response.text_annotations[0].description.replace("\n", "") if response.text_annotations else ""
            print("text: " + text)
            results.append(OcrResult(text=text, language=simplify_lang_code(self.language)))

        return results

    @staticmethod
    def get_name() -> str:
        return "Google Vision Ocr"

    @staticmethod
    def is_valid() -> bool:
        try:
            import traceback
            import logging
            from google.cloud import vision
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_vision_api_key.json"
            vision.ImageAnnotatorClient()
            return True
        except:
            print(
                "Either google cloud vision is having an error or you do not have it installed!."
            )
            print(
                "Google vision credentials have to be in google_vision_api_key.json"
            )
            logging.error(traceback.format_exc())
            return False

    @staticmethod
    def get_arguments() -> list[PluginArgument]:
        return []
