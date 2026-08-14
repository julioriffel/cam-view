import math
import time
from pathlib import Path
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QGridLayout, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFrame, QToolBar, QStatusBar, QSizePolicy,
    QFileDialog, QComboBox, QSystemTrayIcon, QMenu
)
from PySide6.QtCore import Qt, QTimer, Signal, QSize, QUrl
from PySide6.QtGui import (
    QPixmap, QColor, QPainter, QShortcut, QKeySequence,
    QIcon, QDesktopServices
)

from src.core.connection import DVRConfig, build_rtsp_url
from src.core.stream_worker import StreamWorker
from src.core import config_store
from src.views.settings_dialog import TrackingSettingsDialog
from src.views.events_window import EventsStatsWindow
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


class TileControlPanel(QWidget):
    quality_changed = Signal(str)
    tracking_toggled = Signal()

    def __init__(self, default_subtype: int, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setObjectName('tileControlPanel')
        self.setStyleSheet("""
            QWidget#tileControlPanel {
                background-color: rgba(0, 0, 0, 0.85);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 6px;
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(4)

        self._current_mode = 'HD' if default_subtype == 0 else 'SD'

        # Label for the buttons
        label = QLabel("Stream:")
        label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 11px; font-weight: 600; background: transparent; border: none; padding-right: 2px;")
        layout.addWidget(label)

        # Segmented quality buttons
        self.btn_hd = QPushButton('HD')
        self.btn_sd = QPushButton('SD')
        self.btn_off = QPushButton('OFF')

        for btn in (self.btn_hd, self.btn_sd, self.btn_off):
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda checked=False, b=btn: self._on_quality_clicked(b.text()))
            layout.addWidget(btn)

        # Separator
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color: rgba(255,255,255,0.2); background: transparent;")
        layout.addWidget(sep)

        # Motion tracking button
        self.btn_track = QPushButton('🏃')
        self.btn_track.setCursor(Qt.CursorShape.PointingHandCursor)
        self.btn_track.setCheckable(True)
        self.btn_track.clicked.connect(self._on_track_clicked)
        layout.addWidget(self.btn_track)
        
        self._update_styles()

    def _on_track_clicked(self):
        self._update_styles()
        self.tracking_toggled.emit()

    def _on_quality_clicked(self, mode: str):
        if self._current_mode != mode:
            self._current_mode = mode
            self._update_styles()
            self.quality_changed.emit(mode)

    def _update_styles(self):
        base_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 11px;
                font-weight: 600;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                color: #ffffff;
            }}
        """
        active_style = f"""
            QPushButton {{
                background-color: {Colors.ACCENT};
                color: #ffffff;
                border: 1px solid {Colors.ACCENT};
                border-radius: 4px;
                font-size: 11px;
                font-weight: 700;
                padding: 4px 8px;
            }}
        """
        track_style = f"""
            QPushButton {{
                background-color: transparent;
                color: {Colors.TEXT_MUTED};
                border: 1px solid transparent;
                border-radius: 4px;
                font-size: 11px;
                padding: 4px 8px;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.12);
                color: #ffffff;
            }}
            QPushButton:checked {{
                background-color: {Colors.WARNING};
                color: #ffffff;
                border: 1px solid {Colors.WARNING};
                border-radius: 4px;
                font-weight: 700;
            }}
            QPushButton:checked:hover {{
                background-color: #ffb74d;
                border-color: #ffb74d;
            }}
        """
        
        self.btn_hd.setStyleSheet(active_style if self._current_mode == 'HD' else base_style)
        self.btn_sd.setStyleSheet(active_style if self._current_mode == 'SD' else base_style)
        self.btn_off.setStyleSheet(active_style if self._current_mode == 'OFF' else base_style)
        self.btn_track.setStyleSheet(track_style)

    def set_tracking_state(self, enabled: bool):
        self.btn_track.setChecked(enabled)
        self._update_styles()

    def set_mode(self, mode: str):
        self._current_mode = mode
        self._update_styles()

    def set_mode_and_tracking(self, mode: str, tracking: bool):
        self._current_mode = mode
        self.btn_track.setChecked(tracking)
        self._update_styles()


class CameraTile(QFrame):
    """A single camera feed tile with overlays."""

    double_clicked = Signal(int)
    quality_changed = Signal(int, str)  # (channel, mode: 'HD'|'SD'|'OFF')
    tracking_toggled = Signal(int)

    def __init__(self, channel: int, default_subtype: int, parent=None):
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

        # Overlay: tracking badge (hidden by default)
        self.tracking_badge = QLabel(' 🏃 Tracking ')
        self.tracking_badge.setParent(self)
        self.tracking_badge.setStyleSheet(f"""
            background-color: rgba(255, 167, 38, 0.20);
            color: {Colors.WARNING};
            border: 1px solid rgba(255, 167, 38, 0.50);
            font-size: 11px;
            font-weight: 700;
            border-radius: 4px;
            padding: 2px 6px;
        """)
        self.tracking_badge.adjustSize()
        self.tracking_badge.hide()
        self.tracking_badge.raise_()

        # Overlay: Quality Selector & Tracking controls
        self.controls = TileControlPanel(default_subtype, self)
        self.controls.quality_changed.connect(
            lambda mode: self.quality_changed.emit(self.channel, mode)
        )
        self.controls.tracking_toggled.connect(
            lambda: self.tracking_toggled.emit(self.channel)
        )
        self.controls.adjustSize()
        self.controls.raise_()

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

    def set_initial_state(self, mode: str, tracking: bool):
        """Set initial stream mode and tracking state on startup."""
        self.controls.set_mode_and_tracking(mode, tracking)
        if mode == 'OFF':
            self.set_disabled_state()
        else:
            self._set_waiting()
        self.set_tracking_visible(tracking)

    def set_disabled_state(self):
        """Show disabled state when OFF is selected."""
        self.video_label.clear()
        self.video_label.setText(f'CH {self.channel}\nDisabled')
        self.video_label.setStyleSheet(f"""
            background: #0d1117;
            color: {Colors.TEXT_MUTED};
            font-size: 16px;
            font-weight: 600;
            border: none;
            border-radius: 6px;
        """)
        self.fps_label.setText('  -- FPS  ')
        self.status_dot.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 12px; background: transparent; border: none;')

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

    def set_tracking_visible(self, visible: bool):
        self.tracking_badge.setVisible(visible)
        self.controls.set_tracking_state(visible)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.fps_label.move(self.width() - self.fps_label.width() - 10, 10)
        ch_w = self.channel_label.width()
        self.status_dot.move(10 + ch_w + 6, 11)
        self.tracking_badge.move(self.width() - self.tracking_badge.width() - 10, 10 + self.fps_label.height() + 6)
        self.controls.move(10, self.height() - self.controls.height() - 10)

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
        self._channel_metrics: dict[int, dict] = {}
        self._last_notification_times: dict[int, float] = {}
        self._last_alert_snapshot_path: str | None = None

        self.setWindowTitle(f'CamView — {config.host} ({config.channels} CH)')
        self.setMinimumSize(960, 640)
        self.resize(1280, 800)

        self._init_tray_icon()
        self._setup_ui()
        self._start_streams()

    def _init_tray_icon(self):
        """Setup system tray icon with Nano Banana icon and context menu."""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            self.tray_icon = None
            return

        icon_path = Path(__file__).parent.parent / 'assets' / 'icon.jpg'
        icon = QIcon(str(icon_path)) if icon_path.exists() else QIcon()

        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip(f"CamView — {self.config.host} ({self.config.channels} CH)")

        # Context Menu
        menu = QMenu(self)
        menu.setStyleSheet(f"""
            QMenu {{
                background-color: {Colors.BG_PRIMARY};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 4px;
            }}
            QMenu::item {{
                padding: 6px 20px;
                border-radius: 4px;
            }}
            QMenu::item:selected {{
                background-color: {Colors.ACCENT};
                color: #ffffff;
            }}
        """)

        act_show = menu.addAction("👁️ Show CamView")
        act_show.triggered.connect(self._restore_from_tray)

        act_events = menu.addAction("📊 Events & Stats...")
        act_events.triggered.connect(self._show_events_window)

        act_settings = menu.addAction("⚙️ Settings...")
        act_settings.triggered.connect(self._show_settings)

        menu.addSeparator()

        act_quit = menu.addAction("❌ Quit CamView")
        act_quit.triggered.connect(self._quit_application)

        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.messageClicked.connect(self._on_tray_message_clicked)
        self.tray_icon.show()

    def _on_tray_activated(self, reason):
        if reason in (QSystemTrayIcon.ActivationReason.Trigger, QSystemTrayIcon.ActivationReason.DoubleClick):
            if self.isVisible() and not self.isMinimized():
                self.hide()
            else:
                self._restore_from_tray()

    def _restore_from_tray(self):
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _on_tray_message_clicked(self):
        """Open the snapshot referrer file if present and bring app to front."""
        if self._last_alert_snapshot_path and Path(self._last_alert_snapshot_path).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(self._last_alert_snapshot_path))
        self._restore_from_tray()

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

        # Help / Tips label
        help_label = QLabel('  💡 Tip: Press Ctrl+1, Ctrl+2, etc., to toggle motion tracking per channel  ')
        help_label.setStyleSheet(f"""
            color: {Colors.TEXT_MUTED};
            font-size: 12px;
            font-style: italic;
            background: transparent;
            border: none;
        """)
        toolbar.addWidget(help_label)

        # Spacer
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        spacer.setStyleSheet('background: transparent; border: none;')
        toolbar.addWidget(spacer)

        # Events & Stats button
        events_btn = QPushButton('📊 Events & Stats')
        events_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        events_btn.setStyleSheet(_TOOLBAR_BTN)
        events_btn.setToolTip("View AI detection logs & statistics (Ctrl+E)")
        events_btn.clicked.connect(self._show_events_window)
        toolbar.addWidget(events_btn)

        shortcut_events = QShortcut(QKeySequence("Ctrl+E"), self)
        shortcut_events.activated.connect(self._show_events_window)

        # Settings button
        settings_btn = QPushButton('⚙️ Settings')
        settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        settings_btn.setStyleSheet(_TOOLBAR_BTN)
        settings_btn.clicked.connect(self._show_settings)
        toolbar.addWidget(settings_btn)

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
            tile = CameraTile(channel=i + 1, default_subtype=self.config.subtype)
            tile.double_clicked.connect(self._on_tile_double_click)
            tile.quality_changed.connect(self._on_quality_changed)
            tile.tracking_toggled.connect(self._on_tile_tracking_toggled)
            self.tiles.append(tile)
            row, col = divmod(i, cols)
            self.grid_layout.addWidget(tile, row, col)
            
            # Setup shortcut for this channel
            if i < 9:  # Ctrl+1 to Ctrl+9
                shortcut = QShortcut(QKeySequence(f"Ctrl+{i + 1}"), self)
                # Capture i correctly using default argument in lambda
                shortcut.activated.connect(lambda ch_idx=i: self._toggle_tracking(ch_idx))

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
        self.connected_label.setStyleSheet(f'color: {Colors.TEXT_PRIMARY}; font-size: 11px; font-weight: 600; background: transparent; border: none;')

        self.bitrate_label = QLabel('🌐 0.0 KB/s')
        self.bitrate_label.setStyleSheet(f'color: {Colors.ACCENT}; font-size: 11px; font-weight: 600; background: transparent; border: none;')

        self.latency_label = QLabel('⏱️ -- ms')
        self.latency_label.setStyleSheet(f'color: {Colors.TEXT_SECONDARY}; font-size: 11px; background: transparent; border: none;')

        self.health_label = QLabel('🟢 0 Drops')
        self.health_label.setStyleSheet(f'color: {Colors.SUCCESS}; font-size: 11px; font-weight: 600; background: transparent; border: none;')

        self.uptime_label = QLabel('Uptime: 00:00:00')
        self.uptime_label.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 11px; background: transparent; border: none;')

        status_bar.addWidget(self.connected_label)
        status_bar.addWidget(self._make_status_sep())
        status_bar.addWidget(self.bitrate_label)
        status_bar.addWidget(self._make_status_sep())
        status_bar.addWidget(self.latency_label)
        status_bar.addWidget(self._make_status_sep())
        status_bar.addWidget(self.health_label)
        status_bar.addPermanentWidget(self.uptime_label)

        # Uptime timer
        self._uptime_timer = QTimer(self)
        self._uptime_timer.timeout.connect(self._update_uptime)
        self._uptime_timer.start(1000)

    def _make_status_sep(self) -> QLabel:
        sep = QLabel('│')
        sep.setStyleSheet('color: rgba(255, 255, 255, 0.15); font-size: 10px; margin: 0 4px; background: transparent; border: none;')
        return sep

    def _start_streams(self):
        # Ensure channel_states dict exists
        if not hasattr(self.config, 'channel_states') or not isinstance(self.config.channel_states, dict):
            self.config.channel_states = {}

        self.workers = [None] * self.config.channels

        for i in range(self.config.channels):
            ch = i + 1
            st = self.config.channel_states.get(str(ch), {})
            mode = st.get('mode', 'HD' if self.config.subtype == 0 else 'SD')
            tracking = st.get('tracking', False)

            # Sync tile UI state
            self.tiles[i].set_initial_state(mode, tracking)

            if mode == 'OFF':
                self.workers[i] = None
            else:
                subtype = 0 if mode == 'HD' else 1
                self._start_worker(i, subtype)
                if tracking and self.workers[i] is not None:
                    self.workers[i].set_tracking(True)
            
        self._update_connected_count()

    def _start_worker(self, index: int, subtype: int):
        channel = index + 1
        url = build_rtsp_url(self.config, channel, subtype_override=subtype)
        worker = StreamWorker(url, channel, self.config)
        worker.frame_ready.connect(self.tiles[index].update_frame)
        worker.fps_updated.connect(self.tiles[index].update_fps)
        worker.status_changed.connect(self.tiles[index].update_status)
        worker.tracking_status_changed.connect(self.tiles[index].set_tracking_visible)
        worker.status_changed.connect(lambda s, ch=channel: self._on_channel_status(ch, s))
        worker.metrics_updated.connect(self._on_worker_metrics)
        worker.alert_triggered.connect(self._on_worker_alert)
        self.workers[index] = worker
        worker.start()

    def _on_quality_changed(self, channel: int, mode: str):
        index = channel - 1

        # Persist mode change
        if not hasattr(self.config, 'channel_states') or not isinstance(self.config.channel_states, dict):
            self.config.channel_states = {}
        self.config.channel_states.setdefault(str(channel), {})['mode'] = mode
        config_store.save_config(self.config)

        # Stop existing worker if any
        if self.workers[index] is not None:
            self.workers[index].stop()
            self.workers[index].wait(2000)
            self.workers[index] = None

        # Clear metric for stopped channel
        self._channel_metrics.pop(channel, None)

        if mode == 'OFF':
            self.tiles[index].set_disabled_state()
        else:
            self.tiles[index]._set_waiting()
            subtype = 0 if mode == 'HD' else 1
            self._start_worker(index, subtype)

            # Restore tracking state if it was active
            was_tracking = self.config.channel_states.get(str(channel), {}).get('tracking', False)
            if was_tracking and self.workers[index] is not None:
                self.workers[index].set_tracking(True)
                self.tiles[index].set_tracking_visible(True)
            
        self._update_connected_count()
        self._update_network_diagnostics()

    def _on_channel_status(self, channel: int, status: str):
        if status in ('stopped', 'error'):
            self._channel_metrics.pop(channel, None)
        self._update_connected_count()
        self._update_network_diagnostics()

    def _on_worker_metrics(self, data: dict):
        channel = data.get('channel')
        if channel is not None:
            self._channel_metrics[channel] = data
            self._update_network_diagnostics()

    def _update_network_diagnostics(self):
        active_channels = [
            w.channel for w in self.workers if w is not None and w.isRunning()
        ]

        if not active_channels:
            self.bitrate_label.setText('🌐 0.0 KB/s')
            self.latency_label.setText('⏱️ -- ms')
            self.health_label.setText('⚪ Idle')
            self.health_label.setStyleSheet(f'color: {Colors.TEXT_MUTED}; font-size: 11px; font-weight: 600; background: transparent; border: none;')
            return

        total_bytes_sec = 0.0
        total_latency = 0.0
        total_dropped = 0
        interval_dropped = 0
        valid_count = 0

        for ch in active_channels:
            m = self._channel_metrics.get(ch)
            if m:
                total_bytes_sec += m.get('bytes_per_sec', 0.0)
                total_latency += m.get('latency_ms', 0.0)
                total_dropped += m.get('total_dropped', 0)
                interval_dropped += m.get('interval_dropped', 0)
                valid_count += 1

        # 1. Format Live Bitrate
        if total_bytes_sec >= 1_000_000:
            mb_s = total_bytes_sec / 1_000_000.0
            self.bitrate_label.setText(f'🌐 {mb_s:.2f} MB/s')
        else:
            kb_s = total_bytes_sec / 1_000.0
            self.bitrate_label.setText(f'🌐 {kb_s:.1f} KB/s')

        # 2. Format Latency
        if valid_count > 0:
            avg_lat = total_latency / valid_count
            self.latency_label.setText(f'⏱️ ~{avg_lat:.0f} ms')
        else:
            self.latency_label.setText('⏱️ -- ms')

        # 3. Format Stream Health & Drops
        if interval_dropped > 0:
            self.health_label.setText(f'🔴 Jitter (+{interval_dropped} drops)')
            self.health_label.setStyleSheet(f'color: {Colors.ERROR}; font-size: 11px; font-weight: 600; background: transparent; border: none;')
        elif total_dropped > 0:
            self.health_label.setText(f'🟡 {total_dropped} Drops')
            self.health_label.setStyleSheet(f'color: {Colors.WARNING}; font-size: 11px; font-weight: 600; background: transparent; border: none;')
        else:
            self.health_label.setText('🟢 0 Drops (Stable)')
            self.health_label.setStyleSheet(f'color: {Colors.SUCCESS}; font-size: 11px; font-weight: 600; background: transparent; border: none;')

    def _update_connected_count(self):
        live = sum(1 for w in self.workers if w is not None and w.isRunning())
        self.connected_label.setText(f'Channels: {live}/{self.config.channels}')

    def _update_uptime(self):
        self._uptime_seconds += 1
        h = self._uptime_seconds // 3600
        m = (self._uptime_seconds % 3600) // 60
        s = self._uptime_seconds % 60
        self.uptime_label.setText(f'Uptime: {h:02d}:{m:02d}:{s:02d}')

    def _show_events_window(self):
        dialog = EventsStatsWindow(self.config, self)
        dialog.exec()

    def _show_settings(self):
        dialog = TrackingSettingsDialog(self.config, self)
        dialog.settings_saved.connect(self._on_settings_saved)
        dialog.exec()
        
    def _on_settings_saved(self, config: DVRConfig):
        self.config = config
        config_store.save_config(self.config)
        
        # Instantly apply to running streams
        for worker in self.workers:
            if worker is not None:
                worker.save_folder = self.config.save_folder
                worker.update_tracking_params(
                    filter_enabled=self.config.tracking_filter_enabled,
                    min_area=self.config.tracking_min_area,
                    persistence=self.config.tracking_persistence,
                    snapshot_on_motion=self.config.snapshot_on_motion,
                    snapshot_interval=self.config.snapshot_interval,
                    ai_enabled=self.config.ai_enabled,
                    ai_confidence=self.config.ai_confidence_threshold,
                    ai_detect_person=self.config.ai_detect_person,
                    ai_detect_vehicles=self.config.ai_detect_vehicles,
                    ai_detect_animals=self.config.ai_detect_animals,
                    ai_filter_snapshots=self.config.ai_filter_snapshots,
                )

    def _on_tile_double_click(self, channel: int):
        if self._fullscreen_channel == channel:
            self._show_grid()
        else:
            self._show_fullscreen(channel)

    def _show_fullscreen(self, channel: int):
        self._fullscreen_channel = channel
        for tile in self.tiles:
            if tile.channel != channel:
                tile.hide()

    def _on_tile_tracking_toggled(self, channel: int):
        index = channel - 1
        self._toggle_tracking(index)

    def _toggle_tracking(self, index: int):
        ch = index + 1
        if index < len(self.workers) and self.workers[index] is not None:
            worker = self.workers[index]
            new_state = not worker.is_tracking()
            worker.set_tracking(new_state)
            self.tiles[index].set_tracking_visible(new_state)
        else:
            st = self.config.channel_states.get(str(ch), {})
            new_state = not st.get('tracking', False)
            self.tiles[index].set_tracking_visible(new_state)

        # Persist tracking state
        if not hasattr(self.config, 'channel_states') or not isinstance(self.config.channel_states, dict):
            self.config.channel_states = {}
        self.config.channel_states.setdefault(str(ch), {})['tracking'] = new_state
        config_store.save_config(self.config)

    def _on_worker_alert(self, alert_data: dict):
        """Display native desktop notification and store snapshot path for click action."""
        if not getattr(self.config, 'notifications_enabled', True):
            return

        ch = alert_data.get('channel', 1)
        now = time.monotonic()
        last_time = self._last_notification_times.get(ch, 0.0)
        cooldown = max(1.0, float(getattr(self.config, 'notification_cooldown', 5.0)))

        if now - last_time < cooldown:
            return  # Cooldown active

        self._last_notification_times[ch] = now
        snapshot_path = alert_data.get('snapshot_path')
        if snapshot_path:
            self._last_alert_snapshot_path = snapshot_path

        label = alert_data.get('label', 'Motion Detected')
        category = alert_data.get('category', 'motion')

        icon_prefix = "🚶" if category == "person" else ("🚗" if category == "vehicle" else ("🐾" if category == "animal" else "🏃"))
        title = f"{icon_prefix} Alert: Channel {ch}"
        message = f"{label}\n(Click to view snapshot)" if snapshot_path else label

        if hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.isVisible():
            self.tray_icon.showMessage(title, message, QSystemTrayIcon.MessageIcon.Information, 4000)

    def _show_grid(self):
        self._fullscreen_channel = None
        for tile in self.tiles:
            tile.show()

    def _on_disconnect(self):
        self._stop_all_streams()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        self.disconnected.emit()
        self.close()

    def _stop_all_streams(self):
        for worker in self.workers:
            if worker is not None:
                worker.stop()
        for worker in self.workers:
            if worker is not None:
                worker.wait(3000)
        self.workers = [None] * self.config.channels

    def closeEvent(self, event):
        if getattr(self.config, 'minimize_to_tray', True) and hasattr(self, 'tray_icon') and self.tray_icon and self.tray_icon.isVisible():
            event.ignore()
            self.hide()
            self.tray_icon.showMessage(
                'CamView',
                'CamView is running in the background. Surveillance active.',
                QSystemTrayIcon.MessageIcon.Information,
                2500
            )
        else:
            self._quit_application()
            super().closeEvent(event)

    def _quit_application(self):
        """Gracefully stop background streams and close the window."""
        self._stop_all_streams()
        if hasattr(self, '_uptime_timer') and self._uptime_timer.isActive():
            self._uptime_timer.stop()
        if hasattr(self, 'tray_icon') and self.tray_icon:
            self.tray_icon.hide()
        self.close()
