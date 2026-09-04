"""
Camera & Vision Control Module for JARVIS.
Handles webcam capture, screenshot analysis, OCR, object detection.
Requires: opencv-python, Pillow, pytesseract (optional)
"""
import os
import time
import json
from pathlib import Path

_DATA_DIR = Path(__file__).resolve().parent.parent / ".jarvis"
_DATA_DIR.mkdir(exist_ok=True)

def handle(params=None):
    params = params or {}
    action = params.get("action", "capture")
    
    if action == "capture":
        return _capture_photo(params)
    elif action == "start_video":
        return _start_video_stream(params)
    elif action == "stop_video":
        return _stop_video_stream()
    elif action == "list_cameras":
        return _list_cameras()
    elif action == "screenshot":
        return _take_screenshot()
    elif action == "ocr":
        return _ocr_image(params)
    elif action == "detect_faces":
        return _detect_faces(params)
    elif action == "status":
        return _camera_status()
    else:
        return f"Camera: capture|start_video|stop_video|list_cameras|screenshot|ocr|detect_faces|status"

def _capture_photo(params):
    try:
        import cv2
        idx = params.get("camera_index", _get_default_camera())
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            return f"Camera {idx} not available"
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Failed to capture frame"
        path = str(_DATA_DIR / f"photo_{int(time.time())}.jpg")
        cv2.imwrite(path, frame)
        return f"Photo saved: {path}"
    except ImportError:
        return "opencv-python not installed. Run: pip install opencv-python"

def _take_screenshot():
    try:
        from PIL import ImageGrab
        img = ImageGrab.grab()
        path = str(_DATA_DIR / f"screenshot_{int(time.time())}.png")
        img.save(path)
        return f"Screenshot saved: {path}"
    except Exception as e:
        return f"Screenshot error: {e}"

def _list_cameras():
    try:
        import cv2
        available = []
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                ret, frame = cap.read()
                if ret:
                    w = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                    h = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                    available.append({"index": i, "resolution": f"{w}x{h}"})
                cap.release()
        return json.dumps(available) if available else "No cameras found"
    except ImportError:
        return "opencv-python not installed"

def _ocr_image(params):
    try:
        import pytesseract
        from PIL import Image
        path = params.get("path", "")
        if not path:
            return "No image path provided"
        img = Image.open(path)
        text = pytesseract.image_to_string(img)
        return f"OCR result:\n{text[:2000]}"
    except ImportError:
        return "pytesseract not installed. Run: pip install pytesseract"
    except Exception as e:
        return f"OCR error: {e}"

def _detect_faces(params):
    try:
        import cv2
        cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        face_cascade = cv2.CascadeClassifier(cascade_path)
        idx = params.get("camera_index", _get_default_camera())
        cap = cv2.VideoCapture(idx)
        if not cap.isOpened():
            return "Camera not available"
        ret, frame = cap.read()
        cap.release()
        if not ret:
            return "Failed to capture"
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, 1.3, 5)
        return f"Detected {len(faces)} face(s)"
    except ImportError:
        return "opencv-python not installed"
    except Exception as e:
        return f"Face detection error: {e}"

def _start_video_stream(params):
    return "Video streaming requires a GUI window. Use capture action instead."

def _stop_video_stream():
    return "Video stream stopped."

def _camera_status():
    try:
        import cv2
        cameras = []
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cameras.append(i)
                cap.release()
        return f"Available cameras: {cameras}" if cameras else "No cameras detected"
    except ImportError:
        return "opencv-python not installed"

def _get_default_camera():
    try:
        import cv2
        for i in range(6):
            cap = cv2.VideoCapture(i)
            if cap.isOpened():
                cap.release()
                return i
    except Exception:
        pass
    return 0
