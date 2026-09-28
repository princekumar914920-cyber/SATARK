from pathlib import Path
from uuid import uuid4

import cv2
import numpy as np
from fastapi import APIRouter, File, UploadFile
from fastapi.responses import JSONResponse

from app.services.face_engine import face_engine


router = APIRouter(
    prefix="/api/targets",
    tags=["Target Watchlist"]
)

BASE_DIR = Path(__file__).resolve().parent.parent.parent

TARGET_DIR = BASE_DIR / "data" / "targets"
TARGET_DIR.mkdir(parents=True, exist_ok=True)


@router.post("/upload")
async def upload_target(file: UploadFile = File(...)):

    contents = await file.read()

    if not contents:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": "Empty image received."
            }
        )

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
                "message": "Invalid image."
            }
        )

    try:
        feature, face = face_engine.create_embedding(image)

    except ValueError as error:
        return JSONResponse(
            status_code=400,
            content={
                "success": False,
                "message": str(error)
            }
        )

    target_id = str(uuid4())

    image_path = TARGET_DIR / f"{target_id}.jpg"

    cv2.imwrite(
        str(image_path),
        image
    )

    feature_path = TARGET_DIR / f"{target_id}.npy"

    np.save(
        str(feature_path),
        feature
    )

    return {
        "success": True,
        "target_id": target_id,
        "message": "Target profile created successfully.",
        "face_detected": True,
        "face_box": {
            "x": int(face[0]),
            "y": int(face[1]),
            "width": int(face[2]),
            "height": int(face[3])
        }
    }
@router.get("/list")
def list_targets():
    targets = []

    for feature_file in TARGET_DIR.glob("*.npy"):
        target_id = feature_file.stem
        image_file = TARGET_DIR / f"{target_id}.jpg"

        targets.append({
            "target_id": target_id,
            "image": f"/api/targets/image/{target_id}",
            "status": "ACTIVE",
        })

    return {
        "success": True,
        "count": len(targets),
        "targets": targets,
    }


@router.get("/image/{target_id}")
def target_image(target_id: str):

    image_file = TARGET_DIR / f"{target_id}.jpg"

    if not image_file.exists():
        return JSONResponse(
            status_code=404,
            content={
                "success": False,
                "message": "Target image not found",
            },
        )

    return FileResponse(
        image_file,
        media_type="image/jpeg",
    )