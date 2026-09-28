# SATARK AI

## AI-Based Intelligent Video Analytics Platform

SATARK AI is an intelligent video analytics platform designed for surveillance using existing CCTV infrastructure.

It combines computer vision, AI-based face analysis, OCR, GPS location and evidence capture into a centralized surveillance dashboard.

---

## 🚀 Project Status

- Backend: 🟢 Live
- AI Pipeline: 🟢 Implemented
- OCR: 🟢 Implemented
- GPS: 🟢 Implemented
- Target Watchlist: 🟢 Implemented
- Frontend: 🚧 Deployment in progress

---

## 🌐 Live Backend

[Open SATARK Backend](https://satark-xz7b.onrender.com)

## 📚 API Documentation

[Open SATARK API Docs](https://satark-xz7b.onrender.com/docs)

---

## ✨ Features

- 📹 Live camera integration
- 🤖 AI-based video analysis
- 👤 Authorized target watchlist
- 🔍 Face detection and feature comparison
- 🚘 OCR-based text detection
- 📍 GPS location tracking
- 🚨 Security alert generation
- 📸 Evidence and snapshot capture
- 📊 Centralized surveillance dashboard
- 🌐 REST API using FastAPI

---

## 🧠 AI & Computer Vision

SATARK uses:

- OpenCV
- YuNet
- SFace
- ONNX
- EasyOCR
- NumPy
- PyTorch

---

## 💻 Technology Stack

### Frontend

- React.js
- JavaScript
- HTML5
- CSS3
- Vite

### Backend

- Python
- FastAPI
- Uvicorn

### AI / Computer Vision

- OpenCV
- YuNet
- SFace
- ONNX
- EasyOCR
- PyTorch
- NumPy

### Browser APIs

- MediaDevices API
- Geolocation API

---

## 🏗️ Project Structure

```text
SATARK/
│
├── backend/
│   ├── app/
│   │   ├── api/
│   │   │   └── targets.py
│   │   │
│   │   ├── models/
│   │   │   └── ai/
│   │   │       ├── face_detection_yunet_2023mar.onnx
│   │   │       └── face_recognition_sface_2021dec.onnx
│   │   │
│   │   ├── services/
│   │   │   ├── face_engine.py
│   │   │   ├── ocr_engine.py
│   │   │   └── watchlist.py
│   │   │
│   │   └── main.py
│   │
│   ├── data/
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── main.jsx
│   │
│   ├── public/
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── .python-version