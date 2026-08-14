"""
Lightweight AI Object Detector using OpenCV DNN and YOLOv5n ONNX.

Runs 100% locally on CPU to recognize People, Vehicles, and Animals with
zero heavy external ML dependencies.
"""

import threading
import urllib.request
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

# Cache directory for models
MODEL_DIR = Path.home() / '.cache' / 'camview' / 'models'
MODEL_FILENAME = 'yolov5n.onnx'
MODEL_PATH = MODEL_DIR / MODEL_FILENAME
MODEL_URL = 'https://github.com/ultralytics/yolov5/releases/download/v7.0/yolov5n.onnx'

# Standard COCO 80 dataset class names
COCO_CLASSES = [
    'person', 'bicycle', 'car', 'motorcycle', 'airplane', 'bus', 'train', 'truck', 'boat',
    'traffic light', 'fire hydrant', 'stop sign', 'parking meter', 'bench', 'bird', 'cat',
    'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe', 'backpack',
    'umbrella', 'handbag', 'tie', 'suitcase', 'frisbee', 'skis', 'snowboard', 'sports ball',
    'kite', 'baseball bat', 'baseball glove', 'skateboard', 'surfboard', 'tennis racket',
    'bottle', 'wine glass', 'cup', 'fork', 'knife', 'spoon', 'bowl', 'banana', 'apple',
    'sandwich', 'orange', 'broccoli', 'carrot', 'hot dog', 'pizza', 'donut', 'cake',
    'chair', 'couch', 'potted plant', 'bed', 'dining table', 'toilet', 'tv', 'laptop',
    'mouse', 'remote', 'keyboard', 'cell phone', 'microwave', 'oven', 'toaster', 'sink',
    'refrigerator', 'book', 'clock', 'vase', 'scissors', 'teddy bear', 'hair drier',
    'toothbrush'
]

# Category mappings
PERSON_CLASSES = {'person'}
VEHICLE_CLASSES = {'bicycle', 'car', 'motorcycle', 'bus', 'truck'}
ANIMAL_CLASSES = {'bird', 'cat', 'dog', 'horse', 'sheep', 'cow', 'elephant', 'bear', 'zebra', 'giraffe'}

# UI colors for bounding boxes (BGR format for OpenCV)
CATEGORY_COLORS = {
    'person': (255, 200, 0),     # Vibrant Cyan / Sky Blue
    'vehicle': (0, 165, 255),    # Amber / Orange
    'animal': (50, 220, 50),     # Emerald Green
    'other': (180, 180, 180),    # Neutral Gray
}


@dataclass
class Detection:
    """Represents a single detected object in an image frame."""
    class_id: int
    class_name: str
    category: str
    confidence: float
    box: tuple[int, int, int, int]  # (x, y, w, h)


class AIDetector:
    """Thread-safe ONNX object detector powered by cv2.dnn."""

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._net = None
        self._is_loaded = False
        self._load_lock = threading.Lock()
        self._input_size = (640, 640)

    @classmethod
    def get_instance(cls) -> 'AIDetector':
        """Singleton instance accessor."""
        with cls._lock:
            if cls._instance is None:
                cls._instance = AIDetector()
            return cls._instance

    def is_ready(self) -> bool:
        """Check if model is loaded and ready for inference."""
        return self._is_loaded and self._net is not None

    def ensure_model_ready(self) -> bool:
        """Download and load the ONNX model if not already in memory."""
        with self._load_lock:
            if self._is_loaded and self._net is not None:
                return True

            try:
                MODEL_DIR.mkdir(parents=True, exist_ok=True)
                if not MODEL_PATH.exists() or MODEL_PATH.stat().st_size < 1_000_000:
                    print(f"CamView: Downloading AI Model (YOLOv5n ONNX, ~4MB) to {MODEL_PATH}...")
                    req = urllib.request.Request(
                        MODEL_URL,
                        headers={'User-Agent': 'Mozilla/5.0 CamView/1.0'}
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp, open(MODEL_PATH, 'wb') as out_file:
                        out_file.write(resp.read())
                    print("CamView: Model downloaded successfully.")

                net = cv2.dnn.readNetFromONNX(str(MODEL_PATH))
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)

                self._net = net
                self._is_loaded = True
                print("CamView: AIDetector loaded ONNX engine into CPU memory.")
                return True
            except Exception as e:
                print(f"CamView: AIDetector failed to initialize model: {e}")
                self._is_loaded = False
                self._net = None
                return False

    def detect(
        self,
        frame: np.ndarray,
        conf_threshold: float = 0.45,
        allowed_categories: set[str] | None = None,
    ) -> list[Detection]:
        """Perform object detection on an input BGR frame.

        Args:
            frame: Input OpenCV BGR image
            conf_threshold: Minimum confidence score (0.0 to 1.0)
            allowed_categories: Set of allowed categories ('person', 'vehicle', 'animal')
        """
        if not self.ensure_model_ready():
            return []

        orig_h, orig_w = frame.shape[:2]

        # Prepare YOLO input blob
        blob = cv2.dnn.blobFromImage(
            frame,
            scalefactor=1.0 / 255.0,
            size=self._input_size,
            swapRB=True,
            crop=False,
        )

        with self._load_lock:
            self._net.setInput(blob)
            outputs = self._net.forward()

        # Output shape: [1, 25200, 85] -> [x, y, w, h, obj_conf, class_probs...]
        predictions = np.squeeze(outputs[0])

        # Fast filter by objectness
        obj_mask = predictions[:, 4] >= conf_threshold
        preds = predictions[obj_mask]

        if len(preds) == 0:
            return []

        class_scores = preds[:, 5:]
        confidences = np.max(class_scores, axis=1) * preds[:, 4]
        class_ids = np.argmax(class_scores, axis=1)

        # Filter by final confidence
        score_mask = confidences >= conf_threshold
        preds = preds[score_mask]
        confidences = confidences[score_mask]
        class_ids = class_ids[score_mask]

        if len(preds) == 0:
            return []

        x_scale = orig_w / float(self._input_size[0])
        y_scale = orig_h / float(self._input_size[1])

        boxes = []
        for i in range(len(preds)):
            cx, cy, w, h = preds[i][:4]
            left = int((cx - w / 2.0) * x_scale)
            top = int((cy - h / 2.0) * y_scale)
            width = int(w * x_scale)
            height = int(h * y_scale)

            # Clamp coordinates to frame boundary
            left = max(0, min(left, orig_w - 1))
            top = max(0, min(top, orig_h - 1))
            width = max(1, min(width, orig_w - left))
            height = max(1, min(height, orig_h - top))

            boxes.append([left, top, width, height])

        # Non-Maximum Suppression
        indices = cv2.dnn.NMSBoxes(boxes, confidences.tolist(), conf_threshold, 0.45)
        detections: list[Detection] = []

        if len(indices) > 0:
            for idx in indices.flatten():
                cid = int(class_ids[idx])
                cname = COCO_CLASSES[cid] if cid < len(COCO_CLASSES) else f"class_{cid}"

                if cname in PERSON_CLASSES:
                    category = 'person'
                elif cname in VEHICLE_CLASSES:
                    category = 'vehicle'
                elif cname in ANIMAL_CLASSES:
                    category = 'animal'
                else:
                    category = 'other'

                if allowed_categories is None or category in allowed_categories:
                    detections.append(
                        Detection(
                            class_id=cid,
                            class_name=cname,
                            category=category,
                            confidence=float(confidences[idx]),
                            box=tuple(boxes[idx]),
                        )
                    )

        return detections

    def draw_detections(self, frame: np.ndarray, detections: list[Detection]) -> np.ndarray:
        """Render polished bounding boxes and category badges on the frame."""
        for det in detections:
            x, y, w, h = det.box
            color = CATEGORY_COLORS.get(det.category, (0, 255, 0))

            # Main bounding box
            cv2.rectangle(frame, (x, y), (x + w, y + h), color, 2)

            # Label badge
            label = f"{det.class_name.capitalize()} {int(det.confidence * 100)}%"
            font = cv2.FONT_HERSHEY_SIMPLEX
            font_scale = 0.45
            font_thickness = 1
            (text_w, text_h), baseline = cv2.getTextSize(label, font, font_scale, font_thickness)

            # Badge rectangle
            badge_y1 = max(0, y - text_h - 6)
            badge_y2 = y
            badge_x1 = x
            badge_x2 = min(frame.shape[1], x + text_w + 8)

            cv2.rectangle(frame, (badge_x1, badge_y1), (badge_x2, badge_y2), color, cv2.FILLED)
            # Crisp black text on bright badge
            cv2.putText(
                frame,
                label,
                (badge_x1 + 4, badge_y2 - 3),
                font,
                font_scale,
                (0, 0, 0),
                font_thickness,
                cv2.LINE_AA,
            )

        return frame
