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


class StreamWorker(QThread):
    """Background worker that reads RTSP frames and emits them as QPixmap signals."""

    frame_ready = Signal(QPixmap)       # Emitted when a new frame is decoded
    fps_updated = Signal(float)          # Emitted periodically with current FPS
    status_changed = Signal(str)         # 'connecting', 'live', 'reconnecting', 'error', 'stopped'
    tracking_status_changed = Signal(bool) # Emitted when tracking toggles

    MAX_RETRIES = 5
    TARGET_FPS = 25

    def __init__(self, rtsp_url: str, channel: int, save_folder: str, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.channel = channel
        self.save_folder = save_folder
        self._running = False
        self._tracking_enabled = False
        self._last_snapshot_time = 0.0
        self._mutex = QMutex()

    def set_tracking(self, enabled: bool):
        """Enable or disable motion tracking."""
        with QMutexLocker(self._mutex):
            self._tracking_enabled = enabled
        self.tracking_status_changed.emit(enabled)

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
            # Give the subtractor some frames to learn before triggering
            learning_frames = 30

            while self._running:
                loop_start = time.monotonic()

                ret, frame = cap.read()
                if not ret or frame is None:
                    break  # Stream dropped, will try to reconnect

                with QMutexLocker(self._mutex):
                    tracking = self._tracking_enabled

                if tracking:
                    # Apply background subtraction
                    mask = bg_subtractor.apply(frame)
                    
                    if learning_frames > 0:
                        learning_frames -= 1
                    else:
                        # Find contours of moving objects
                        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
                        motion_detected = False
                        
                        for contour in contours:
                            if cv2.contourArea(contour) > 800:  # Ignore small noise
                                x, y, w, h = cv2.boundingRect(contour)
                                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                                motion_detected = True
                                
                        if motion_detected:
                            now = time.monotonic()
                            # Save snapshot at most once every 2 seconds
                            if now - self._last_snapshot_time > 2.0:
                                self._last_snapshot_time = now
                                self._save_snapshot(frame)
                else:
                    # Reset learning phase when tracking is disabled so it learns fresh when re-enabled
                    learning_frames = 30

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
