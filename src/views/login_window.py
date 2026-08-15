"""Login / connection screen for the DVR Viewer."""

from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QSpinBox, QFrame,
    QGraphicsDropShadowEffect, QCheckBox,
)
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve, Signal, QThread
from PySide6.QtGui import QColor, QPainter, QLinearGradient

from src.core.connection import DVRConfig, test_connection
from src.styles.theme import Colors
from src.core import config_store


class ConnectionTester(QThread):
    """Runs connection test in background thread."""
    finished = Signal(bool, str)

    def __init__(self, config: DVRConfig):
        super().__init__()
        self.config = config

    def run(self):
        success, message = test_connection(self.config)
        self.finished.emit(success, message)


# ── Reusable style helpers ──────────────────────────────────────────

_FIELD_LABEL = f"""
    font-size: 11px;
    color: {Colors.TEXT_SECONDARY};
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 0;
    margin: 0 0 2px 2px;
"""

_INPUT_BOX = f"""
    background-color: rgba(255, 255, 255, 0.07);
    color: {Colors.TEXT_PRIMARY};
    border: 1px solid rgba(255, 255, 255, 0.10);
    border-radius: 8px;
    padding: 10px 12px;
    font-size: 13px;
"""

_INPUT_BOX_FOCUS = f"""
    border: 1px solid {Colors.BORDER_FOCUS};
    background-color: rgba(255, 255, 255, 0.10);
"""

_SPINBOX_STYLE = f"""
    QSpinBox {{
        {_INPUT_BOX}
    }}
    QSpinBox:focus {{
        {_INPUT_BOX_FOCUS}
    }}
    QSpinBox::up-button, QSpinBox::down-button {{
        background: transparent;
        border: none;
        width: 18px;
    }}
    QSpinBox::up-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-bottom: 5px solid {Colors.TEXT_SECONDARY};
    }}
    QSpinBox::down-arrow {{
        border-left: 4px solid transparent;
        border-right: 4px solid transparent;
        border-top: 5px solid {Colors.TEXT_SECONDARY};
    }}
"""

_LINE_EDIT_STYLE = f"""
    QLineEdit {{
        {_INPUT_BOX}
    }}
    QLineEdit:focus {{
        {_INPUT_BOX_FOCUS}
    }}
    QLineEdit:disabled {{
        color: {Colors.TEXT_MUTED};
        background-color: rgba(255, 255, 255, 0.02);
    }}
"""

_PRIMARY_BTN = f"""
    QPushButton {{
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {Colors.ACCENT}, stop:1 #6366f1
        );
        color: #ffffff;
        border: none;
        border-radius: 10px;
        padding: 14px 32px;
        font-size: 14px;
        font-weight: 700;
        letter-spacing: 0.5px;
    }}
    QPushButton:hover {{
        background-color: qlineargradient(
            x1:0, y1:0, x2:1, y2:0,
            stop:0 {Colors.ACCENT_HOVER}, stop:1 #818cf8
        );
    }}
    QPushButton:pressed {{
        background-color: {Colors.ACCENT_PRESSED};
    }}
    QPushButton:disabled {{
        background-color: rgba(74, 158, 255, 0.20);
        color: rgba(255, 255, 255, 0.30);
    }}
"""

_SECONDARY_BTN = f"""
    QPushButton {{
        background-color: transparent;
        color: {Colors.ACCENT};
        border: 1px solid rgba(74, 158, 255, 0.35);
        border-radius: 10px;
        padding: 10px 32px;
        font-size: 13px;
        font-weight: 600;
    }}
    QPushButton:hover {{
        background-color: rgba(74, 158, 255, 0.08);
        border-color: {Colors.ACCENT};
    }}
    QPushButton:pressed {{
        background-color: rgba(74, 158, 255, 0.15);
    }}
"""

_CARD_STYLE = """
    QFrame#loginCard {
        background-color: rgba(16, 18, 45, 0.92);
        border: 1px solid rgba(255, 255, 255, 0.07);
        border-radius: 20px;
    }
"""


_CHECKBOX_STYLE = f"""
    QCheckBox {{
        color: {Colors.TEXT_SECONDARY};
        font-size: 12px;
        background: transparent;
        border: none;
    }}
    QCheckBox::indicator {{
        width: 16px;
        height: 16px;
        border: 2px solid rgba(255, 255, 255, 0.2);
        border-radius: 4px;
        background: rgba(0, 0, 0, 0.2);
    }}
    QCheckBox::indicator:hover {{
        border-color: rgba(255, 255, 255, 0.4);
    }}
    QCheckBox::indicator:checked {{
        background-color: {Colors.ACCENT};
        border-color: {Colors.ACCENT};
    }}
"""


class LoginWindow(QMainWindow):
    """Beautiful login screen for DVR connection."""

    connection_successful = Signal(object)  # Emits DVRConfig on success

    def __init__(self):
        super().__init__()
        self.setWindowTitle('CamView — DVR Viewer')
        self.setFixedSize(520, 740)
        self._tester = None
        self._setup_ui()

    def paintEvent(self, event):
        """Paint gradient background."""
        painter = QPainter(self)
        gradient = QLinearGradient(0, 0, self.width(), self.height())
        gradient.setColorAt(0.0, QColor('#080b1f'))
        gradient.setColorAt(0.4, QColor('#0e1230'))
        gradient.setColorAt(1.0, QColor('#181840'))
        painter.fillRect(self.rect(), gradient)
        painter.end()

    def _make_label(self, text: str) -> QLabel:
        """Create a styled field label."""
        lbl = QLabel(text)
        lbl.setStyleSheet(_FIELD_LABEL)
        return lbl

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.setContentsMargins(40, 30, 40, 30)

        # ── Card Container ──
        card = QFrame()
        card.setObjectName('loginCard')
        card.setStyleSheet(_CARD_STYLE)
        card.setFixedWidth(430)

        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(80)
        shadow.setColor(QColor(0, 0, 0, 160))
        shadow.setOffset(0, 12)
        card.setGraphicsEffect(shadow)

        cl = QVBoxLayout(card)
        cl.setSpacing(10)
        cl.setContentsMargins(36, 32, 36, 28)

        # ── Header: Icon + Title ──
        header_icon = QLabel('⬤')
        header_icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header_icon.setStyleSheet(f"""
            font-size: 36px;
            color: {Colors.ACCENT};
            background: transparent;
            border: none;
            margin-bottom: 0;
        """)
        cl.addWidget(header_icon)

        title = QLabel('CamView')
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet(f"""
            font-size: 26px;
            font-weight: 700;
            color: {Colors.TEXT_PRIMARY};
            letter-spacing: 2px;
            background: transparent;
            border: none;
            margin: 0;
        """)
        cl.addWidget(title)

        subtitle = QLabel('Intelbras MHDX 1004')
        subtitle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle.setStyleSheet(f"""
            font-size: 11px;
            color: {Colors.TEXT_MUTED};
            background: transparent;
            border: none;
            margin-bottom: 8px;
            letter-spacing: 3px;
        """)
        cl.addWidget(subtitle)

        # ── Separator ──
        sep = QFrame()
        sep.setFixedHeight(1)
        sep.setStyleSheet('background: rgba(255,255,255,0.06); border: none;')
        cl.addWidget(sep)
        cl.addSpacing(6)

        # ── IP + Port Row ──
        ip_port = QHBoxLayout()
        ip_port.setSpacing(10)

        ip_col = QVBoxLayout()
        ip_col.setSpacing(4)
        ip_col.addWidget(self._make_label('DVR IP Address'))
        self.ip_input = QLineEdit('192.168.1.3')
        self.ip_input.setPlaceholderText('192.168.1.x')
        self.ip_input.setStyleSheet(_LINE_EDIT_STYLE)
        ip_col.addWidget(self.ip_input)

        port_col = QVBoxLayout()
        port_col.setSpacing(4)
        port_col.addWidget(self._make_label('Port'))
        self.port_input = QSpinBox()
        self.port_input.setRange(1, 65535)
        self.port_input.setValue(554)
        self.port_input.setFixedWidth(90)
        self.port_input.setStyleSheet(_SPINBOX_STYLE)
        port_col.addWidget(self.port_input)

        ip_port.addLayout(ip_col, 3)
        ip_port.addLayout(port_col, 1)
        cl.addLayout(ip_port)

        # ── Username ──
        cl.addWidget(self._make_label('Username'))
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText('admin')
        self.user_input.setStyleSheet(_LINE_EDIT_STYLE)
        cl.addWidget(self.user_input)

        # ── Password ──
        cl.addWidget(self._make_label('Password'))
        self.pass_input = QLineEdit()
        self.pass_input.setPlaceholderText('Enter password')
        self.pass_input.setEchoMode(QLineEdit.EchoMode.Password)
        self.pass_input.setStyleSheet(_LINE_EDIT_STYLE)
        cl.addWidget(self.pass_input)

        # ── Channels ──
        cl.addWidget(self._make_label('Channels'))
        self.channels_input = QSpinBox()
        self.channels_input.setRange(1, 16)
        self.channels_input.setValue(4)
        self.channels_input.setStyleSheet(_SPINBOX_STYLE)
        cl.addWidget(self.channels_input)

        # ── Save Config Checkbox ──
        self.save_checkbox = QCheckBox(" Remember login info")
        self.save_checkbox.setStyleSheet(_CHECKBOX_STYLE)
        cl.addWidget(self.save_checkbox)

        cl.addSpacing(4)

        # ── Status Message ──
        self.status_label = QLabel('')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setWordWrap(True)
        self.status_label.setFixedHeight(22)
        self.status_label.setStyleSheet(f"""
            font-size: 12px;
            color: {Colors.TEXT_SECONDARY};
            background: transparent;
            border: none;
        """)
        cl.addWidget(self.status_label)

        # ── Connect Button ──
        self.connect_btn = QPushButton('Connect to DVR')
        self.connect_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.connect_btn.setMinimumHeight(48)
        self.connect_btn.setStyleSheet(_PRIMARY_BTN)
        self.connect_btn.clicked.connect(self._on_connect)
        cl.addWidget(self.connect_btn)

        # ── Test Connection Button ──
        self.test_btn = QPushButton('Test Connection')
        self.test_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.test_btn.setMinimumHeight(38)
        self.test_btn.setStyleSheet(_SECONDARY_BTN)
        self.test_btn.clicked.connect(self._on_test_connection)
        cl.addWidget(self.test_btn)

        # ── Footer ──
        footer = QLabel('RTSP Protocol  •  Port 554')
        footer.setAlignment(Qt.AlignmentFlag.AlignCenter)
        footer.setStyleSheet(f"""
            font-size: 10px;
            color: {Colors.TEXT_MUTED};
            background: transparent;
            border: none;
            margin-top: 6px;
        """)
        cl.addWidget(footer)

        main_layout.addWidget(card, alignment=Qt.AlignmentFlag.AlignCenter)

        # ── Load saved config ──
        saved_config = config_store.load_config()
        if saved_config:
            self.ip_input.setText(saved_config.host)
            self.port_input.setValue(saved_config.port)
            self.user_input.setText(saved_config.username)
            self.pass_input.setText(saved_config.password)
            self.channels_input.setValue(saved_config.channels)
            self.save_checkbox.setChecked(True)
        else:
            self.user_input.setText("admin")

        # ── Fade-in animation ──
        self.setWindowOpacity(0.0)
        self._fade_anim = QPropertyAnimation(self, b'windowOpacity')
        self._fade_anim.setDuration(600)
        self._fade_anim.setStartValue(0.0)
        self._fade_anim.setEndValue(1.0)
        self._fade_anim.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._fade_anim.start()

    def auto_connect(self):
        """Programmatically trigger connection if a config is saved."""
        if self.save_checkbox.isChecked() and config_store.has_saved_config():
            self._on_connect()

    # ── Config & Actions ──────────────────────────────────────────

    def _build_config(self) -> DVRConfig:
        existing = config_store.load_config() or DVRConfig()
        existing.host = self.ip_input.text().strip()
        existing.port = self.port_input.value()
        existing.username = self.user_input.text().strip()
        existing.password = self.pass_input.text()
        existing.channels = self.channels_input.value()
        if not hasattr(existing, 'subtype') or existing.subtype is None:
            existing.subtype = 1
        return existing

    def _on_test_connection(self):
        self._set_loading(True, 'Testing connection...')
        config = self._build_config()
        self._tester = ConnectionTester(config)
        self._tester.finished.connect(self._on_test_result)
        self._tester.start()

    def _on_test_result(self, success: bool, message: str):
        color = Colors.SUCCESS if success else Colors.ERROR
        self.status_label.setStyleSheet(f'font-size: 12px; color: {color}; background: transparent; border: none;')
        self.status_label.setText(message)
        self._set_loading(False)

    def _on_connect(self):
        config = self._build_config()
        if not config.host:
            self.status_label.setStyleSheet(f'font-size: 12px; color: {Colors.ERROR}; background: transparent; border: none;')
            self.status_label.setText('Please enter a valid IP address.')
            return

        self._set_loading(True, 'Connecting to DVR...')
        self._tester = ConnectionTester(config)
        self._tester.finished.connect(lambda ok, msg: self._on_connect_result(ok, msg, config))
        self._tester.start()

    def _on_connect_result(self, success: bool, message: str, config: DVRConfig):
        self._set_loading(False)
        if success:
            if self.save_checkbox.isChecked():
                config_store.save_config(config)
            else:
                config_store.delete_config()
            self.connection_successful.emit(config)
        else:
            self.status_label.setStyleSheet(f'font-size: 12px; color: {Colors.ERROR}; background: transparent; border: none;')
            self.status_label.setText(message)

    def _set_loading(self, loading: bool, message: str = ''):
        self.connect_btn.setEnabled(not loading)
        self.test_btn.setEnabled(not loading)
        if loading:
            self.connect_btn.setText('Connecting...')
            self.status_label.setStyleSheet(f'font-size: 12px; color: {Colors.ACCENT}; background: transparent; border: none;')
            self.status_label.setText(message)
        else:
            self.connect_btn.setText('Connect to DVR')
