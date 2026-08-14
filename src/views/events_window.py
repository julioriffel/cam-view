"""Event Search and AI Object Statistics Window with Export capabilities."""

import csv
import json
import shutil
import time
from datetime import datetime, timedelta
from pathlib import Path

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QComboBox, QTableWidget, QTableWidgetItem, QHeaderView,
    QFrame, QMessageBox, QWidget, QAbstractItemView, QFileDialog
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon, QColor, QDesktopServices

from src.core.event_db import EventDatabase
from src.core.connection import DVRConfig
from src.styles.theme import Colors


class EventsStatsWindow(QDialog):
    """Search, analytics, and export dashboard for AI object detections."""

    def __init__(self, config: DVRConfig, parent=None):
        super().__init__(parent)
        self.config = config
        self.db = EventDatabase.get_instance()

        self.setWindowTitle("AI Object Detection History & Statistics")
        self.setMinimumSize(960, 700)
        self.resize(1060, 760)

        self._init_styles()
        self._init_ui()
        self._load_data()

    def _init_styles(self):
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.BG_PRIMARY};
            }}
            QLabel {{
                color: {Colors.TEXT_PRIMARY};
                font-family: 'Segoe UI', 'Roboto', 'Arial', sans-serif;
            }}
            QComboBox {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 6px 12px;
                font-size: 13px;
                min-width: 130px;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.BG_SECONDARY};
                color: {Colors.TEXT_PRIMARY};
                selection-background-color: {Colors.ACCENT};
                border: 1px solid {Colors.BORDER};
            }}
            QPushButton {{
                background-color: {Colors.BG_INPUT};
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 6px;
                padding: 7px 16px;
                font-size: 13px;
                font-weight: 600;
            }}
            QPushButton:hover {{
                background-color: rgba(255, 255, 255, 0.08);
                border-color: rgba(255, 255, 255, 0.2);
            }}
            QPushButton#primaryBtn {{
                background-color: {Colors.ACCENT};
                border-color: {Colors.ACCENT};
                color: #ffffff;
            }}
            QPushButton#primaryBtn:hover {{
                background-color: {Colors.ACCENT_HOVER};
            }}
            QPushButton#exportBtn {{
                background-color: qlineargradient(
                    x1:0, y1:0, x2:1, y2:1,
                    stop:0 #22c55e, stop:1 #16a34a
                );
                border: none;
                color: #ffffff;
            }}
            QPushButton#exportBtn:hover {{
                background-color: #4ade80;
            }}
            QPushButton#dangerBtn {{
                background-color: rgba(239, 83, 80, 0.15);
                border-color: rgba(239, 83, 80, 0.4);
                color: {Colors.ERROR};
            }}
            QPushButton#dangerBtn:hover {{
                background-color: rgba(239, 83, 80, 0.30);
            }}
            QPushButton#subtleBtn {{
                background-color: transparent;
                border: 1px solid rgba(255, 255, 255, 0.1);
                color: {Colors.TEXT_SECONDARY};
                padding: 4px 10px;
                font-size: 11px;
            }}
            QPushButton#subtleBtn:hover {{
                background-color: rgba(255, 255, 255, 0.05);
                color: {Colors.TEXT_PRIMARY};
            }}
            QTableWidget {{
                background-color: rgba(14, 18, 44, 0.85);
                color: {Colors.TEXT_PRIMARY};
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                gridline-color: rgba(255, 255, 255, 0.05);
                font-size: 13px;
                selection-background-color: rgba(74, 158, 255, 0.30);
                selection-color: #ffffff;
            }}
            QHeaderView::section {{
                background-color: rgba(20, 24, 55, 0.95);
                color: {Colors.TEXT_SECONDARY};
                font-weight: 600;
                font-size: 12px;
                padding: 6px 8px;
                border: none;
                border-bottom: 1px solid {Colors.BORDER};
            }}
            QFrame#statCard {{
                background-color: rgba(20, 26, 60, 0.75);
                border: 1px solid {Colors.BORDER};
                border-radius: 8px;
                padding: 12px;
            }}
        """)

    def _init_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(14)
        main_layout.setContentsMargins(18, 18, 18, 18)

        # ── 1. Top Filter Controls ───────────────────────────────────
        filter_bar = QHBoxLayout()
        filter_bar.setSpacing(10)

        # Channel filter
        ch_label = QLabel("Channel:")
        self.combo_channel = QComboBox()
        self.combo_channel.addItem("All Channels", None)
        for ch in range(1, self.config.channels + 1):
            self.combo_channel.addItem(f"Channel {ch}", ch)
        self.combo_channel.currentIndexChanged.connect(self._load_data)

        # Category filter
        cat_label = QLabel("Category:")
        self.combo_category = QComboBox()
        self.combo_category.addItem("All Categories", "all")
        self.combo_category.addItem("🚶 People", "person")
        self.combo_category.addItem("🚗 Vehicles", "vehicle")
        self.combo_category.addItem("🐾 Animals", "animal")
        self.combo_category.currentIndexChanged.connect(self._load_data)

        # Time range filter
        time_label = QLabel("Period:")
        self.combo_time = QComboBox()
        self.combo_time.addItem("Today", "today")
        self.combo_time.addItem("Last 24 Hours", "24h")
        self.combo_time.addItem("Last 7 Days", "7d")
        self.combo_time.addItem("All Time", "all")
        self.combo_time.currentIndexChanged.connect(self._load_data)

        btn_refresh = QPushButton("🔄 Refresh")
        btn_refresh.setObjectName("primaryBtn")
        btn_refresh.clicked.connect(self._load_data)

        btn_clear = QPushButton("🗑️ Clear History")
        btn_clear.setObjectName("dangerBtn")
        btn_clear.clicked.connect(self._on_clear_history)

        filter_bar.addWidget(ch_label)
        filter_bar.addWidget(self.combo_channel)
        filter_bar.addWidget(cat_label)
        filter_bar.addWidget(self.combo_category)
        filter_bar.addWidget(time_label)
        filter_bar.addWidget(self.combo_time)
        filter_bar.addWidget(btn_refresh)
        filter_bar.addStretch()
        filter_bar.addWidget(btn_clear)

        main_layout.addLayout(filter_bar)

        # ── 2. KPI Summary Cards ─────────────────────────────────────
        kpi_layout = QHBoxLayout()
        kpi_layout.setSpacing(12)

        self.card_total = self._make_kpi_card("📊 Total Detections", "0", Colors.ACCENT)
        self.card_people = self._make_kpi_card("🚶 People", "0", "#00c8ff")
        self.card_vehicles = self._make_kpi_card("🚗 Vehicles", "0", "#ffa500")
        self.card_animals = self._make_kpi_card("🐾 Animals", "0", "#32dc32")

        kpi_layout.addWidget(self.card_total)
        kpi_layout.addWidget(self.card_people)
        kpi_layout.addWidget(self.card_vehicles)
        kpi_layout.addWidget(self.card_animals)

        main_layout.addLayout(kpi_layout)

        # ── 3. Channel Breakdown Matrix ──────────────────────────────
        matrix_title = QLabel("📈 Detection Frequency Matrix by Channel")
        matrix_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT_SECONDARY}; margin-top: 4px;")
        main_layout.addWidget(matrix_title)

        self.matrix_table = QTableWidget()
        self.matrix_table.setColumnCount(5)
        self.matrix_table.setHorizontalHeaderLabels(["Channel", "🚶 People", "🚗 Vehicles", "🐾 Animals", "Total Events"])
        self.matrix_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.matrix_table.verticalHeader().setVisible(False)
        self.matrix_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.matrix_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.matrix_table.setFixedHeight(120)
        main_layout.addWidget(self.matrix_table)

        # ── 4. Detailed Event Log Table with Selection Tools ─────────
        log_title_bar = QHBoxLayout()
        log_title = QLabel("📋 Detailed Detection Logs (Select rows to export or double-click to view snapshot)")
        log_title.setStyleSheet(f"font-size: 13px; font-weight: bold; color: {Colors.TEXT_SECONDARY}; margin-top: 4px;")
        log_title_bar.addWidget(log_title)
        log_title_bar.addStretch()

        btn_select_all = QPushButton("Select All")
        btn_select_all.setObjectName("subtleBtn")
        btn_select_all.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_select_all.clicked.connect(self._select_all_rows)

        btn_deselect = QPushButton("Deselect")
        btn_deselect.setObjectName("subtleBtn")
        btn_deselect.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_deselect.clicked.connect(self._deselect_all_rows)

        self.log_count_label = QLabel("0 events")
        self.log_count_label.setStyleSheet(f"color: {Colors.TEXT_MUTED}; font-size: 12px; margin-left: 8px;")

        log_title_bar.addWidget(btn_select_all)
        log_title_bar.addWidget(btn_deselect)
        log_title_bar.addWidget(self.log_count_label)
        main_layout.addLayout(log_title_bar)

        self.event_table = QTableWidget()
        self.event_table.setColumnCount(6)
        self.event_table.setHorizontalHeaderLabels(["Timestamp", "Channel", "Category", "Detected Target", "Confidence", "Snapshot"])
        self.event_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Stretch)
        self.event_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeMode.ResizeToContents)
        self.event_table.verticalHeader().setVisible(False)
        self.event_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.event_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.event_table.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.event_table.doubleClicked.connect(self._on_row_double_clicked)
        main_layout.addWidget(self.event_table)

        # ── 5. Bottom Action Bar ─────────────────────────────────────
        bottom_bar = QHBoxLayout()
        bottom_bar.setSpacing(8)

        btn_export_json = QPushButton("📦 Export JSON")
        btn_export_json.setObjectName("exportBtn")
        btn_export_json.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_json.setToolTip("Export selected events as JSON data (*.json)")
        btn_export_json.clicked.connect(lambda: self._on_export_events('json'))

        btn_export_csv = QPushButton("📄 Export CSV")
        btn_export_csv.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_export_csv.setToolTip("Export selected events as CSV spreadsheet (*.csv)")
        btn_export_csv.clicked.connect(lambda: self._on_export_events('csv'))

        btn_open_snapshot = QPushButton("🖼️ Open Snapshot")
        btn_open_snapshot.clicked.connect(self._open_selected_snapshot)

        btn_open_folder = QPushButton("📁 Open Snapshots Folder")
        btn_open_folder.clicked.connect(self._open_snapshots_folder)

        btn_close = QPushButton("Close")
        btn_close.clicked.connect(self.accept)

        bottom_bar.addWidget(btn_export_json)
        bottom_bar.addWidget(btn_export_csv)
        bottom_bar.addWidget(btn_open_snapshot)
        bottom_bar.addWidget(btn_open_folder)
        bottom_bar.addStretch()
        bottom_bar.addWidget(btn_close)

        main_layout.addLayout(bottom_bar)

    def _make_kpi_card(self, title: str, value: str, color: str) -> QFrame:
        card = QFrame()
        card.setObjectName("statCard")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(12, 10, 12, 10)
        layout.setSpacing(4)

        t_lbl = QLabel(title)
        t_lbl.setStyleSheet(f"color: {Colors.TEXT_SECONDARY}; font-size: 12px; font-weight: 600;")
        
        v_lbl = QLabel(value)
        v_lbl.setStyleSheet(f"color: {color}; font-size: 22px; font-weight: bold;")
        v_lbl.setObjectName("valueLabel")

        layout.addWidget(t_lbl)
        layout.addWidget(v_lbl)
        return card

    def _update_kpi_card(self, card: QFrame, value: int):
        val_lbl = card.findChild(QLabel, "valueLabel")
        if val_lbl:
            val_lbl.setText(f"{value:,}")

    def _get_time_bounds(self) -> tuple[float | None, float | None]:
        period = self.combo_time.currentData()
        now = time.time()

        if period == "today":
            today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            return today_start.timestamp(), now
        elif period == "24h":
            return now - 86400, now
        elif period == "7d":
            return now - 7 * 86400, now
        else:
            return None, None

    def _load_data(self):
        start_time, end_time = self._get_time_bounds()
        channel = self.combo_channel.currentData()
        category = self.combo_category.currentData()

        # 1. Fetch Stats
        stats = self.db.get_statistics(start_time=start_time, end_time=end_time)
        self._update_kpi_card(self.card_total, stats['total_events'])
        self._update_kpi_card(self.card_people, stats['category_counts'].get('person', 0))
        self._update_kpi_card(self.card_vehicles, stats['category_counts'].get('vehicle', 0))
        self._update_kpi_card(self.card_animals, stats['category_counts'].get('animal', 0))

        # 2. Populate Channel Breakdown Matrix
        channel_matrix = stats['channel_matrix']
        self.matrix_table.setRowCount(self.config.channels + 1)

        total_p, total_v, total_a, grand_total = 0, 0, 0, 0

        for idx in range(self.config.channels):
            ch = idx + 1
            m = channel_matrix.get(ch, {'person': 0, 'vehicle': 0, 'animal': 0, 'total': 0})
            
            total_p += m['person']
            total_v += m['vehicle']
            total_a += m['animal']
            grand_total += m['total']

            self._set_matrix_row(idx, f"Channel {ch}", m['person'], m['vehicle'], m['animal'], m['total'], is_total=False)

        # Summary Row
        self._set_matrix_row(
            self.config.channels,
            "Total (All CH)",
            total_p, total_v, total_a, grand_total,
            is_total=True
        )

        # 3. Populate Detailed Event Log Table
        self._current_events = self.db.query_events(
            channel=channel,
            category=category,
            start_time=start_time,
            end_time=end_time,
            limit=500
        )

        self.log_count_label.setText(f"{len(self._current_events)} events shown (max 500)")
        self.event_table.setRowCount(len(self._current_events))

        for row_idx, ev in enumerate(self._current_events):
            # Timestamp
            item_time = QTableWidgetItem(ev['datetime_str'])
            item_time.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Channel
            item_ch = QTableWidgetItem(f"CH {ev['channel']}")
            item_ch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Category
            cat_name = ev['category']
            cat_display = "🚶 Person" if cat_name == "person" else ("🚗 Vehicle" if cat_name == "vehicle" else "🐾 Animal")
            item_cat = QTableWidgetItem(cat_display)

            # Object Label
            item_label = QTableWidgetItem(ev['label'])

            # Confidence
            conf_pct = int(ev['confidence'] * 100)
            item_conf = QTableWidgetItem(f"{conf_pct}%")
            item_conf.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Snapshot
            snap_path = ev.get('snapshot_path')
            if snap_path and Path(snap_path).exists():
                item_snap = QTableWidgetItem("📷 Available")
                item_snap.setForeground(QColor(Colors.ACCENT))
            else:
                item_snap = QTableWidgetItem("—")
                item_snap.setForeground(QColor(Colors.TEXT_MUTED))
            item_snap.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

            # Store snapshot path in row data
            item_time.setData(Qt.ItemDataRole.UserRole, snap_path)

            self.event_table.setItem(row_idx, 0, item_time)
            self.event_table.setItem(row_idx, 1, item_ch)
            self.event_table.setItem(row_idx, 2, item_cat)
            self.event_table.setItem(row_idx, 3, item_label)
            self.event_table.setItem(row_idx, 4, item_conf)
            self.event_table.setItem(row_idx, 5, item_snap)

    def _set_matrix_row(self, row: int, ch_name: str, p: int, v: int, a: int, tot: int, is_total: bool = False):
        item_ch = QTableWidgetItem(ch_name)
        item_p = QTableWidgetItem(f"{p:,}")
        item_v = QTableWidgetItem(f"{v:,}")
        item_a = QTableWidgetItem(f"{a:,}")
        item_tot = QTableWidgetItem(f"{tot:,}")

        item_ch.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_p.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_v.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_a.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
        item_tot.setTextAlignment(Qt.AlignmentFlag.AlignCenter)

        if is_total:
            bold_font = item_ch.font()
            bold_font.setBold(True)
            for item in (item_ch, item_p, item_v, item_a, item_tot):
                item.setFont(bold_font)
                item.setBackground(QColor(255, 255, 255, 12))

        self.matrix_table.setItem(row, 0, item_ch)
        self.matrix_table.setItem(row, 1, item_p)
        self.matrix_table.setItem(row, 2, item_v)
        self.matrix_table.setItem(row, 3, item_a)
        self.matrix_table.setItem(row, 4, item_tot)

    def _select_all_rows(self):
        self.event_table.selectAll()

    def _deselect_all_rows(self):
        self.event_table.clearSelection()

    def _on_row_double_clicked(self, model_index):
        row = model_index.row()
        item = self.event_table.item(row, 0)
        if item:
            snap_path = item.data(Qt.ItemDataRole.UserRole)
            if snap_path and Path(snap_path).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(snap_path))
            else:
                QMessageBox.information(self, "No Snapshot", "No snapshot image was captured for this event.")

    def _open_selected_snapshot(self):
        selected_rows = self.event_table.selectionModel().selectedRows()
        if not selected_rows:
            QMessageBox.information(self, "Select Event", "Please click an event in the table to view its snapshot.")
            return

        row = selected_rows[0].row()
        item = self.event_table.item(row, 0)
        if item:
            snap_path = item.data(Qt.ItemDataRole.UserRole)
            if snap_path and Path(snap_path).exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(snap_path))
            else:
                QMessageBox.information(self, "No Snapshot", "No snapshot image was captured for this event.")

    def _open_snapshots_folder(self):
        folder = self.config.save_folder
        if Path(folder).exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(folder))
        else:
            QMessageBox.warning(self, "Directory Not Found", f"Snapshot directory does not exist yet:\n{folder}")

    def _on_export_events(self, format_type: str = 'json'):
        """Export selected events (or all filtered events) to JSON or CSV with optional snapshot image bundling."""
        selected_model_indexes = self.event_table.selectionModel().selectedRows()
        selected_rows = sorted(set(idx.row() for idx in selected_model_indexes))

        if not selected_rows:
            if self.event_table.rowCount() == 0:
                QMessageBox.information(self, "Export Events", "No detection events available to export.")
                return
            reply = QMessageBox.question(
                self,
                f"Export All Events ({format_type.upper()})",
                f"No specific rows are selected.\nDo you want to export all {self.event_table.rowCount()} currently displayed events to {format_type.upper()}?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply != QMessageBox.StandardButton.Yes:
                return
            selected_rows = list(range(self.event_table.rowCount()))

        export_data = []
        for r in selected_rows:
            if 0 <= r < len(self._current_events):
                ev = self._current_events[r]
                export_data.append({
                    'id': ev.get('id'),
                    'timestamp': float(ev.get('timestamp', 0)),
                    'datetime_str': str(ev.get('datetime_str', '')),
                    'channel': int(ev.get('channel', 1)),
                    'category': str(ev.get('category', '')),
                    'label': str(ev.get('label', '')),
                    'confidence': float(ev.get('confidence', 0.0)),
                    'snapshot_path': str(ev.get('snapshot_path')) if ev.get('snapshot_path') else None,
                })
            else:
                item = self.event_table.item(r, 0)
                export_data.append({
                    'id': r + 1,
                    'timestamp': time.time(),
                    'datetime_str': self.event_table.item(r, 0).text(),
                    'channel': int(self.event_table.item(r, 1).text().replace("CH", "").strip() or 1),
                    'category': self.event_table.item(r, 2).text(),
                    'label': self.event_table.item(r, 3).text(),
                    'confidence': float(self.event_table.item(r, 4).text().replace("%", "").strip() or 0) / 100.0,
                    'snapshot_path': str(item.data(Qt.ItemDataRole.UserRole)) if item and item.data(Qt.ItemDataRole.UserRole) else None,
                })

        timestamp_str = datetime.now().strftime('%Y%m%d_%H%M%S')
        is_json = format_type.lower() == 'json'

        if is_json:
            default_path = str(Path.home() / f"camview_events_{timestamp_str}.json")
            file_filter = "JSON Files (*.json);;All Files (*)"
        else:
            default_path = str(Path.home() / f"camview_events_{timestamp_str}.csv")
            file_filter = "CSV Files (*.csv);;All Files (*)"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            f"Export Selected Events ({format_type.upper()})",
            default_path,
            file_filter
        )

        if not file_path:
            return

        out_path = Path(file_path)
        if is_json and out_path.suffix.lower() != '.json':
            out_path = out_path.with_suffix('.json')
        elif not is_json and out_path.suffix.lower() != '.csv':
            out_path = out_path.with_suffix('.csv')

        try:
            if is_json:
                with open(out_path, 'w', encoding='utf-8') as f:
                    json.dump(export_data, f, indent=2, ensure_ascii=False)
            else:
                with open(out_path, 'w', newline='', encoding='utf-8') as f:
                    fieldnames = ['id', 'timestamp', 'datetime_str', 'channel', 'category', 'label', 'confidence', 'snapshot_path']
                    writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
                    writer.writeheader()
                    for row in export_data:
                        writer.writerow(row)

            # Check if any exported events have snapshots on disk
            valid_snapshots = [
                item['snapshot_path'] for item in export_data
                if item.get('snapshot_path') and Path(item['snapshot_path']).exists()
            ]

            if valid_snapshots:
                copy_reply = QMessageBox.question(
                    self,
                    "Export Associated Snapshots?",
                    f"Exported {len(export_data)} records to {out_path.name}.\n\nWould you like to copy the {len(valid_snapshots)} associated snapshot images into a '{out_path.stem}_snapshots' folder?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.Yes,
                )
                if copy_reply == QMessageBox.StandardButton.Yes:
                    export_img_dir = out_path.parent / f"{out_path.stem}_snapshots"
                    export_img_dir.mkdir(parents=True, exist_ok=True)
                    copied = 0
                    for snap in valid_snapshots:
                        shutil.copy2(snap, export_img_dir / Path(snap).name)
                        copied += 1

                    QMessageBox.information(
                        self,
                        "Export Complete",
                        f"Successfully exported:\n• {len(export_data)} event records to {out_path.name}\n• {copied} snapshot images to {export_img_dir.name}"
                    )
                    return

            QMessageBox.information(
                self,
                "Export Complete",
                f"Successfully exported {len(export_data)} events to:\n{out_path}"
            )
        except Exception as e:
            QMessageBox.critical(self, "Export Error", f"Failed to export events:\n{str(e)}")

    def _on_clear_history(self):
        reply = QMessageBox.question(
            self,
            "Clear Event History",
            "Are you sure you want to delete all recorded detection events?\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.db.clear_history()
            self._load_data()
