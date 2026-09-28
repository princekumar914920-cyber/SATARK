from pathlib import Path
from datetime import datetime
import json
import time
import asyncio

import cv2
import numpy as np

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse

from app.api.targets import router as targets_router
from app.services.watchlist import analyze_frame
from app.services.ocr_engine import ocr_engine


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="SATARK AI",
    description="AI Based Intelligent Video Analytics Platform",
    version="1.0.0",
)

app.include_router(targets_router)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

DATA_DIR = BASE_DIR / "data"

SNAPSHOT_DIR = DATA_DIR / "snapshots"
MATCH_DIR = DATA_DIR / "matches"

SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
MATCH_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# FILES
# ============================================================

LATEST_FRAME = SNAPSHOT_DIR / "mobile_latest.jpg"

LOCATION_FILE = DATA_DIR / "mobile_location.json"

LATEST_MATCH = MATCH_DIR / "latest_match.json"

MATCH_SNAPSHOT = MATCH_DIR / "latest_match.jpg"

OCR_RESULT_FILE = DATA_DIR / "ocr_result.json"


# ============================================================
# CAMERA
# ============================================================

CAMERA_ID = "MOBILE-01"


# ============================================================
# PERFORMANCE SETTINGS
# ============================================================

# AI analysis minimum interval.
#
# Camera frames can arrive more frequently than AI processing.
# We do NOT want multiple AI jobs running simultaneously.

AI_INTERVAL_SECONDS = 1.5

# OCR is much heavier than normal frame handling.
# Run OCR only periodically.

OCR_INTERVAL_SECONDS = 5.0


# ============================================================
# BACKGROUND STATE
# ============================================================

last_ai_time = 0.0

last_ocr_time = 0.0

ai_running = False

ocr_running = False

background_lock = asyncio.Lock()


# ============================================================
# CACHED RESULTS
# ============================================================

latest_ai_result = {
    "status": "WAITING",
    "camera": CAMERA_ID,
    "faces_detected": 0,
    "candidate_target_id": None,
    "similarity_score": 0,
    "similarity_percent": 0,
    "human_review_required": False,
    "location": None,
    "timestamp": None,
}


latest_ocr_result = {
    "status": "WAITING",
    "camera": CAMERA_ID,
    "text_detected": 0,
    "results": [],
    "timestamp": None,
}


# ============================================================
# ROOT
# ============================================================

@app.get("/")
def root():

    return {
        "project": "SATARK AI",
        "status": "online",
        "message": "SATARK AI backend is running",
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/api/health")
def health():

    return {
        "status": "healthy",
        "ai_engine": "ready",
        "mobile_camera": "ready",
        "watchlist_engine": "ready",
        "ocr_engine": "ready",
        "gps": "ready",
    }


# ============================================================
# MOBILE CAMERA STATUS
# ============================================================

@app.get("/api/mobile/status")
def mobile_status():

    if not LATEST_FRAME.exists():

        return {
            "camera": CAMERA_ID,
            "status": "WAITING",
            "last_frame": None,
        }

    modified_time = datetime.fromtimestamp(
        LATEST_FRAME.stat().st_mtime
    )

    return {
        "camera": CAMERA_ID,
        "status": "ONLINE",
        "last_frame": modified_time.isoformat(),
    }


# ============================================================
# BACKGROUND AI ANALYSIS
# ============================================================

async def process_ai_background(image):

    global ai_running
    global last_ai_time
    global latest_ai_result

    # --------------------------------------------------------
    # Prevent multiple AI jobs
    # --------------------------------------------------------

    if ai_running:
        return

    current_time = time.time()

    if (
        current_time - last_ai_time
        < AI_INTERVAL_SECONDS
    ):
        return

    ai_running = True
    last_ai_time = current_time

    try:

        # ----------------------------------------------------
        # Run CPU-heavy AI outside async event loop
        # ----------------------------------------------------

        result = await asyncio.to_thread(
            analyze_frame,
            image.copy()
        )

        if result is None:

            result = {
                "status": "ANALYSIS_ERROR",
                "camera": CAMERA_ID,
                "faces_detected": 0,
                "similarity_score": 0,
                "candidate_target_id": None,
                "human_review_required": False,
                "timestamp": datetime.now().isoformat(),
            }

        latest_ai_result = result

    except Exception as error:

        print(
            "AI BACKGROUND ERROR:",
            str(error)
        )

        latest_ai_result = {
            "status": "ANALYSIS_ERROR",
            "camera": CAMERA_ID,
            "faces_detected": 0,
            "similarity_score": 0,
            "candidate_target_id": None,
            "human_review_required": False,
            "message": str(error),
            "timestamp": datetime.now().isoformat(),
        }

    finally:

        ai_running = False


# ============================================================
# BACKGROUND OCR
# ============================================================

async def process_ocr_background(image):

    global ocr_running
    global last_ocr_time
    global latest_ocr_result

    # --------------------------------------------------------
    # Prevent multiple OCR jobs
    # --------------------------------------------------------

    if ocr_running:
        return

    current_time = time.time()

    if (
        current_time - last_ocr_time
        < OCR_INTERVAL_SECONDS
    ):
        return

    ocr_running = True
    last_ocr_time = current_time

    try:

        # ----------------------------------------------------
        # OCR is CPU-heavy
        # Run outside event loop
        # ----------------------------------------------------

        results = await asyncio.to_thread(
            ocr_engine.read_text,
            image.copy()
        )

        latest_ocr_result = {

            "status": (
                "TEXT_DETECTED"
                if len(results) > 0
                else "NO_TEXT"
            ),

            "camera": CAMERA_ID,

            "text_detected": len(
                results
            ),

            "results": results,

            "timestamp":
                datetime.now().isoformat(),
        }


        # ----------------------------------------------------
        # Save OCR result
        # ----------------------------------------------------

        try:

            with open(
                OCR_RESULT_FILE,
                "w",
                encoding="utf-8"
            ) as file:

                json.dump(
                    latest_ocr_result,
                    file,
                    indent=2,
                    ensure_ascii=False
                )

        except Exception as error:

            print(
                "OCR RESULT SAVE ERROR:",
                str(error)
            )


    except Exception as error:

        print(
            "OCR BACKGROUND ERROR:",
            str(error)
        )

        latest_ocr_result = {

            "status": "OCR_ERROR",

            "camera": CAMERA_ID,

            "text_detected": 0,

            "results": [],

            "message": str(error),

            "timestamp":
                datetime.now().isoformat(),
        }

    finally:

        ocr_running = False


# ============================================================
# RECEIVE MOBILE CAMERA FRAME
#
# IMPORTANT:
#
# This endpoint does NOT wait for AI.
#
# It:
#
# 1. Receives frame
# 2. Saves frame
# 3. Starts background AI/OCR
# 4. Immediately returns
#
# ============================================================

@app.post("/api/mobile/frame")
async def receive_mobile_frame(
    file: UploadFile = File(...)
):

    try:

        # ----------------------------------------------------
        # READ FRAME
        # ----------------------------------------------------

        contents = await file.read()

        if not contents:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Empty frame received",
                },
            )


        # ----------------------------------------------------
        # DECODE IMAGE
        # ----------------------------------------------------

        image_array = np.frombuffer(
            contents,
            dtype=np.uint8
        )

        image = cv2.imdecode(
            image_array,
            cv2.IMREAD_COLOR
        )

        if image is None:

            return JSONResponse(
                status_code=400,
                content={
                    "success": False,
                    "message":
                        "Invalid image frame",
                },
            )


        # ----------------------------------------------------
        # SAVE LATEST FRAME
        # ----------------------------------------------------

        # JPEG is already compressed from frontend.
        #
        # Save directly so the dashboard can immediately
        # retrieve the latest frame.

        with open(
            LATEST_FRAME,
            "wb"
        ) as output_file:

            output_file.write(contents)


        # ----------------------------------------------------
        # START BACKGROUND AI
        # ----------------------------------------------------

        asyncio.create_task(
            process_ai_background(
                image
            )
        )


        # ----------------------------------------------------
        # START BACKGROUND OCR
        # ----------------------------------------------------

        asyncio.create_task(
            process_ocr_background(
                image
            )
        )


        # ----------------------------------------------------
        # IMMEDIATE RESPONSE
        # ----------------------------------------------------

        return {

            "success": True,

            "camera": CAMERA_ID,

            "message":
                "Frame received",

            "timestamp":
                datetime.now().isoformat(),

            "ai_processing":
                ai_running,

            "ocr_processing":
                ocr_running,
        }


    except Exception as error:

        print(
            "FRAME ERROR:",
            str(error)
        )

        return JSONResponse(
            status_code=500,
            content={
                "success": False,
                "message": str(error),
            },
        )


# ============================================================
# MOBILE GPS LOCATION
# ============================================================

@app.post("/api/mobile/location")
async def receive_mobile_location(
    data: dict
):

    try:

        latitude = float(
            data.get(
                "latitude"
            )
        )

        longitude = float(
            data.get(
                "longitude"
            )
        )

        accuracy = float(
            data.get(
                "accuracy",
                0
            )
        )


        location = {

            "latitude":
                latitude,

            "longitude":
                longitude,

            "accuracy_m":
                accuracy,

            "updated_at":
                datetime.now().isoformat(),

            "camera":
                CAMERA_ID,
        }


        # ----------------------------------------------------
        # SAVE LOCATION
        # ----------------------------------------------------

        with open(
            LOCATION_FILE,
            "w",
            encoding="utf-8"
        ) as file:

            json.dump(
                location,
                file,
                indent=2
            )


        return {

            "success": True,

            "location":
                location,

        }


    except Exception as error:

        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(error),
            },
        )


# ============================================================
# GET MOBILE GPS LOCATION
# ============================================================

@app.get("/api/mobile/location")
def get_mobile_location():

    if not LOCATION_FILE.exists():

        return {

            "available":
                False,

            "location":
                None,

        }


    try:

        with open(
            LOCATION_FILE,
            "r",
            encoding="utf-8"
        ) as file:

            location = json.load(file)


        return {

            "available":
                True,

            "location":
                location,

        }


    except Exception as error:

        return {

            "available":
                False,

            "location":
                None,

            "message":
                str(error),

        }


# ============================================================
# LATEST MOBILE FRAME
# ============================================================

@app.get("/api/mobile/latest")
def latest_mobile_frame():

    if not LATEST_FRAME.exists():

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message":
                    "No mobile camera frame available",
            },
        )


    return FileResponse(

        LATEST_FRAME,

        media_type="image/jpeg",

        headers={

            "Cache-Control":
                "no-cache, no-store, must-revalidate",

            "Pragma":
                "no-cache",

            "Expires":
                "0",
        },
    )


# ============================================================
# LATEST AI ANALYSIS
# ============================================================

@app.get("/api/ai/latest")
def latest_ai_analysis():

    return latest_ai_result


# ============================================================
# LATEST AI EVIDENCE
# ============================================================

@app.get("/api/ai/evidence")
def latest_ai_evidence():

    if not MATCH_SNAPSHOT.exists():

        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message":
                    "No AI evidence available",
            },
        )


    return FileResponse(

        MATCH_SNAPSHOT,

        media_type="image/jpeg",

        headers={

            "Cache-Control":
                "no-cache, no-store, must-revalidate",

            "Pragma":
                "no-cache",

            "Expires":
                "0",
        },
    )


# ============================================================
# LATEST OCR RESULT
# ============================================================

@app.get("/api/ai/ocr")
def get_latest_ocr_result():

    # --------------------------------------------------------
    # Return memory cache first
    # --------------------------------------------------------

    return latest_ocr_result


# ============================================================
# APPLICATION STARTUP
# ============================================================

@app.on_event("startup")
async def startup_event():

    print("")
    print("=" * 60)
    print("SATARK AI BACKEND")
    print("=" * 60)
    print("Camera       :", CAMERA_ID)
    print("AI interval  :", AI_INTERVAL_SECONDS, "seconds")
    print("OCR interval :", OCR_INTERVAL_SECONDS, "seconds")
    print("=" * 60)
    print("")