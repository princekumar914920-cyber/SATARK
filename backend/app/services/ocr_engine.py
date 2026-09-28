import easyocr
import cv2


class OCREngine:

    def __init__(self):
        print("Loading EasyOCR...")

        self.reader = easyocr.Reader(
            ["en"],
            gpu=False
        )

        print("EasyOCR loaded successfully.")

    def read_text(self, image):

        if image is None:
            return []

        try:
            # -----------------------------------------
            # ORIGINAL IMAGE
            # -----------------------------------------

            results_original = self.reader.readtext(
                image,
                detail=1,
                paragraph=False
            )

            # -----------------------------------------
            # GRAYSCALE IMAGE
            # -----------------------------------------

            gray = cv2.cvtColor(
                image,
                cv2.COLOR_BGR2GRAY
            )

            results_gray = self.reader.readtext(
                gray,
                detail=1,
                paragraph=False
            )

            # -----------------------------------------
            # UPSCALED IMAGE
            # -----------------------------------------

            height, width = image.shape[:2]

            scale = 2

            upscaled = cv2.resize(
                image,
                (width * scale, height * scale),
                interpolation=cv2.INTER_CUBIC
            )

            results_upscaled = self.reader.readtext(
                upscaled,
                detail=1,
                paragraph=False
            )

            # -----------------------------------------
            # COMBINE RESULTS
            # -----------------------------------------

            all_results = (
                results_original
                + results_gray
                + results_upscaled
            )

            detected_text = []

            for result in all_results:

                if len(result) < 3:
                    continue

                box = result[0]
                text = str(result[1]).strip()
                confidence = float(result[2])

                if not text:
                    continue

                # Ignore extremely low-confidence noise
                if confidence < 0.20:
                    continue

                detected_text.append({
                    "text": text,
                    "confidence": round(
                        confidence,
                        4
                    ),
                    "box": box
                })

            # -----------------------------------------
            # REMOVE DUPLICATES
            # -----------------------------------------

            unique_results = {}

            for item in detected_text:

                key = item["text"].upper()

                if (
                    key not in unique_results
                    or item["confidence"]
                    > unique_results[key]["confidence"]
                ):
                    unique_results[key] = item

            return list(
                unique_results.values()
            )

        except Exception as error:

            print(
                "EasyOCR ERROR:",
                str(error)
            )

            return []


ocr_engine = OCREngine()