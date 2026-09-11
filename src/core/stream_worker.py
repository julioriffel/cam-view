"""
Background RTSP stream worker with High-Performance Motion and Asynchronous AI Detection.

Runs on a dedicated QThread:
- Continuously reads frames from an RTSP source without blocking or stutter.
- Executes downscaled motion detection (KNN / MOG2 with shadow suppression).
- Dispatches AI object recognition asynchronously to avoid frame drops.
- Converts video frames to QPixmap and emits Qt signals for the UI.
- Includes automatic reconnection with exponential back-off.
"""

import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage, QPixmap

from src.core.connection import DVRConfig
from src.core.motion_detector import MotionDetector
from src.core.ai_detector import AIDetector, Detection
from src.core.event_db import EventDatabase


class StreamWorker(QThread):
    """Background thread to process RTSP stream via OpenCV with non-blocking AI."""

    frame_ready = Signal(QPixmap)
    fps_updated = Signal(float)
    status_changed = Signal(str)
    tracking_status_changed = Signal(bool)
    metrics_updated = Signal(dict)
    alert_triggered = Signal(dict)

    TARGET_FPS = 20.0
    MAX_RETRIES = 5

    def __init__(self, url: str, channel: int, config: DVRConfig, parent=None):
        super().__init__(parent)
        self.rtsp_url = url
        self.channel = channel
        self.save_folder = config.save_folder
        self._tracking_enabled = False

        # Motion detector module
        self._motion_detector = MotionDetector(
            algorithm=getattr(config, 'motion_algorithm', 'knn'),
            target_width=getattr(config, 'motion_downscale_width', 480),
            min_area=config.tracking_min_area,
            persistence=config.tracking_persistence,
            filter_enabled=config.tracking_filter_enabled,
        )

        # Snapshot and AI parameters
        self._snapshot_on_motion = config.snapshot_on_motion
        self._snapshot_interval = float(config.snapshot_interval)
        self._ai_enabled = config.ai_enabled
        self._ai_confidence = float(config.ai_confidence_threshold)
        self._ai_detect_person = config.ai_detect_person
        self._ai_detect_vehicles = config.ai_detect_vehicles
        self._ai_detect_animals = config.ai_detect_animals
        self._ai_filter_snapshots = config.ai_filter_snapshots

        # Async AI tracking state
        self._ai_busy = False
        self._active_ai_detections: List[Detection] = []
        self._ai_detections_expiry = 0.0

        self._running = False
        self._mutex = QMutex()
        self._last_snapshot_time = 0.0

    def set_tracking(self, enabled: bool):
        """Enable or disable motion tracking overlays and snapshots."""
        with QMutexLocker(self._mutex):
            self._tracking_enabled = enabled
            if not enabled:
                self._motion_detector.reset()
                self._active_ai_detections.clear()
                self._ai_detections_expiry = 0.0
        self.tracking_status_changed.emit(enabled)

    def update_tracking_params(
        self,
        filter_enabled: bool,
        min_area: int,
        persistence: int,
        motion_algorithm: str = 'knn',
        motion_downscale_width: int = 480,
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
            self._motion_detector.update_params(
                algorithm=motion_algorithm,
                min_area=min_area,
                persistence=persistence,
                filter_enabled=filter_enabled,
                target_width=motion_downscale_width,
            )
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

    def _on_async_ai_finished(self, detections: List[Detection], snap_frame: Optional[cv2.Mat] = None):
        """Callback executed on background thread when AI inference finishes."""
        if not self._running:
            self._ai_busy = False
            return

        now = time.monotonic()
        self._ai_busy = False

        with QMutexLocker(self._mutex):
            snapshot_on_motion = self._snapshot_on_motion
            snapshot_interval = self._snapshot_interval
            ai_filter_snapshots = self._ai_filter_snapshots

        if len(detections) > 0:
            with QMutexLocker(self._mutex):
                self._active_ai_detections = detections
                # Keep active AI bounding boxes visible for 1.2s for smooth visual tracking
                self._ai_detections_expiry = now + 1.2

            alert_label = ", ".join(
                [f"{d.class_name.capitalize()} ({int(d.confidence * 100)}%)" for d in detections[:2]]
            )
            alert_category = detections[0].category

            snapshot_path = None
            if snapshot_on_motion:
                if now - self._last_snapshot_time >= snapshot_interval:
                    self._last_snapshot_time = now
                    if snap_frame is not None:
                        # Draw bounding boxes onto the saved snapshot
                        out_frame = snap_frame.copy()
                        AIDetector.get_instance().draw_detections(out_frame, detections)
                        snapshot_path = self._save_snapshot(out_frame)

            # Log to SQLite Event database (with 10-second debounce per category)
            db = EventDatabase.get_instance()
            for d in detections:
                db.log_event(
                    channel=self.channel,
                    category=d.category,
                    label=f"{d.class_name.capitalize()} ({int(d.confidence * 100)}%)",
                    confidence=d.confidence,
                    snapshot_path=snapshot_path,
                    cooldown=10.0,
                )

            # Emit alert event for desktop notifications and UI status
            self.alert_triggered.emit({
                'channel': self.channel,
                'label': alert_label,
                'category': alert_category,
                'snapshot_path': snapshot_path,
                'timestamp': now,
            })
        else:
            # No AI targets recognized
            if snapshot_on_motion and not ai_filter_snapshots:
                if now - self._last_snapshot_time >= snapshot_interval:
                    self._last_snapshot_time = now
                    snapshot_path = self._save_snapshot(snap_frame) if snap_frame is not None else None
                    self.alert_triggered.emit({
                        'channel': self.channel,
                        'label': "Motion Detected",
                        'category': "motion",
                        'snapshot_path': snapshot_path,
                        'timestamp': now,
                    })

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
            accumulated_latency = 0.0
            accumulated_bytes = 0.0
            total_dropped = 0
            interval_dropped = 0
            last_frame_time = 0.0

            # Reset motion detector on connection
            self._motion_detector.reset()

            while self._running:
                loop_start = time.monotonic()

                grab_start = time.monotonic()
                ret, frame = cap.read()
                grab_latency_ms = (time.monotonic() - grab_start) * 1000.0

                if not ret or frame is None:
                    break  # Stream dropped, will reconnect

                now_time = time.monotonic()
                if last_frame_time > 0.0:
                    delta = now_time - last_frame_time
                    if delta > 1.7 * frame_interval:
                        dropped_est = max(1, int(round(delta / frame_interval)) - 1)
                        total_dropped += dropped_est
                        interval_dropped += dropped_est
                last_frame_time = now_time

                with QMutexLocker(self._mutex):
                    tracking = self._tracking_enabled
                    snapshot_on_motion = self._snapshot_on_motion
                    snapshot_interval = self._snapshot_interval
                    ai_enabled = self._ai_enabled
                    ai_conf = self._ai_confidence
                    ai_person = self._ai_detect_person
                    ai_vehicles = self._ai_detect_vehicles
                    ai_animals = self._ai_detect_animals
                    ai_filter_snapshots = self._ai_filter_snapshots
                    active_detections = list(self._active_ai_detections)
                    ai_expiry = self._ai_detections_expiry

                if tracking:
                    # High-performance downscaled motion analysis
                    has_raw, is_persistent, valid_boxes = self._motion_detector.process_frame(frame)

                    if is_persistent:
                        if ai_enabled:
                            # Submit frame for asynchronous detection if AI worker is idle
                            if not self._ai_busy:
                                self._ai_busy = True
                                allowed_categories = set()
                                if ai_person:
                                    allowed_categories.add('person')
                                if ai_vehicles:
                                    allowed_categories.add('vehicle')
                                if ai_animals:
                                    allowed_categories.add('animal')

                                frame_copy = frame.copy()
                                AIDetector.get_instance().detect_async(
                                    frame=frame_copy,
                                    conf_threshold=ai_conf,
                                    allowed_categories=allowed_categories,
                                    callback=lambda dets, snap=frame_copy: self._on_async_ai_finished(dets, snap),
                                )

                            # Render current active AI detections if still valid
                            if now_time < ai_expiry and len(active_detections) > 0:
                                AIDetector.get_instance().draw_detections(frame, active_detections)
                            else:
                                # Subtle motion bounding boxes while AI is processing or if no AI targets
                                for (x, y, w, h) in valid_boxes:
                                    cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 1)
                        else:
                            # Pure motion tracking without AI
                            for (x, y, w, h) in valid_boxes:
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

                            snapshot_path = None
                            if snapshot_on_motion:
                                if now_time - self._last_snapshot_time >= snapshot_interval:
                                    self._last_snapshot_time = now_time
                                    snapshot_path = self._save_snapshot(frame)

                            self.alert_triggered.emit({
                                'channel': self.channel,
                                'label': "Motion Detected",
                                'category': "motion",
                                'snapshot_path': snapshot_path,
                                'timestamp': now_time,
                            })
                    else:
                        # If AI detection is active but motion subsided, still render smoothly until expiry
                        if ai_enabled and now_time < ai_expiry and len(active_detections) > 0:
                            AIDetector.get_instance().draw_detections(frame, active_detections)

                # Convert BGR -> RGB -> QImage -> QPixmap
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, ch = rgb_frame.shape
                bytes_per_line = ch * w
                q_image = QImage(
                    rgb_frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888,
                )
                pixmap = QPixmap.fromImage(q_image)

                self.frame_ready.emit(pixmap)

                # Metrics accumulation
                frame_count += 1
                accumulated_latency += grab_latency_ms
                est_bytes = (w * h * 3.0) / (60.0 if w >= 1280 else 40.0)
                accumulated_bytes += est_bytes

                # Periodic 1-second metrics calculation
                elapsed = time.monotonic() - fps_start_time
                if elapsed >= 1.0:
                    current_fps = frame_count / elapsed
                    avg_latency = accumulated_latency / max(1, frame_count)
                    bytes_per_sec = accumulated_bytes / elapsed

                    self.fps_updated.emit(current_fps)
                    self.metrics_updated.emit({
                        'channel': self.channel,
                        'fps': current_fps,
                        'bytes_per_sec': bytes_per_sec,
                        'latency_ms': avg_latency,
                        'total_dropped': total_dropped,
                        'interval_dropped': interval_dropped,
                        'width': w,
                        'height': h,
                    })

                    frame_count = 0
                    accumulated_latency = 0.0
                    accumulated_bytes = 0.0
                    interval_dropped = 0
                    fps_start_time = time.monotonic()

                # FPS cap — sleep remaining time
                processing_time = time.monotonic() - loop_start
                sleep_time = frame_interval - processing_time
                if sleep_time > 0:
                    time.sleep(sleep_time)

            cap.release()

            if self._running:
                # Stream dropped unexpectedly, attempt reconnect
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

    def _save_snapshot(self, frame) -> Optional[str]:
        """Save a snapshot to the designated folder and return the saved path."""
        if frame is None:
            return None
        folder = Path(self.save_folder)
        try:
            folder.mkdir(parents=True, exist_ok=True)
            now = datetime.now()
            timestamp = now.strftime('%Y%m%d_%H%M%S') + f"_{now.microsecond // 1000:03d}"
            filename = folder / f"CH{self.channel}_{timestamp}.jpg"
            if filename.exists():
                counter = 1
                while filename.exists():
                    filename = folder / f"CH{self.channel}_{timestamp}_{counter}.jpg"
                    counter += 1
            cv2.imwrite(str(filename), frame)
            return str(filename)
        except Exception:
            return None

    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be interrupted by stop()."""
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time and self._running:
            time.sleep(0.1)
