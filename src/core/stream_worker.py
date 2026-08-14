"""
Background RTSP stream worker.

Runs on a dedicated QThread, continuously reads frames from an RTSP source,
converts them to QPixmap, and emits Qt signals for the UI to consume.
Includes automatic reconnection with exponential back-off.
"""

import time
from datetime import datetime
from pathlib import Path

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from src.core.connection import DVRConfig
from src.core.ai_detector import AIDetector


class StreamWorker(QThread):
    """Background thread to process RTSP stream via OpenCV."""

    frame_ready = Signal(QPixmap)
    fps_updated = Signal(float)
    status_changed = Signal(str)
    tracking_status_changed = Signal(bool)

    TARGET_FPS = 20.0
    MAX_RETRIES = 5

    def __init__(self, url: str, channel: int, config: DVRConfig, parent=None):
        super().__init__(parent)
        self.rtsp_url = url
        self.channel = channel
        self.save_folder = config.save_folder
        self._tracking_enabled = False
        
        # Motion tracking parameters
        self._filter_enabled = config.tracking_filter_enabled
        self._min_area = config.tracking_min_area
        self._persistence = config.tracking_persistence
        self._snapshot_on_motion = config.snapshot_on_motion
        self._snapshot_interval = float(config.snapshot_interval)

        # AI Smart Vision parameters
        self._ai_enabled = config.ai_enabled
        self._ai_confidence = float(config.ai_confidence_threshold)
        self._ai_detect_person = config.ai_detect_person
        self._ai_detect_vehicles = config.ai_detect_vehicles
        self._ai_detect_animals = config.ai_detect_animals
        self._ai_filter_snapshots = config.ai_filter_snapshots
        
        self._running = False
        self._mutex = QMutex()
        self._last_snapshot_time = 0.0

    def set_tracking(self, enabled: bool):
        """Enable or disable motion tracking overlays and snapshots."""
        with QMutexLocker(self._mutex):
            self._tracking_enabled = enabled
        self.tracking_status_changed.emit(enabled)
        
    def update_tracking_params(
        self,
        filter_enabled: bool,
        min_area: int,
        persistence: int,
        snapshot_on_motion: bool = True,
        snapshot_interval: float = 2.0,
        ai_enabled: bool = False,
        ai_confidence: float = 0.45,
        ai_detect_person: bool = True,
        ai_detect_vehicles: bool = True,
        ai_detect_animals: bool = False,
        ai_filter_snapshots: bool = True,
    ):
        """Dynamically update tracking sensitivity, snapshot, and AI parameters."""
        with QMutexLocker(self._mutex):
            self._filter_enabled = filter_enabled
            self._min_area = min_area
            self._persistence = persistence
            self._snapshot_on_motion = snapshot_on_motion
            self._snapshot_interval = float(snapshot_interval)
            self._ai_enabled = ai_enabled
            self._ai_confidence = float(ai_confidence)
            self._ai_detect_person = ai_detect_person
            self._ai_detect_vehicles = ai_detect_vehicles
            self._ai_detect_animals = ai_detect_animals
            self._ai_filter_snapshots = ai_filter_snapshots

    def is_tracking(self) -> bool:
        with QMutexLocker(self._mutex):
            return self._tracking_enabled

    def run(self):
        self._running = True
        retry_count = 0

        while self._running:
            self.status_changed.emit('connecting')
            cap = cv2.VideoCapture(self.rtsp_url, cv2.CAP_FFMPEG)
            cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
            cap.set(cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 5000)
            cap.set(cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000)

            if not cap.isOpened():
                retry_count += 1
                if retry_count > self.MAX_RETRIES:
                    self.status_changed.emit('error')
                    break
                self.status_changed.emit('reconnecting')
                wait_time = min(2 ** retry_count, 30)
                self._interruptible_sleep(wait_time)
                continue

            # Connected successfully
            retry_count = 0
            self.status_changed.emit('live')

            frame_count = 0
            fps_start_time = time.monotonic()
            frame_interval = 1.0 / self.TARGET_FPS
            
            # Motion detection setup
            bg_subtractor = cv2.createBackgroundSubtractorMOG2(history=500, varThreshold=50, detectShadows=False)
            kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (5, 5))
            # Give the subtractor some frames to learn before triggering
            learning_frames = 30
            consecutive_motion_frames = 0

            while self._running:
                loop_start = time.monotonic()

                ret, frame = cap.read()
                if not ret or frame is None:
                    break  # Stream dropped, will try to reconnect

                with QMutexLocker(self._mutex):
                    tracking = self._tracking_enabled
                    filter_enabled = self._filter_enabled
                    min_area = self._min_area
                    persistence = self._persistence
                    snapshot_on_motion = self._snapshot_on_motion
                    snapshot_interval = self._snapshot_interval
                    ai_enabled = self._ai_enabled
                    ai_conf = self._ai_confidence
                    ai_person = self._ai_detect_person
                    ai_vehicles = self._ai_detect_vehicles
                    ai_animals = self._ai_detect_animals
                    ai_filter_snapshots = self._ai_filter_snapshots

                if tracking:
                    # Apply background subtraction
                    mask = bg_subtractor.apply(frame)
                    
                    if learning_frames > 0:
                        learning_frames -= 1
                    else:
                        if filter_enabled:
                            # Morphological open to remove noise (bugs/rain)
                            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)
                        
                        # Find contours of moving objects
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        
                        frame_has_motion = False
                        valid_contours = []
                        
                        for contour in contours:
                            if cv2.contourArea(contour) > min_area:
                                valid_contours.append(cv2.boundingRect(contour))
                                frame_has_motion = True
                                
                        if frame_has_motion:
                            consecutive_motion_frames += 1
                        else:
                            consecutive_motion_frames = 0
                            
                        # Only trigger if motion persists for required frames
                        if consecutive_motion_frames >= persistence:
                            target_detected = False

                            if ai_enabled:
                                allowed_categories = set()
                                if ai_person:
                                    allowed_categories.add('person')
                                if ai_vehicles:
                                    allowed_categories.add('vehicle')
                                if ai_animals:
                                    allowed_categories.add('animal')

                                # Run lightweight AI detector on the frame
                                detector = AIDetector.get_instance()
                                detections = detector.detect(
                                    frame,
                                    conf_threshold=ai_conf,
                                    allowed_categories=allowed_categories,
                                )

                                if len(detections) > 0:
                                    target_detected = True
                                    detector.draw_detections(frame, detections)
                                else:
                                    # If no AI target detected, render subtle motion boxes
                                    for (x, y, w, h) in valid_contours:
                                        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                            else:
                                # Standard motion tracking boxes
                                target_detected = True
                                for (x, y, w, h) in valid_contours:
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                
                            if snapshot_on_motion:
                                # If ai_filter_snapshots is True and AI is enabled, require a recognized target
                                should_snapshot = target_detected or (not ai_enabled) or (not ai_filter_snapshots)

                                if should_snapshot:
                                    now = time.monotonic()
                                    if now - self._last_snapshot_time >= snapshot_interval:
                                        self._last_snapshot_time = now
                                        self._save_snapshot(frame)
                else:
                    # Reset states when tracking is disabled
                    learning_frames = 30
                    consecutive_motion_frames = 0

                # Convert BGR -> RGB -> QImage -> QPixmap
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_image = QImage(
                    rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888,
                )
                pixmap = QPixmap.fromImage(q_image)

                self.frame_ready.emit(pixmap)

                # FPS calculation
                frame_count += 1
                elapsed = time.monotonic() - fps_start_time
                if elapsed >= 1.0:
                    self.fps_updated.emit(frame_count / elapsed)
                    frame_count = 0
                    fps_start_time = time.monotonic()

                # FPS cap — sleep remaining time
                processing_time = time.monotonic() - loop_start
                sleep_time = frame_interval - processing_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

            cap.release()

            if self._running:
                # Stream dropped unexpectedly, try to reconnect
                retry_count += 1
                if retry_count > self.MAX_RETRIES:
                    self.status_changed.emit('error')
                    break
                self.status_changed.emit('reconnecting')
                wait_time = min(2 ** retry_count, 30)
                self._interruptible_sleep(wait_time)

        self.status_changed.emit('stopped')

    def stop(self):
        """Signal the worker to stop gracefully."""
        self._running = False

    def _save_snapshot(self, frame):
        """Save a snapshot to the designated folder."""
        folder = Path(self.save_folder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = folder / f'CH{self.channel}_{timestamp}.jpg'
            cv2.imwrite(str(filename), frame)
        except Exception:
            pass  # Fail silently if directory is not writable

    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be interrupted by stop()."""
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time and self._running:
            time.sleep(0.1)
