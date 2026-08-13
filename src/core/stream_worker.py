"""
Background RTSP stream worker.

Runs on a dedicated QThread, continuously reads frames from an RTSP source,
converts them to QPixmap, and emits Qt signals for the UI to consume.
Includes automatic reconnection with exponential back-off.
"""

import time

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage, QPixmap


class StreamWorker(QThread):
    """Background worker that reads RTSP frames and emits them as QPixmap signals."""

    frame_ready = Signal(QPixmap)       # Emitted when a new frame is decoded
    fps_updated = Signal(float)          # Emitted periodically with current FPS
    status_changed = Signal(str)         # 'connecting', 'live', 'reconnecting', 'error', 'stopped'

    MAX_RETRIES = 5
    TARGET_FPS = 25

    def __init__(self, rtsp_url: str, channel: int, parent=None):
        super().__init__(parent)
        self.rtsp_url = rtsp_url
        self.channel = channel
        self._running = False
        self._mutex = QMutex()

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

            while self._running:
                loop_start = time.monotonic()

                ret, frame = cap.read()
                if not ret or frame is None:
                    break  # Stream dropped, will try to reconnect

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

    def _interruptible_sleep(self, seconds: float):
        """Sleep that can be interrupted by stop()."""
        end_time = time.monotonic() + seconds
        while time.monotonic() < end_time and self._running:
            time.sleep(0.1)
