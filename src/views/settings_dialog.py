from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QCheckBox, 
    QSlider, QSpinBox, QDoubleSpinBox, QPushButton, QFrame, QGroupBox,
    QFileDialog, QTabWidget, QWidget
)
from PySide6.QtCore import Qt, Signal
from src.core.connection import DVRConfig
from src.styles.theme import Colors


class TrackingSettingsDialog(QDialog):
    """Dialog for configuring motion tracking, Smart Vision AI, alerts, and storage across tabs."""
    
    settings_saved = Signal(DVRConfig)

    def __init__(self, config: DVRConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.setWindowTitle("Settings")
        self.setMinimumWidth(480)
        self.resize(500, 440)
        self.setStyleSheet(f"""
            QDialog {{ background: {Colors.BG_PRIMARY}; }}
            QLabel {{ color: {Colors.TEXT_PRIMARY}; font-size: 13px; }}
            QGroupBox {{
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 14px;
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 6px;
                left: 10px;
            }}
            QCheckBox {{ color: {Colors.TEXT_PRIMARY}; font-size: 13px; }}
            QSpinBox, QDoubleSpinBox {{
                background: {Colors.BG_INPUT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 4px;
                padding: 4px 8px;
            }}
            QTabWidget::pane {{
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                background: rgba(14, 18, 44, 0.75);
                padding: 12px;
            }}
            QTabBar::tab {{
                background: rgba(255, 255, 255, 0.03);
                color: {Colors.TEXT_SECONDARY};
                border: 1px solid {Colors.BORDER};
                border-bottom: none;
                border-top-left-radius: 6px;
                border-top-right-radius: 6px;
                padding: 8px 14px;
                margin-right: 3px;
                font-size: 12px;
                font-weight: 600;
            }}
            QTabBar::tab:selected {{
                background: {Colors.ACCENT};
                color: #ffffff;
                border-color: {Colors.ACCENT};
            }}
            QTabBar::tab:hover:!selected {{
                background: rgba(255, 255, 255, 0.08);
                color: {Colors.TEXT_PRIMARY};
            }}
            QPushButton {{
                background: {Colors.BG_INPUT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 16px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background: rgba(255, 255, 255, 0.05);
            }}
            QPushButton#saveBtn {{
                background: {Colors.ACCENT};
                border: 1px solid {Colors.ACCENT};
            }}
            QPushButton#saveBtn:hover {{
                background: #60a5fa;
            }}
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(12)
        main_layout.setContentsMargins(14, 14, 14, 14)

        tabs = QTabWidget(self)

        # ═════════════════════════════════════════════════════════════
        # TAB 1: 🏃 Motion & Snapshots
        # ═════════════════════════════════════════════════════════════
        tab_motion = QWidget()
        tab_motion_layout = QVBoxLayout(tab_motion)
        tab_motion_layout.setSpacing(12)
        tab_motion_layout.setContentsMargins(4, 8, 4, 4)

        # Algorithm Group
        group_algo = QGroupBox("Motion Detection Algorithm")
        algo_layout = QVBoxLayout(group_algo)
        algo_layout.setSpacing(10)

        self.cb_filter = QCheckBox("Enable Morphological Noise Filter")
        self.cb_filter.setToolTip("Removes thin streaks like flying bugs or rain")
        self.cb_filter.setChecked(self.config.tracking_filter_enabled)
        algo_layout.addWidget(self.cb_filter)

        # Minimum Area
        area_layout = QVBoxLayout()
        area_layout.setSpacing(3)
        area_label_layout = QHBoxLayout()
        area_label = QLabel("Minimum Object Area (pixels):")
        self.spin_area = QSpinBox()
        self.spin_area.setRange(100, 20000)
        self.spin_area.setSingleStep(100)
        self.spin_area.setValue(self.config.tracking_min_area)

        self.slider_area = QSlider(Qt.Orientation.Horizontal)
        self.slider_area.setRange(100, 20000)
        self.slider_area.setSingleStep(100)
        self.slider_area.setValue(self.config.tracking_min_area)

        self.spin_area.valueChanged.connect(self.slider_area.setValue)
        self.slider_area.valueChanged.connect(self.spin_area.setValue)

        area_label_layout.addWidget(area_label)
        area_label_layout.addStretch()
        area_label_layout.addWidget(self.spin_area)
        area_layout.addLayout(area_label_layout)
        area_layout.addWidget(self.slider_area)
        algo_layout.addLayout(area_layout)

        # Persistence
        pers_layout = QVBoxLayout()
        pers_layout.setSpacing(3)
        pers_label_layout = QHBoxLayout()
        pers_label = QLabel("Temporal Persistence (frames):")
        self.spin_pers = QSpinBox()
        self.spin_pers.setRange(1, 30)
        self.spin_pers.setValue(self.config.tracking_persistence)

        self.slider_pers = QSlider(Qt.Orientation.Horizontal)
        self.slider_pers.setRange(1, 30)
        self.slider_pers.setValue(self.config.tracking_persistence)

        self.spin_pers.valueChanged.connect(self.slider_pers.setValue)
        self.slider_pers.valueChanged.connect(self.spin_pers.setValue)

        pers_label_layout.addWidget(pers_label)
        pers_label_layout.addStretch()
        pers_label_layout.addWidget(self.spin_pers)
        pers_layout.addLayout(pers_label_layout)
        pers_layout.addWidget(self.slider_pers)
        algo_layout.addLayout(pers_layout)

        tab_motion_layout.addWidget(group_algo)

        # Snapshot Group
        group_snapshot = QGroupBox("Motion Snapshots")
        snapshot_layout = QVBoxLayout(group_snapshot)
        snapshot_layout.setSpacing(8)

        self.cb_snapshot = QCheckBox("Automatically capture snapshot on motion")
        self.cb_snapshot.setChecked(self.config.snapshot_on_motion)
        snapshot_layout.addWidget(self.cb_snapshot)

        interval_layout = QVBoxLayout()
        interval_layout.setSpacing(3)
        interval_label_layout = QHBoxLayout()
        interval_label = QLabel("Snapshot Interval (seconds):")

        self.spin_interval = QDoubleSpinBox()
        self.spin_interval.setRange(0.5, 60.0)
        self.spin_interval.setSingleStep(0.5)
        self.spin_interval.setDecimals(1)
        self.spin_interval.setSuffix(" s")
        self.spin_interval.setValue(self.config.snapshot_interval)

        self.slider_interval = QSlider(Qt.Orientation.Horizontal)
        self.slider_interval.setRange(5, 600)
        self.slider_interval.setSingleStep(5)
        self.slider_interval.setValue(int(self.config.snapshot_interval * 10))

        self.spin_interval.valueChanged.connect(lambda val: self.slider_interval.setValue(int(val * 10)))
        self.slider_interval.valueChanged.connect(lambda val: self.spin_interval.setValue(val / 10.0))

        interval_label_layout.addWidget(interval_label)
        interval_label_layout.addStretch()
        interval_label_layout.addWidget(self.spin_interval)
        interval_layout.addLayout(interval_label_layout)
        interval_layout.addWidget(self.slider_interval)
        snapshot_layout.addLayout(interval_layout)

        def _toggle_interval_widgets(enabled: bool):
            self.spin_interval.setEnabled(enabled)
            self.slider_interval.setEnabled(enabled)
            interval_label.setEnabled(enabled)

        self.cb_snapshot.toggled.connect(_toggle_interval_widgets)
        _toggle_interval_widgets(self.config.snapshot_on_motion)

        tab_motion_layout.addWidget(group_snapshot)
        tab_motion_layout.addStretch()
        tabs.addTab(tab_motion, "🏃 Motion")

        # ═════════════════════════════════════════════════════════════
        # TAB 2: 🧠 Smart Vision (AI)
        # ═════════════════════════════════════════════════════════════
        tab_ai = QWidget()
        tab_ai_layout = QVBoxLayout(tab_ai)
        tab_ai_layout.setSpacing(12)
        tab_ai_layout.setContentsMargins(4, 8, 4, 4)

        group_ai = QGroupBox("Local AI Object Recognition (CPU)")
        ai_layout = QVBoxLayout(group_ai)
        ai_layout.setSpacing(10)

        self.cb_ai_enabled = QCheckBox("Enable Smart Vision AI Detection")
        self.cb_ai_enabled.setChecked(self.config.ai_enabled)
        ai_layout.addWidget(self.cb_ai_enabled)

        # Confidence Slider
        conf_layout = QVBoxLayout()
        conf_layout.setSpacing(3)
        conf_label_layout = QHBoxLayout()
        conf_label = QLabel("Confidence Threshold:")

        self.spin_conf = QSpinBox()
        self.spin_conf.setRange(15, 95)
        self.spin_conf.setSingleStep(5)
        self.spin_conf.setSuffix(" %")
        self.spin_conf.setValue(int(self.config.ai_confidence_threshold * 100))

        self.slider_conf = QSlider(Qt.Orientation.Horizontal)
        self.slider_conf.setRange(15, 95)
        self.slider_conf.setSingleStep(5)
        self.slider_conf.setValue(int(self.config.ai_confidence_threshold * 100))

        self.spin_conf.valueChanged.connect(self.slider_conf.setValue)
        self.slider_conf.valueChanged.connect(self.spin_conf.setValue)

        conf_label_layout.addWidget(conf_label)
        conf_label_layout.addStretch()
        conf_label_layout.addWidget(self.spin_conf)
        conf_layout.addLayout(conf_label_layout)
        conf_layout.addWidget(self.slider_conf)
        ai_layout.addLayout(conf_layout)

        # Target Categories
        cat_label = QLabel("Target Categories:")
        cat_label.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-weight: 600; font-size: 12px; margin-top: 2px;")
        ai_layout.addWidget(cat_label)

        cat_boxes_layout = QVBoxLayout()
        cat_boxes_layout.setSpacing(6)
        cat_boxes_layout.setContentsMargins(8, 0, 0, 0)

        self.cb_ai_person = QCheckBox("🚶 People  (Person)")
        self.cb_ai_person.setChecked(self.config.ai_detect_person)
        cat_boxes_layout.addWidget(self.cb_ai_person)

        self.cb_ai_vehicles = QCheckBox("🚗 Vehicles  (Car, Motorcycle, Bicycle, Truck, Bus)")
        self.cb_ai_vehicles.setChecked(self.config.ai_detect_vehicles)
        cat_boxes_layout.addWidget(self.cb_ai_vehicles)

        self.cb_ai_animals = QCheckBox("🐾 Animals  (Dog, Cat, Bird)")
        self.cb_ai_animals.setChecked(self.config.ai_detect_animals)
        cat_boxes_layout.addWidget(self.cb_ai_animals)

        ai_layout.addLayout(cat_boxes_layout)

        self.cb_ai_filter_snapshots = QCheckBox("Only capture snapshots if recognized targets are detected")
        self.cb_ai_filter_snapshots.setChecked(self.config.ai_filter_snapshots)
        self.cb_ai_filter_snapshots.setStyleSheet(f"color: {Colors.ACCENT}; margin-top: 4px;")
        ai_layout.addWidget(self.cb_ai_filter_snapshots)

        def _toggle_ai_widgets(enabled: bool):
            conf_label.setEnabled(enabled)
            self.spin_conf.setEnabled(enabled)
            self.slider_conf.setEnabled(enabled)
            cat_label.setEnabled(enabled)
            self.cb_ai_person.setEnabled(enabled)
            self.cb_ai_vehicles.setEnabled(enabled)
            self.cb_ai_animals.setEnabled(enabled)
            self.cb_ai_filter_snapshots.setEnabled(enabled)

        self.cb_ai_enabled.toggled.connect(_toggle_ai_widgets)
        _toggle_ai_widgets(self.config.ai_enabled)

        tab_ai_layout.addWidget(group_ai)
        tab_ai_layout.addStretch()
        tabs.addTab(tab_ai, "🧠 Smart Vision")

        # ═════════════════════════════════════════════════════════════
        # TAB 3: 🔔 Alerts & System Tray
        # ═════════════════════════════════════════════════════════════
        tab_notif = QWidget()
        tab_notif_layout = QVBoxLayout(tab_notif)
        tab_notif_layout.setSpacing(12)
        tab_notif_layout.setContentsMargins(4, 8, 4, 4)

        group_notif = QGroupBox("Desktop Notifications & System Tray")
        notif_layout = QVBoxLayout(group_notif)
        notif_layout.setSpacing(10)

        self.cb_notif_enabled = QCheckBox("Show native desktop notifications on motion / AI alerts")
        self.cb_notif_enabled.setChecked(getattr(self.config, 'notifications_enabled', True))
        notif_layout.addWidget(self.cb_notif_enabled)

        self.cb_minimize_tray = QCheckBox("Minimize to system tray on close (keep surveillance running)")
        self.cb_minimize_tray.setChecked(getattr(self.config, 'minimize_to_tray', True))
        notif_layout.addWidget(self.cb_minimize_tray)

        cooldown_layout = QVBoxLayout()
        cooldown_layout.setSpacing(3)
        cooldown_label_layout = QHBoxLayout()
        cooldown_label = QLabel("Notification Cooldown (seconds between alerts):")

        self.spin_notif_cooldown = QSpinBox()
        self.spin_notif_cooldown.setRange(1, 60)
        self.spin_notif_cooldown.setSingleStep(1)
        self.spin_notif_cooldown.setSuffix(" s")
        self.spin_notif_cooldown.setValue(int(getattr(self.config, 'notification_cooldown', 5.0)))

        self.slider_notif_cooldown = QSlider(Qt.Orientation.Horizontal)
        self.slider_notif_cooldown.setRange(1, 60)
        self.slider_notif_cooldown.setValue(int(getattr(self.config, 'notification_cooldown', 5.0)))

        self.spin_notif_cooldown.valueChanged.connect(self.slider_notif_cooldown.setValue)
        self.slider_notif_cooldown.valueChanged.connect(self.spin_notif_cooldown.setValue)

        cooldown_label_layout.addWidget(cooldown_label)
        cooldown_label_layout.addStretch()
        cooldown_label_layout.addWidget(self.spin_notif_cooldown)
        cooldown_layout.addLayout(cooldown_label_layout)
        cooldown_layout.addWidget(self.slider_notif_cooldown)
        notif_layout.addLayout(cooldown_layout)

        def _toggle_notif_cooldown(enabled: bool):
            cooldown_label.setEnabled(enabled)
            self.spin_notif_cooldown.setEnabled(enabled)
            self.slider_notif_cooldown.setEnabled(enabled)

        self.cb_notif_enabled.toggled.connect(_toggle_notif_cooldown)
        _toggle_notif_cooldown(getattr(self.config, 'notifications_enabled', True))

        tab_notif_layout.addWidget(group_notif)
        tab_notif_layout.addStretch()
        tabs.addTab(tab_notif, "🔔 Alerts & Tray")

        # ═════════════════════════════════════════════════════════════
        # TAB 4: 💾 Storage
        # ═════════════════════════════════════════════════════════════
        tab_storage = QWidget()
        tab_storage_layout = QVBoxLayout(tab_storage)
        tab_storage_layout.setSpacing(12)
        tab_storage_layout.setContentsMargins(4, 8, 4, 4)

        storage_group = QGroupBox("Snapshot Storage Directory")
        storage_layout = QVBoxLayout(storage_group)
        storage_layout.setSpacing(10)

        folder_desc = QLabel("Directory where automatic motion and target snapshots are saved:")
        folder_desc.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px;")
        storage_layout.addWidget(folder_desc)

        folder_layout = QHBoxLayout()
        self.folder_label = QLabel(self.config.save_folder)
        self.folder_label.setStyleSheet(f"color: {Colors.ACCENT}; font-family: monospace; font-size: 12px; background: rgba(0,0,0,0.3); padding: 6px 10px; border-radius: 4px; border: 1px solid {Colors.BORDER};")

        btn_browse = QPushButton("Browse...")
        btn_browse.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_browse.clicked.connect(self._select_folder)

        folder_layout.addWidget(self.folder_label, stretch=1)
        folder_layout.addWidget(btn_browse)
        storage_layout.addLayout(folder_layout)

        tab_storage_layout.addWidget(storage_group)
        tab_storage_layout.addStretch()
        tabs.addTab(tab_storage, "💾 Storage")

        main_layout.addWidget(tabs)

        # ── Action Buttons ───────────────────────────────────────────
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        btn_cancel = QPushButton("Cancel")
        btn_cancel.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_cancel.clicked.connect(self.reject)

        btn_save = QPushButton("Save Settings")
        btn_save.setObjectName("saveBtn")
        btn_save.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_save.clicked.connect(self._on_save)

        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(btn_save)

        main_layout.addLayout(btn_layout)

    def _select_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Snapshot Save Folder", self.config.save_folder)
        if folder:
            self.folder_label.setText(folder)
            self._pending_folder = folder
        else:
            self._pending_folder = None

    def _on_save(self):
        # Motion settings
        self.config.tracking_filter_enabled = self.cb_filter.isChecked()
        self.config.tracking_min_area = self.spin_area.value()
        self.config.tracking_persistence = self.spin_pers.value()
        self.config.snapshot_on_motion = self.cb_snapshot.isChecked()
        self.config.snapshot_interval = round(self.spin_interval.value(), 1)
        
        # AI settings
        self.config.ai_enabled = self.cb_ai_enabled.isChecked()
        self.config.ai_confidence_threshold = round(self.spin_conf.value() / 100.0, 2)
        self.config.ai_detect_person = self.cb_ai_person.isChecked()
        self.config.ai_detect_vehicles = self.cb_ai_vehicles.isChecked()
        self.config.ai_detect_animals = self.cb_ai_animals.isChecked()
        self.config.ai_filter_snapshots = self.cb_ai_filter_snapshots.isChecked()

        # Notification & Tray settings
        self.config.notifications_enabled = self.cb_notif_enabled.isChecked()
        self.config.minimize_to_tray = self.cb_minimize_tray.isChecked()
        self.config.notification_cooldown = float(self.spin_notif_cooldown.value())

        if hasattr(self, '_pending_folder') and self._pending_folder:
            self.config.save_folder = self._pending_folder
            
        self.settings_saved.emit(self.config)
        self.accept()
