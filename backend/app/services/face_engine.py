from pathlib import Path

import cv2
import numpy as np


BASE_DIR = Path(__file__).resolve().parent.parent.parent

MODEL_DIR = BASE_DIR / "app" / "models" / "ai"

YUNET_MODEL = MODEL_DIR / "face_detection_yunet_2023mar.onnx"
SFACE_MODEL = MODEL_DIR / "face_recognition_sface_2021dec.onnx"


class FaceEngine:

    def __init__(self):

        if not YUNET_MODEL.exists():
            raise FileNotFoundError(
                f"YuNet model not found: {YUNET_MODEL}"
            )

        if not SFACE_MODEL.exists():
            raise FileNotFoundError(
                f"SFace model not found: {SFACE_MODEL}"
            )

        self.detector = cv2.FaceDetectorYN.create(
            str(YUNET_MODEL),
            "",
            (320, 320),
            0.6,
            0.3,
            5000
        )

        self.recognizer = cv2.FaceRecognizerSF.create(
            str(SFACE_MODEL),
            ""
        )

    def detect_faces(self, image):

        if image is None:
            return []

        height, width = image.shape[:2]

        self.detector.setInputSize((width, height))

        _, faces = self.detector.detect(image)

        if faces is None:
            return []

        return faces

    def extract_feature(self, image, face):

        aligned = self.recognizer.alignCrop(
            image,
            face
        )

        feature = self.recognizer.feature(
            aligned
        )

        return feature

    def create_embedding(self, image):

        faces = self.detect_faces(image)

        if len(faces) == 0:
            raise ValueError(
                "No face detected in image."
            )

        # Use the largest detected face
        face = max(
            faces,
            key=lambda f: f[2] * f[3]
        )

        feature = self.extract_feature(
            image,
            face
        )

        return feature, face

    def compare(
        self,
        target_feature,
        query_feature
    ):

        score = self.recognizer.match(
            target_feature,
            query_feature,
            cv2.FaceRecognizerSF_FR_COSINE
        )

        return float(score)


face_engine = FaceEngine()