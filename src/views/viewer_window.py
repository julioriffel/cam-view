"""Main camera grid viewer window for the DVR Viewer."""

import math
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout,
    QLabel, QPushButton, QFrame, QToolBar, QStatusBar, QSizePolicy,
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize
from PySide6.QtGui import QPixmap, QColor, QPainter

from src.core.connection import DVRConfig, build_rtsp_url
from src.core.stream_worker import StreamWorker
from src.styles.theme import Colors


# ── Tile styles ──────────────────────────────────────────────────

_TILE_STYLE = """
    QFrame#cameraTile {
        background-color: #0d1117;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
    }
"""

_OVERLAY_STYLE = """
    background-color: rgba(0, 0, 0, 0.60);
    color: #ffffff;
    font-size: 11px;
    font-weight: 600;
    border-radius: 4px;
    padding: 3px 8px;
    border: none;
"""

_VIDEO_STYLE = """
    background: #0d1117;
    border: none;
    border-radius: 6px;
"""


class CameraTile(QFrame):
    """A single camera feed tile with overlays."""

    double_clicked = Signal(int)

    def __init__(self, channel: int, parent=None):
        super().__init__(parent)
        self.channel = channel
        self.setObjectName('cameraTile')
        self.setStyleSheet(_TILE_STYLE)
        self.setMinimumSize(320, 240)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(0)

        # Video display
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.video_label.setStyleSheet(_VIDEO_STYLE)
        self.video_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.video_label)

        # Overlay: channel label (top-left)
        self.channel_label = QLabel(f'  CH {channel}  ')
        self.channel_label.setParent(self)
        self.channel_label.setStyleSheet(_OVERLAY_STYLE)
        self.channel_label.adjustSize()
        self.channel_label.move(10, 10)
        self.channel_label.raise_()

        # Overlay: FPS counter (top-right)
        self.fps_label = QLabel('  -- FPS  ')
        self.fps_label.setParent(self)
        self.fps_label.setStyleSheet(_OVERLAY_STYLE)
        self.fps_label.adjustSize()
        self.fps_label.raise_()

        # Overlay: status dot
        self.status_dot = QLabel('●')
        self.status_dot.setParent(self)
        self.status_dot.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 12px; background: transparent; border: none;')
        self.status_dot.adjustSize()
        self.status_dot.raise_()

        self._set_waiting()

    def _set_waiting(self):
        self.video_label.setText(f'CH {self.channel}\nConnecting...')
        self.video_label.setStyleSheet(f"""
            background: #0d1117;
            color: {Colors.TEXT_MUTED};
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
        """)

    def update_frame(self, pixmap: QPixmap):
        scaled = pixmap.scaled(
            self.video_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.video_label.setPixmap(scaled)

    def update_fps(self, fps: float):
        self.fps_label.setText(f'  {fps:.1f} FPS  ')
        self.fps_label.adjustSize()

    def update_status(self, status: str):
        color_map = {
            'live': Colors.SUCCESS,
            'connecting': Colors.WARNING,
            'reconnecting': Colors.WARNING,
            'error': Colors.ERROR,
            'stopped': Colors.TEXT_MUTED,
        }
        color = color_map.get(status, Colors.TEXT_MUTED)
        self.status_dot.setStyleSheet(f'color: {color}; font-size: 12px; background: transparent; border: none;')

        if status == 'error':
            self.video_label.setText(f'CH {self.channel}\nConnection Lost')
            self.video_label.setStyleSheet(f"""
                background: #0d1117;
                color: {Colors.ERROR};
                font-size: 16px;
                font-weight: 600;
                border: none;
                border-radius: 6px;
            """)
        elif status == 'live':
            # Clear waiting text style once we get a frame
            self.video_label.setStyleSheet(_VIDEO_STYLE)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fps_label.move(self.width() - self.fps_label.width() - 10, 10)
        ch_w = self.channel_label.width()
        self.status_dot.move(10 + ch_w + 6, 11)

    def mouseDoubleClickEvent(self, event):
        self.double_clicked.emit(self.channel)


# ── Toolbar button styles ────────────────────────────────────────

_TOOLBAR_BTN = f"""
    QPushButton {{
        background: transparent;
        color: {Colors.TEXT_SECONDARY};
        border: 1px solid rgba(255,255,255,0.08);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 500;
    }}
    QPushButton:hover {{
        background: rgba(255,255,255,0.06);
        color: {Colors.TEXT_PRIMARY};
        border-color: rgba(255,255,255,0.15);
    }}
"""

_DISCONNECT_BTN = f"""
    QPushButton {{
        background: rgba(239, 83, 80, 0.12);
        color: {Colors.ERROR};
        border: 1px solid rgba(239, 83, 80, 0.25);
        border-radius: 8px;
        padding: 6px 14px;
        font-size: 12px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background: rgba(239, 83, 80, 0.25);
        border-color: rgba(239, 83, 80, 0.4);
    }}
"""


class ViewerWindow(QMainWindow):
    """Main camera grid viewer."""

    disconnected = Signal()

    def __init__(self, config: DVRConfig):
        super().__init__()
        self.config = config
        self.workers: list[StreamWorker] = []
        self.tiles: list[CameraTile] = []
        self._fullscreen_channel: int | None = None
        self._uptime_seconds = 0

        self.setWindowTitle(f'CamView — {config.host} ({config.channels} CH)')
        self.setMinimumSize(960, 640)
        self.resize(1280, 800)

        self._setup_ui()
        self._start_streams()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor('#080b1f'))
        painter.end()

    def _setup_ui(self):
        # ── Toolbar ──
        toolbar = QToolBar('Controls')
        toolbar.setMovable(False)
        toolbar.setIconSize(QSize(20, 20))
        toolbar.setStyleSheet(f"""
            QToolBar {{
                background: rgba(12, 14, 35, 0.95);
                border-bottom: 1px solid rgba(255,255,255,0.06);
                padding: 6px 12px;
                spacing: 8px;
            }}
        """)
        self.addToolBar(toolbar)

        # DVR info badge
        info_label = QLabel(f'  {self.config.host}:{self.config.port}  ·  {self.config.channels} CH  ')
        info_label.setStyleSheet(f"""
            background: rgba(74, 158, 255, 0.10);
            color: {Colors.ACCENT};
            border: 1px solid rgba(74, 158, 255, 0.20);
            border-radius: 12px;
            padding: 5px 14px;
            font-size: 12px;
            font-weight: 600;
        """)
        toolbar.addWidget(info_label)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet('background: transparent; border: none;')
        toolbar.addWidget(spacer)

        # Grid view button
        grid_btn = QPushButton('Grid View')
        grid_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        grid_btn.setStyleSheet(_TOOLBAR_BTN)
        grid_btn.clicked.connect(self._show_grid)
        toolbar.addWidget(grid_btn)

        # Disconnect button
        disconnect_btn = QPushButton('Disconnect')
        disconnect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        disconnect_btn.setStyleSheet(_DISCONNECT_BTN)
        disconnect_btn.clicked.connect(self._on_disconnect)
        toolbar.addWidget(disconnect_btn)

        # ── Central Grid ──
        self.central_widget = QWidget()
        self.central_widget.setStyleSheet('background: transparent; border: none;')
        self.setCentralWidget(self.central_widget)

        self.grid_layout = QGridLayout(self.central_widget)
        self.grid_layout.setSpacing(3)
        self.grid_layout.setContentsMargins(3, 3, 3, 3)

        cols = 2 if self.config.channels <= 4 else int(math.ceil(math.sqrt(self.config.channels)))

        for i in range(self.config.channels):
            tile = CameraTile(channel=i + 1)
            tile.double_clicked.connect(self._on_tile_double_click)
            self.tiles.append(tile)
            row, col = divmod(i, cols)
            self.grid_layout.addWidget(tile, row, col)

        # ── Status Bar ──
        status_bar = QStatusBar()
        status_bar.setStyleSheet(f"""
            QStatusBar {{
                background: rgba(8, 11, 31, 0.95);
                color: {Colors.TEXT_MUTED};
                border-top: 1px solid rgba(255,255,255,0.06);
                font-size: 11px;
                padding: 2px 12px;
            }}
            QStatusBar::item {{ border: none; }}
        """)
        self.setStatusBar(status_bar)

        self.connected_label = QLabel('Channels: 0/0')
        self.connected_label.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent; border: none;')
        self.uptime_label = QLabel('Uptime: 00:00:00')
        self.uptime_label.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent; border: none;')

        status_bar.addWidget(self.connected_label)
        status_bar.addPermanentWidget(self.uptime_label)

        # Uptime timer
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)

    def _start_streams(self):
        for i in range(self.config.channels):
            channel = i + 1
            url = build_rtsp_url(self.config, channel)
            worker = StreamWorker(url, channel)
            worker.frame_ready.connect(self.tiles[i].update_frame)
            worker.fps_updated.connect(self.tiles[i].update_fps)
            worker.status_changed.connect(self.tiles[i].update_status)
            worker.status_changed.connect(lambda s, ch=channel: self._on_channel_status(ch, s))
            self.workers.append(worker)
            worker.start()
        self._update_connected_count()

    def _on_channel_status(self, channel: int, status: str):
        self._update_connected_count()

    def _update_connected_count(self):
        live = sum(1 for w in self.workers if w.isRunning())
        self.connected_label.setText(f'  Channels: {live}/{self.config.channels}  ')

    def _update_uptime(self):
        self._uptime_seconds += 1
        h = self._uptime_seconds // 3600
        m = (self._uptime_seconds % 3600) // 60
        s = self._uptime_seconds % 60
        self.uptime_label.setText(f'  Uptime: {h:02d}:{m:02d}:{s:02d}  ')

    def _on_tile_double_click(self, channel: int):
        if self._fullscreen_channel is not None:
            self._show_grid()
        else:
            self._show_fullscreen(channel)

    def _show_fullscreen(self, channel: int):
        self._fullscreen_channel = channel
        for tile in self.tiles:
            if tile.channel != channel:
                tile.hide()

    def _show_grid(self):
        self._fullscreen_channel = None
        for tile in self.tiles:
            tile.show()

    def _on_disconnect(self):
        self._stop_all_streams()
        self.disconnected.emit()
        self.close()

    def _stop_all_streams(self):
        for worker in self.workers:
            worker.stop()
        for worker in self.workers:
            worker.wait(3000)
        self.workers.clear()

    def closeEvent(self, event):
        self._stop_all_streams()
        if self._uptime_timer.isActive():
            self._uptime_timer.stop()
        super().closeEvent(event)
