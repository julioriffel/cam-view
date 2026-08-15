"""CamView — DVR Viewer for Intelbras MHDX 1004.

Beautiful desktop application to view live camera feeds via RTSP.
"""

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont, QIcon

from src.styles.theme import get_global_stylesheet
from src.views.login_window import LoginWindow
from src.views.viewer_window import ViewerWindow
from src.core.connection import DVRConfig
from src.core.resource_path import get_asset_path


class CamViewApp:
    """Application controller managing window transitions."""

    def __init__(self):
        self.app = QApplication(sys.argv)
        self.app.setApplicationName("CamView")
        self.app.setOrganizationName("CamView")

        # Set application icon
        icon_path = get_asset_path("icon.jpg")
        if icon_path.exists():
            self.app.setWindowIcon(QIcon(str(icon_path)))

        # Apply global dark theme
        self.app.setStyleSheet(get_global_stylesheet())

        # Set default font
        font = QFont("Inter", 10)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)
        self.app.setFont(font)

        self.login_window: LoginWindow | None = None
        self.viewer_window: ViewerWindow | None = None

    def run(self) -> int:
        """Start the application."""
        self._show_login()
        return self.app.exec()

    def _show_login(self):
        """Display the login/connection screen."""
        self.login_window = LoginWindow()
        self.login_window.connection_successful.connect(self._on_connected)
        self.login_window.show()
        # Automatically attempt connection if a valid config is saved
        self.login_window.auto_connect()

    def _on_connected(self, config: DVRConfig):
        """Transition from login to viewer."""
        if self.login_window:
            self.login_window.close()
            self.login_window = None

        self.viewer_window = ViewerWindow(config)
        self.viewer_window.disconnected.connect(self._on_disconnected)
        self.viewer_window.show()

    def _on_disconnected(self):
        """Return to login screen on disconnect."""
        if self.viewer_window:
            self.viewer_window.close()
            self.viewer_window = None

        self._show_login()


def main():
    app = CamViewApp()
    sys.exit(app.run())


if __name__ == "__main__":
    main()
