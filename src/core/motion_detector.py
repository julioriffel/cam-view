"""
High-Performance Motion Detection Engine for CamView.

Features:
- Downscaled analysis (480p) to minimize CPU usage by up to 70-80%.
- KNN Background Subtraction with active shadow suppression.
- Morphological noise filtering (rain/bugs/speckles removal).
- Temporal persistence debounce to avoid single-frame glitch triggers.
- Automatic upscaling of bounding boxes to match original video resolution.
- Optional Region of Interest (ROI) polygon mask support.
"""

from typing import Optional, List, Tuple
import cv2
import numpy as np


class MotionDetector:
    """Modular, high-performance motion detector with downscaling and shadow removal."""

    def __init__(
        self,
        algorithm: str = 'knn',
        target_width: int = 480,
        min_area: int = 1500,
        persistence: int = 5,
        filter_enabled: bool = True,
        history: int = 400,
    ):
        self.algorithm_name = algorithm.lower()
        self.target_width = target_width
        self.min_area = min_area
        self.persistence = persistence
        self.filter_enabled = filter_enabled
        self.history = history

        self._kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
        self._bg_subtractor = self._create_subtractor()
        self._learning_frames = 25
        self._consecutive_motion_frames = 0
        self._roi_mask: Optional[np.ndarray] = None
        self._cached_roi_size: Optional[Tuple[int, int]] = None
        self._small_roi_mask: Optional[np.ndarray] = None

    def _create_subtractor(self):
        """Create OpenCV Background Subtractor based on algorithm preference."""
        if self.algorithm_name == 'mog2':
            return cv2.createBackgroundSubtractorMOG2(
                history=self.history,
                varThreshold=40,
                detectShadows=True,
            )
        # Default: KNN (superior shadow handling and dynamic background adaptation)
        return cv2.createBackgroundSubtractorKNN(
            history=self.history,
            dist2Threshold=400.0,
            detectShadows=True,
        )

    def update_params(
        self,
        algorithm: Optional[str] = None,
        min_area: Optional[int] = None,
        persistence: Optional[int] = None,
        filter_enabled: Optional[bool] = None,
        target_width: Optional[int] = None,
    ):
        """Dynamically update detector parameters at runtime."""
        if algorithm is not None and algorithm.lower() != self.algorithm_name:
            self.algorithm_name = algorithm.lower()
            self._bg_subtractor = self._create_subtractor()
            self._learning_frames = 25

        if min_area is not None:
            self.min_area = max(50, min_area)

        if persistence is not None:
            self.persistence = max(1, persistence)

        if filter_enabled is not None:
            self.filter_enabled = filter_enabled

        if target_width is not None and target_width > 0:
            self.target_width = target_width

    def set_roi_mask(self, mask: Optional[np.ndarray]):
        """Set a binary ROI mask (255 for active zones, 0 for excluded zones)."""
        self._roi_mask = mask
        self._cached_roi_size = None
        self._small_roi_mask = None

    def reset(self):
        """Reset background model and persistence tracking state."""
        self._bg_subtractor = self._create_subtractor()
        self._learning_frames = 25
        self._consecutive_motion_frames = 0

    def process_frame(
        self, frame: np.ndarray
    ) -> Tuple[bool, bool, List[Tuple[int, int, int, int]]]:
        """
        Process a single BGR frame.

        Returns:
            (has_raw_motion: bool, is_persistent_motion: bool, bounding_boxes: list[(x, y, w, h)])
        """
        if frame is None or frame.size == 0:
            return False, False, []

        orig_h, orig_w = frame.shape[:2]

        # Calculate downscaling ratio
        if orig_w > self.target_width:
            scale = self.target_width / float(orig_w)
            target_h = max(1, int(orig_h * scale))
            small_frame = cv2.resize(
                frame, (self.target_width, target_h), interpolation=cv2.INTER_LINEAR
            )
        else:
            scale = 1.0
            small_frame = frame

        # Apply background subtraction
        fg_mask = self._bg_subtractor.apply(small_frame)

        if self._learning_frames > 0:
            self._learning_frames -= 1
            return False, False, []

        # Shadow suppression (KNN/MOG2 marks shadows as gray ~127; foreground is 255)
        # Threshold at 200 strictly keeps only solid moving foreground objects
        _, fg_mask = cv2.threshold(fg_mask, 200, 255, cv2.THRESH_BINARY)

        # Apply ROI mask if present
        if self._roi_mask is not None:
            mask_size = (small_frame.shape[1], small_frame.shape[0])
            if self._cached_roi_size != mask_size:
                self._small_roi_mask = cv2.resize(
                    self._roi_mask, mask_size, interpolation=cv2.INTER_NEAREST
                )
                self._cached_roi_size = mask_size
            fg_mask = cv2.bitwise_and(fg_mask, self._small_roi_mask)

        # Morphological noise filter (removes insects, rain streaks, sensor noise)
        if self.filter_enabled:
            fg_mask = cv2.morphologyEx(fg_mask, cv2.MORPH_OPEN, self._kernel)

        # Extract contours
        contours, _ = cv2.findContours(
            fg_mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE
        )

        # Scale min_area proportionally to downscaled resolution
        scaled_min_area = self.min_area * (scale * scale)

        valid_boxes: List[Tuple[int, int, int, int]] = []
        inv_scale = 1.0 / scale

        for cnt in contours:
            if cv2.contourArea(cnt) >= scaled_min_area:
                x, y, w, h = cv2.boundingRect(cnt)
                # Map bounding box back to original frame coordinate space
                orig_x = max(0, min(orig_w - 1, int(x * inv_scale)))
                orig_y = max(0, min(orig_h - 1, int(y * inv_scale)))
                orig_box_w = min(orig_w - orig_x, int(w * inv_scale))
                orig_box_h = min(orig_h - orig_y, int(h * inv_scale))
                valid_boxes.append((orig_x, orig_y, orig_box_w, orig_box_h))

        has_raw_motion = len(valid_boxes) > 0

        if has_raw_motion:
            self._consecutive_motion_frames += 1
        else:
            self._consecutive_motion_frames = 0

        is_persistent = self._consecutive_motion_frames >= self.persistence

        return has_raw_motion, is_persistent, valid_boxes
