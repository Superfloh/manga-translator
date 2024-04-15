import json
import os

import cv2
from google.cloud import vision
from google.cloud.vision_v1 import AnnotateImageResponse

from google.protobuf.json_format import MessageToJson


def google_vision_ocr(image_path):

    img = cv2.imread(image_path)
    _, encoded_image = cv2.imencode('.png', img)

    os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "google_vision_api_key.json"
    client = vision.ImageAnnotatorClient()

    api_image = vision.Image(content=encoded_image.tobytes())

    response = client.document_text_detection(image=api_image)
    text = response.text_annotations[0].description if response.text_annotations else ""
    print("text: " + text)

    with open("sample.json", "w", encoding='utf-8') as outfile:
        json_response = AnnotateImageResponse.to_json(response)
        outfile.write(json_response)

    return text
