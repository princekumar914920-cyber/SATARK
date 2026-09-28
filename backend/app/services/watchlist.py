from pathlib import Path
from datetime import datetime
import json
import time

import cv2
import numpy as np

from app.services.face_engine import face_engine


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"

TARGET_DIR = DATA_DIR / "targets"
MATCH_DIR = DATA_DIR / "matches"
SNAPSHOT_DIR = DATA_DIR / "snapshots"

TARGET_DIR.mkdir(parents=True, exist_ok=True)
MATCH_DIR.mkdir(parents=True, exist_ok=True)
SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FILES
# ============================================================

LAST_RESULT_FILE = MATCH_DIR / "latest_match.json"

MATCH_SNAPSHOT = MATCH_DIR / "latest_match.jpg"

HISTORY_FILE = MATCH_DIR / "detection_history.json"

LOCATION_FILE = DATA_DIR / "mobile_location.json"


# ============================================================
# CAMERA
# ============================================================

CAMERA_ID = "MOBILE-01"


# ============================================================
# AI SETTINGS
# ============================================================

# Demo candidate-alert threshold.
# This is NOT an identity decision.
MATCH_THRESHOLD = 0.45


# ============================================================
# COOLDOWNS
# ============================================================

# Evidence snapshot cooldown
ALERT_COOLDOWN_SECONDS = 5

# History entry cooldown
HISTORY_COOLDOWN_SECONDS = 3


_last_alert_time = 0
_last_history_time = 0

# Keep target embeddings in memory instead of reading every .npy
# file from disk for every camera frame.
TARGET_CACHE_SECONDS = 5.0
_targets_cache = []
_targets_cache_time = 0.0


# ============================================================
# LOAD GPS LOCATION
# ============================================================

def load_location():

    if not LOCATION_FILE.exists():
        return None

    try:

        with open(
            LOCATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            location = json.load(file)

        return {
            "latitude": location.get("latitude"),
            "longitude": location.get("longitude"),
            "accuracy_m": location.get("accuracy_m"),
            "camera": location.get(
                "camera",
                CAMERA_ID
            ),
            "updated_at": location.get(
                "updated_at"
            ),
        }

    except Exception:
        return None


# ============================================================
# LOAD WATCHLIST TARGETS
# ============================================================

def load_targets():

    global _targets_cache
    global _targets_cache_time

    current_time = time.monotonic()

    # Return cached embeddings during normal live processing.
    if (
        _targets_cache
        and current_time - _targets_cache_time
        < TARGET_CACHE_SECONDS
    ):
        return _targets_cache

    targets = []

    for feature_file in TARGET_DIR.glob("*.npy"):

        try:

            feature = np.load(
                str(feature_file)
            )

            target_id = feature_file.stem

            image_file = TARGET_DIR / f"{target_id}.jpg"

            targets.append({
                "target_id": target_id,
                "feature": feature,
                "image_path": str(image_file),
            })

        except Exception:
            continue

    _targets_cache = targets
    _targets_cache_time = current_time

    return _targets_cache


# ============================================================
# ANALYZE FRAME
# ============================================================

def analyze_frame(image):

    global _last_alert_time
    global _last_history_time

    # --------------------------------------------------------
    # INVALID IMAGE
    # --------------------------------------------------------

    if image is None:

        result = {
            "status": "ERROR",
            "camera": CAMERA_ID,
            "message": "Invalid frame",
            "timestamp": datetime.now().isoformat(),
        }

        _save_result(result)

        return result


    # --------------------------------------------------------
    # LOAD TARGETS
    # --------------------------------------------------------

    targets = load_targets()

    if not targets:

        result = {
            "status": "NO_TARGETS",
            "camera": CAMERA_ID,
            "message": "No authorized watchlist profiles available",
            "faces_detected": 0,
            "similarity_score": 0.0,
            "human_review_required": False,
            "timestamp": datetime.now().isoformat(),
        }

        _add_location(result)
        _save_result(result)

        return result


    # --------------------------------------------------------
    # FACE DETECTION
    # --------------------------------------------------------

    faces = face_engine.detect_faces(image)


    # --------------------------------------------------------
    # NO FACE
    # --------------------------------------------------------

    if len(faces) == 0:

        result = {
            "status": "NO_FACE",
            "camera": CAMERA_ID,
            "message": "No face detected",
            "faces_detected": 0,
            "similarity_score": 0.0,
            "candidate_target_id": None,
            "human_review_required": False,
            "timestamp": datetime.now().isoformat(),
        }

        _add_location(result)

        _save_result(result)

        _save_history_if_needed(result)

        return result


    # --------------------------------------------------------
    # FIND BEST MATCH
    # --------------------------------------------------------

    best_match = None

    for face in faces:

        try:

            query_feature = face_engine.extract_feature(
                image,
                face
            )

        except Exception:

            continue


        for target in targets:

            try:

                score = face_engine.compare(
                    target["feature"],
                    query_feature
                )

            except Exception:

                continue


            if (
                best_match is None
                or score > best_match["score"]
            ):

                best_match = {
                    "target_id": target["target_id"],
                    "score": score,
                    "face": face,
                }


    # --------------------------------------------------------
    # ANALYSIS ERROR
    # --------------------------------------------------------

    if best_match is None:

        result = {
            "status": "ANALYSIS_ERROR",
            "camera": CAMERA_ID,
            "faces_detected": len(faces),
            "similarity_score": 0.0,
            "candidate_target_id": None,
            "human_review_required": False,
            "timestamp": datetime.now().isoformat(),
        }

        _add_location(result)

        _save_result(result)

        return result


    # --------------------------------------------------------
    # SCORE
    # --------------------------------------------------------

    score = best_match["score"]

    is_candidate = score >= MATCH_THRESHOLD


    # --------------------------------------------------------
    # RESULT
    # --------------------------------------------------------

    result = {

        "status": (
            "POSSIBLE_MATCH"
            if is_candidate
            else "NO_MATCH"
        ),

        "camera": CAMERA_ID,

        "faces_detected": len(faces),

        "candidate_target_id": (
            best_match["target_id"]
            if is_candidate
            else None
        ),

        "similarity_score": round(
            float(score),
            4
        ),

        "similarity_percent": round(
            float(score) * 100,
            2
        ),

        "human_review_required": is_candidate,

        "timestamp": datetime.now().isoformat(),
    }


    # --------------------------------------------------------
    # ADD GPS
    # --------------------------------------------------------

    _add_location(result)


    # --------------------------------------------------------
    # SAVE EVIDENCE
    # --------------------------------------------------------

    current_time = time.time()


    if is_candidate and (
        current_time - _last_alert_time
        >= ALERT_COOLDOWN_SECONDS
    ):

        face = best_match["face"]

        x, y, w, h = [
            int(value)
            for value in face[:4]
        ]


        annotated = image.copy()


        # Face bounding box

        cv2.rectangle(
            annotated,
            (x, y),
            (x + w, y + h),
            (0, 255, 255),
            2
        )


        # Alert text

        cv2.putText(
            annotated,
            "POSSIBLE WATCHLIST MATCH - REVIEW",
            (
                x,
                max(y - 10, 20)
            ),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.6,
            (0, 255, 255),
            2
        )


        # Camera label

        cv2.putText(
            annotated,
            f"CAMERA: {CAMERA_ID}",
            (20, 30),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )


        # Similarity label

        cv2.putText(
            annotated,
            f"SIMILARITY: {score * 100:.2f}%",
            (20, 60),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.7,
            (0, 255, 255),
            2
        )


        # Save snapshot

        cv2.imwrite(
            str(MATCH_SNAPSHOT),
            annotated
        )


        result["evidence_snapshot"] = str(
            MATCH_SNAPSHOT
        )


        _last_alert_time = current_time


    # --------------------------------------------------------
    # SAVE LATEST RESULT
    # --------------------------------------------------------

    _save_result(result)


    # --------------------------------------------------------
    # SAVE HISTORY
    # --------------------------------------------------------

    _save_history_if_needed(result)


    return result


# ============================================================
# ADD LOCATION TO RESULT
# ============================================================

def _add_location(result):

    location = load_location()

    if location is None:

        result["location"] = None

        return


    result["location"] = {

        "latitude": location.get(
            "latitude"
        ),

        "longitude": location.get(
            "longitude"
        ),

        "accuracy_m": location.get(
            "accuracy_m"
        ),

        "camera": location.get(
            "camera",
            CAMERA_ID
        ),

        "updated_at": location.get(
            "updated_at"
        ),
    }


# ============================================================
# SAVE LATEST RESULT
# ============================================================

def _save_result(result):

    try:

        with open(
            LAST_RESULT_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                result,
                file,
                indent=2
            )

    except Exception as error:

        print(
            "Could not save latest result:",
            error
        )


# ============================================================
# SAVE DETECTION HISTORY
# ============================================================

def _save_history_if_needed(result):

    global _last_history_time

    current_time = time.time()


    # Avoid creating hundreds of history
    # entries every second.

    if (
        current_time - _last_history_time
        < HISTORY_COOLDOWN_SECONDS
    ):

        return


    try:

        history = []


        # Load existing history

        if HISTORY_FILE.exists():

            try:

                with open(
                    HISTORY_FILE,
                    "r",
                    encoding="utf-8"
                ) as file:

                    history = json.load(file)

                    if not isinstance(
                        history,
                        list
                    ):

                        history = []

            except Exception:

                history = []


        # Create compact history record

        history_item = {

            "timestamp": result.get(
                "timestamp"
            ),

            "camera": result.get(
                "camera",
                CAMERA_ID
            ),

            "status": result.get(
                "status"
            ),

            "faces_detected": result.get(
                "faces_detected",
                0
            ),

            "similarity_percent": result.get(
                "similarity_percent",
                0
            ),

            "candidate_target_id": result.get(
                "candidate_target_id"
            ),

            "human_review_required": result.get(
                "human_review_required",
                False
            ),

            "location": result.get(
                "location"
            ),

            "evidence_snapshot": result.get(
                "evidence_snapshot"
            ),
        }


        history.append(
            history_item
        )


        # Keep only latest 100 records

        history = history[-100:]


        # Save

        with open(
            HISTORY_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                history,
                file,
                indent=2
            )


        _last_history_time = current_time


    except Exception as error:

        print(
            "Could not save detection history:",
            error
        )