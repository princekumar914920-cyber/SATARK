import cv2


class OCREngine:

    def __init__(self):
        # EasyOCR ko startup par load nahi karna.
        # Isse Render ke limited RAM me startup memory kam rahegi.
        self.reader = None

    def _get_reader(self):
        """
        EasyOCR ko sirf tab load karta hai jab OCR actually use hota hai.
        """

        if self.reader is None:

            print("Loading EasyOCR...")

            # Lazy import:
            # EasyOCR + PyTorch server startup par load nahi honge.
            import easyocr

            self.reader = easyocr.Reader(
                ["en"],
                gpu=False,
                verbose=False
            )

            print("EasyOCR loaded successfully.")

        return self.reader

    def read_text(self, image):

        if image is None:
            return []

        try:

            # -----------------------------------------
            # GET EASY OCR READER
            # -----------------------------------------

            reader = self._get_reader()

            # -----------------------------------------
            # ORIGINAL IMAGE
            # -----------------------------------------

            results_original = reader.readtext(
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

            results_gray = reader.readtext(
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

            results_upscaled = reader.readtext(
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


# -----------------------------------------
# OCR ENGINE INSTANCE
# -----------------------------------------
#
# Important:
# OCREngine object banega,
# lekin EasyOCR Reader abhi load nahi hoga.
#
# EasyOCR tab load hoga jab read_text()
# actually call hoga.
# -----------------------------------------

ocr_engine = OCREngine()