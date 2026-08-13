"""
Premium dark theme for the DVR Viewer application.

Provides a cohesive design system with color constants, a global Qt Style Sheet,
and component-specific style helpers for login cards, camera tiles, and overlays.
"""


class Colors:
    """Design-system color palette for the DVR Viewer UI."""

    BG_PRIMARY = '#0a0e27'
    BG_SECONDARY = '#1a1a3e'
    BG_CARD = 'rgba(30, 30, 60, 0.85)'
    BG_INPUT = 'rgba(255, 255, 255, 0.06)'

    ACCENT = '#4a9eff'
    ACCENT_HOVER = '#6bb3ff'
    ACCENT_PRESSED = '#3a8eef'

    TEXT_PRIMARY = '#e8eaf6'
    TEXT_SECONDARY = '#9ea7c0'
    TEXT_MUTED = '#5a6380'

    SUCCESS = '#4caf50'
    ERROR = '#ef5350'
    WARNING = '#ffa726'

    BORDER = 'rgba(255, 255, 255, 0.08)'
    BORDER_FOCUS = 'rgba(74, 158, 255, 0.5)'


def get_global_stylesheet() -> str:
    """Return the application-wide Qt Style Sheet.

    Covers every standard widget used in the DVR Viewer with consistent
    dark-theme styling, smooth hover/pressed transitions, and frosted-glass
    toolbar effects.
    """
    c = Colors
    return f"""
        /* ── Base Widgets ─────────────────────────────────────── */
        QMainWindow {{
            background-color: {c.BG_PRIMARY};
        }}

        QWidget {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
            font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            font-size: 14px;
        }}

        /* ── QLineEdit ────────────────────────────────────────── */
        QLineEdit {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
            selection-background-color: {c.ACCENT};
            selection-color: #ffffff;
        }}

        QLineEdit:focus {{
            border: 1px solid {c.BORDER_FOCUS};
            background-color: rgba(255, 255, 255, 0.08);
        }}

        QLineEdit:disabled {{
            color: {c.TEXT_MUTED};
            background-color: rgba(255, 255, 255, 0.02);
        }}

        /* ── QPushButton (Primary / Accent) ───────────────────── */
        QPushButton {{
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {c.ACCENT}, stop:1 {c.ACCENT_PRESSED}
            );
            color: #ffffff;
            border: none;
            border-radius: 10px;
            padding: 12px 32px;
            font-size: 14px;
            font-weight: 600;
        }}

        QPushButton:hover {{
            background-color: qlineargradient(
                x1:0, y1:0, x2:1, y2:1,
                stop:0 {c.ACCENT_HOVER}, stop:1 {c.ACCENT}
            );
        }}

        QPushButton:pressed {{
            background-color: {c.ACCENT_PRESSED};
        }}

        QPushButton:disabled {{
            background-color: rgba(74, 158, 255, 0.25);
            color: rgba(255, 255, 255, 0.35);
        }}

        /* ── QPushButton#secondaryButton (Outline style) ────────── */
        QPushButton#secondaryButton {{
            background-color: transparent;
            color: {c.ACCENT};
            border: 1px solid {c.ACCENT};
            border-radius: 10px;
            padding: 12px 32px;
            font-size: 14px;
            font-weight: 600;
        }}

        QPushButton#secondaryButton:hover {{
            background-color: rgba(74, 158, 255, 0.10);
            border-color: {c.ACCENT_HOVER};
            color: {c.ACCENT_HOVER};
        }}

        QPushButton#secondaryButton:pressed {{
            background-color: rgba(74, 158, 255, 0.18);
            border-color: {c.ACCENT_PRESSED};
        }}

        /* ── QLabel ───────────────────────────────────────────── */
        QLabel {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
            border: none;
            font-size: 14px;
        }}

        /* ── QComboBox ────────────────────────────────────────── */
        QComboBox {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
            min-width: 120px;
        }}

        QComboBox:focus {{
            border: 1px solid {c.BORDER_FOCUS};
        }}

        QComboBox::drop-down {{
            subcontrol-origin: padding;
            subcontrol-position: top right;
            width: 30px;
            border-left: 1px solid {c.BORDER};
            border-top-right-radius: 8px;
            border-bottom-right-radius: 8px;
        }}

        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c.TEXT_SECONDARY};
            margin-right: 8px;
        }}

        QComboBox QAbstractItemView {{
            background-color: {c.BG_SECONDARY};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 6px;
            selection-background-color: {c.ACCENT};
            selection-color: #ffffff;
            outline: none;
        }}

        /* ── QSpinBox ─────────────────────────────────────────── */
        QSpinBox {{
            background-color: {c.BG_INPUT};
            color: {c.TEXT_PRIMARY};
            border: 1px solid {c.BORDER};
            border-radius: 8px;
            padding: 12px;
            font-size: 14px;
        }}

        QSpinBox:focus {{
            border: 1px solid {c.BORDER_FOCUS};
        }}

        QSpinBox::up-button, QSpinBox::down-button {{
            background-color: transparent;
            border: none;
            width: 20px;
        }}

        QSpinBox::up-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-bottom: 6px solid {c.TEXT_SECONDARY};
        }}

        QSpinBox::down-arrow {{
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {c.TEXT_SECONDARY};
        }}

        /* ── QToolBar ─────────────────────────────────────────── */
        QToolBar {{
            background-color: rgba(10, 14, 39, 0.80);
            border-bottom: 1px solid {c.BORDER};
            padding: 6px 12px;
            spacing: 8px;
        }}

        QToolBar::separator {{
            width: 1px;
            background-color: {c.BORDER};
            margin: 4px 8px;
        }}

        QToolBar QToolButton {{
            background-color: transparent;
            color: {c.TEXT_SECONDARY};
            border: none;
            border-radius: 6px;
            padding: 6px 10px;
            font-size: 13px;
        }}

        QToolBar QToolButton:hover {{
            background-color: rgba(255, 255, 255, 0.06);
            color: {c.TEXT_PRIMARY};
        }}

        /* ── QStatusBar ───────────────────────────────────────── */
        QStatusBar {{
            background-color: {c.BG_SECONDARY};
            color: {c.TEXT_SECONDARY};
            border-top: 1px solid {c.BORDER};
            font-size: 12px;
            padding: 4px 12px;
        }}

        QStatusBar::item {{
            border: none;
        }}

        /* ── QCheckBox ────────────────────────────────────────── */
        QCheckBox {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
            spacing: 8px;
            font-size: 14px;
        }}

        QCheckBox::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {c.TEXT_MUTED};
            border-radius: 4px;
            background-color: transparent;
        }}

        QCheckBox::indicator:hover {{
            border-color: {c.ACCENT};
        }}

        QCheckBox::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
        }}

        /* ── QRadioButton ─────────────────────────────────────── */
        QRadioButton {{
            background-color: transparent;
            color: {c.TEXT_PRIMARY};
            spacing: 8px;
            font-size: 14px;
        }}

        QRadioButton::indicator {{
            width: 20px;
            height: 20px;
            border: 2px solid {c.TEXT_MUTED};
            border-radius: 11px;
            background-color: transparent;
        }}

        QRadioButton::indicator:hover {{
            border-color: {c.ACCENT};
        }}

        QRadioButton::indicator:checked {{
            background-color: {c.ACCENT};
            border-color: {c.ACCENT};
        }}

        /* ── Scrollbars ───────────────────────────────────────── */
        QScrollBar:vertical {{
            background-color: transparent;
            width: 8px;
            margin: 4px 2px;
        }}

        QScrollBar::handle:vertical {{
            background-color: {c.TEXT_MUTED};
            border-radius: 4px;
            min-height: 30px;
        }}

        QScrollBar::handle:vertical:hover {{
            background-color: {c.ACCENT};
        }}

        QScrollBar::add-line:vertical,
        QScrollBar::sub-line:vertical {{
            height: 0px;
        }}

        QScrollBar::add-page:vertical,
        QScrollBar::sub-page:vertical {{
            background: none;
        }}

        QScrollBar:horizontal {{
            background-color: transparent;
            height: 8px;
            margin: 2px 4px;
        }}

        QScrollBar::handle:horizontal {{
            background-color: {c.TEXT_MUTED};
            border-radius: 4px;
            min-width: 30px;
        }}

        QScrollBar::handle:horizontal:hover {{
            background-color: {c.ACCENT};
        }}

        QScrollBar::add-line:horizontal,
        QScrollBar::sub-line:horizontal {{
            width: 0px;
        }}

        QScrollBar::add-page:horizontal,
        QScrollBar::sub-page:horizontal {{
            background: none;
        }}
    """


def get_login_card_style() -> str:
    """Return the QSS for the login card container widget.

    Produces a floating-card effect with rounded corners, a subtle border,
    and a deeply tinted translucent background.
    """
    return """
        QFrame#loginCard {
            background-color: rgba(20, 20, 50, 0.9);
            border: 1px solid rgba(255, 255, 255, 0.08);
            border-radius: 20px;
            padding: 40px;
        }
    """


def get_camera_tile_style() -> str:
    """Return the QSS for individual camera feed tile widgets."""
    return """
        background-color: #0d1117;
        border: 1px solid rgba(255, 255, 255, 0.06);
        border-radius: 8px;
    """


def get_overlay_label_style() -> str:
    """Return the QSS for text overlay labels rendered on top of camera tiles."""
    return """
        background-color: rgba(0, 0, 0, 0.55);
        color: #ffffff;
        font-size: 11px;
        font-weight: 500;
        border-radius: 4px;
        padding: 3px 8px;
    """
