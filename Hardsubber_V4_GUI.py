
#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.3 ║
# ║  GUI Edition with PyQt6    ║
# ║  by Nexus // MD-nexus      ║
# ╚════════════════════════════╝

import sys
import os
import re
import time
import json
import difflib
import threading
import subprocess
import webbrowser
import qtawesome as qta
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QComboBox, QProgressBar,
    QFileDialog, QScrollArea, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QLineEdit, QSlider,
    QStatusBar, QMenuBar, QMenu, QDialog, QFormLayout, QTabWidget,
    QColorDialog, QFontDialog, QRadioButton, QButtonGroup
)
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings, QMimeData, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction, QStandardItem, QDrag

# ---VIDEO PROCESSOR THREAD CLASS--- #
class VideoProcessor(QThread):
    progress_updated = pyqtSignal(int, str, float, float, float, float)
    video_completed = pyqtSignal(str, bool, str)
    all_completed = pyqtSignal(int, int)
    error_occurred = pyqtSignal(str, str)
    skip_current = pyqtSignal()

    def __init__(self, video_pairs, output_folder, speed_preset, subtitle_settings):
        super().__init__()
        self.video_pairs = video_pairs
        self.output_folder = output_folder
        self.speed_preset = speed_preset
        self.subtitle_settings = subtitle_settings
        self.is_running = True
        self.skip_requested = False
        self.start_time = None
        self.processed_count = 0
        self.cancelled = False

    def stop(self):
        self.is_running = False
        self.cancelled = True

    def skip(self):
        self.skip_requested = True

    def get_file_size_mb(self, path):
        try:
            return os.path.getsize(path) / (1024 * 1024)
        except:
            return 0.0

    def get_duration(self, video_path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                 "-of", "default=noprint_wrappers=1:nokey=1", video_path],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30
            )
            return float(result.stdout.strip())
        except:
            return None

    def break_proof_filename(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)

    def calculate_eta(self, current_progress, total_videos):
        if not self.start_time or current_progress == 0:
            return 0.0

        elapsed = time.time() - self.start_time
        videos_completed = self.processed_count + (current_progress / 100)
        if videos_completed == 0:
            return 0.0

        time_per_video = elapsed / videos_completed
        remaining_videos = total_videos - videos_completed
        return remaining_videos * time_per_video

    def run(self):
        self.start_time = time.time()
        success_count = 0
        total_videos = len(self.video_pairs)

        for i, (video_path, subtitle_path) in enumerate(self.video_pairs):
            if not self.is_running or self.cancelled:
                break

            self.skip_requested = False
            video_name = os.path.basename(video_path)
            name, ext = os.path.splitext(video_name)
            safe_name = self.break_proof_filename(name)

            if self.output_folder:
                output_path = os.path.join(self.output_folder, f"{safe_name}_subbed.mp4")
            else:
                output_path = os.path.join(os.path.dirname(video_path), f"{safe_name}_subbed.mp4")

            total_duration = self.get_duration(video_path)
            if not total_duration:
                self.error_occurred.emit(video_name, "Could not determine video duration")
                continue

            video_size = self.get_file_size_mb(video_path)
            subtitle_size = self.get_file_size_mb(subtitle_path)
            input_total_size = video_size + subtitle_size

            # Build subtitle filter with custom settings
            subtitle_filter_path = subtitle_path.replace("\\", "/").replace(":", "\\:")

            # Build force_style based on enabled settings
            force_style_parts = []

            if self.subtitle_settings.get('font_enabled', False):
                font_size = self.subtitle_settings.get('font_size', 16)
                font_name = self.subtitle_settings.get('font_name', 'Arial')
                force_style_parts.append(f"FontSize={font_size}")
                force_style_parts.append(f"FontName={font_name}")

            if self.subtitle_settings.get('color_enabled', False):
                color = self.subtitle_settings.get('font_color', '#FFFFFF')
                # Convert hex to BGR for ASS format
                if color.startswith('#'):
                    hex_color = color[1:]
                    r = int(hex_color[0:2], 16)
                    g = int(hex_color[2:4], 16)
                    b = int(hex_color[4:6], 16)
                    bgr_color = f"&H00{b:02X}{g:02X}{r:02X}"
                    force_style_parts.append(f"PrimaryColour={bgr_color}")

            if self.subtitle_settings.get('border_enabled', False):
                border_style = self.subtitle_settings.get('border_style', 3)
                force_style_parts.append(f"BorderStyle={border_style}")
                force_style_parts.append(f"Outline=2")
                force_style_parts.append(f"Shadow=1")

            # Default minimal styling if nothing is enabled
            if not force_style_parts:
                force_style_parts = ["FontSize=16", "BorderStyle=3", "Outline=2"]

            force_style = ",".join(force_style_parts)

            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{subtitle_filter_path}':force_style='{force_style}'",
                "-c:v", "libx264", "-preset", self.speed_preset,
                "-c:a", "copy",
                "-movflags", "+faststart",
                output_path
            ]

            # Add CRF if enabled
            if self.subtitle_settings.get('crf_enabled', False):
                crf_value = self.subtitle_settings.get('crf_value', 23)
                cmd.insert(-3, "-crf")
                cmd.insert(-3, str(crf_value))

            try:
                process = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    universal_newlines=True, bufsize=0
                )

                for line in process.stderr:
                    if not self.is_running or self.skip_requested or self.cancelled:
                        process.terminate()
                        if self.skip_requested:
                            self.video_completed.emit(video_name, False, "")
                        break

                    if "time=" in line:
                        match = re.search(r"time=(\d+):(\d+):(\d+.\d)", line)
                        if match:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = min((current_sec / total_duration) * 100, 99)
                            output_size = self.get_file_size_mb(output_path)
                            eta = self.calculate_eta(percent, total_videos)

                            self.progress_updated.emit(
                                int(percent), video_name, output_size, input_total_size, video_size, eta
                            )

                if not self.skip_requested and not self.cancelled:
                    process.wait()
                    success = process.returncode == 0 and self.is_running
                    if success:
                        success_count += 1
                        self.video_completed.emit(video_name, True, output_path)
                    else:
                        self.error_occurred.emit(video_name, "FFmpeg processing failed")
                        self.video_completed.emit(video_name, False, "")

            except Exception as e:
                self.error_occurred.emit(video_name, str(e))
                self.video_completed.emit(video_name, False, "")

            self.processed_count += 1

        if self.is_running and not self.cancelled:
            self.all_completed.emit(success_count, total_videos)

# ---DRAGGABLE TABLE WIDGET--- #
class DraggableTableWidget(QTableWidget):
    def __init__(self):
        super().__init__()
        self.setDragDropMode(QTableWidget.DragDropMode.InternalMove)
        self.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    

    def dropEvent(self, event):
        if event.source() == self:
            rows = sorted(set(item.row() for item in self.selectedItems()))
            target_row = self.drop_indicator_position()

            if target_row == -1:
                target_row = self.rowCount()

            # Store the data from selected rows
            rows_data = []
            for row in reversed(rows):  # Reverse to maintain order
                row_data = []
                for col in range(self.columnCount()):
                    item = self.item(row, col)
                    widget = self.cellWidget(row, col)
                    if widget:
                        if isinstance(widget, QCheckBox):
                            row_data.append(('checkbox', widget.isChecked()))
                        elif isinstance(widget, QPushButton):
                            row_data.append(('button', widget.text()))
                        else:
                            row_data.append(('widget', None))
                    elif item:
                        row_data.append(('item', item.clone()))
                    else:
                        row_data.append(('empty', None))
                rows_data.append(row_data)
                self.removeRow(row)

            # Adjust target row after removals
            for row in rows:
                if row < target_row:
                    target_row -= 1

            # Insert rows at target position
            for i, row_data in enumerate(reversed(rows_data)):
                self.insertRow(target_row + i)
                for col, (data_type, data) in enumerate(row_data):
                    if data_type == 'checkbox':
                        checkbox = QCheckBox()
                        checkbox.setChecked(data)
                        checkbox.stateChanged.connect(self.parent().update_ui_state)
                        self.setCellWidget(target_row + i, col, checkbox)
                    elif data_type == 'button':
                        browse_btn = QPushButton("Browse")
                        browse_btn.setIcon(qta.icon('fa5s.folder-open', color='#007bff'))
                        browse_btn.setStyleSheet("QPushButton { border: none; background: transparent; color: #007bff; text-decoration: underline; }")
                        browse_btn.clicked.connect(lambda checked, r=target_row + i: self.parent().browse_subtitle(r))
                        self.setCellWidget(target_row + i, col, browse_btn)
                    elif data_type == 'item':
                        self.setItem(target_row + i, col, data)

            event.accept()
        else:
            super().dropEvent(event)

    def drop_indicator_position(self):
        return self.rowAt(self.mapFromGlobal(self.cursor().pos()).y())

# ---SUBTITLE PREVIEW WIDGET--- #
class SubtitlePreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(400, 250)
        self.current_video_file = None
        self.setStyleSheet("""
            QWidget {
                background-color: #2b2b2b;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        # --- integrated video+subtitle widget ---
        class SubtitleVideoWidget(QVideoWidget):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.subtitle_text = ""
                self.subtitle_style = ""  # will be set by update_preview

            def setSubtitle(self, text, style_css=""):
                self.subtitle_text = text
                self.subtitle_style = style_css
                self.update()  # trigger repaint

            def paintEvent(self, event):
                super().paintEvent(event)
                if not self.subtitle_text:
                    return
                painter = QPainter(self)
                # draw CSS style if needed (e.g. background box)
                painter.setPen(Qt.white)
                # You can parse font-size etc from subtitle_style or hard‑code here:
                font = QFont("Arial", 16, QFont.Bold)
                painter.setFont(font)
                # draw text centered at bottom:
                rect = self.rect().adjusted(0, self.height() - 80, 0, -10)
                painter.drawText(rect, Qt.AlignCenter | Qt.TextWordWrap, self.subtitle_text)
                painter.end()

        # In your SubtitlePreviewWidget.__init__ replace the old video_widget + subtitle area:
        self.media_player = QMediaPlayer(self)
        self.audio_output = QAudioOutput(self)
        self.media_player.setAudioOutput(self.audio_output)

        # use our new subclass:
        self.video_widget = SubtitleVideoWidget()
        self.video_widget.setMinimumHeight(250)
        self.media_player.setVideoOutput(self.video_widget)

        header_layout = QHBoxLayout()

        self.select_table_btn = QPushButton("Select Video")
        self.select_table_btn.setIcon(qta.icon('fa5s.list', color='white'))
        header_layout.addWidget(self.select_table_btn)

        # now stack Save/Load buttons under it:
        side_buttons = QVBoxLayout()
        side_buttons.addLayout(header_layout)
        side_buttons.addSpacing(10)

        self.save_cfg_btn = QPushButton("💾 Save Settings")
        side_buttons.addWidget(self.save_cfg_btn)

        self.load_cfg_btn = QPushButton("📂 Load Settings")
        side_buttons.addWidget(self.load_cfg_btn)
        # then add side_buttons next to the video_widget:
        main_preview_layout = QHBoxLayout()
        main_preview_layout.addWidget(self.video_widget, 3)    # big video area
        main_preview_layout.addLayout(side_buttons, 1)         # narrow control column
        layout.addLayout(main_preview_layout)


    def load_video(self, file_path):
        """Load and pause the video so the first frame is shown."""
        self.media_player.setSource(QUrl.fromLocalFile(file_path))
        self.media_player.pause()

    def browse_video_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Video File for Preview",
            "", "Video Files (*.mp4 *.mkv *.mov *.avi *.wmv *.flv *.webm);;All Files (*)"
        )
        if file_path:
            self.load_video(file_path)


    def update_preview(self, font_size=16, font_color="#FFFFFF", font_name="Arial", border_style=3):
        # Create subtitle styling based on border style
        border_css = ""
        if border_style == 1:  # Outline
            border_css = "border: 2px solid #000000;"
        elif border_style == 2:  # Drop shadow
            border_css = "text-shadow: 2px 2px 4px #000000;"
        elif border_style == 3:  # Box background
            border_css = "background-color: rgba(0, 0, 0, 180); border-radius: 4px; padding: 8px;"
        elif border_style == 4:  # Outline + drop shadow
            border_css = "border: 2px solid #000000; text-shadow: 2px 2px 4px #000000;"

        style = f"""
            QLabel {{
                color: {font_color};
                font-family: {font_name};
                font-size: {font_size}px;
                font-weight: bold;
                {border_css}
            }}
        """
        self.subtitle_label.setStyleSheet(style)

# ---ADVANCED SETTINGS DIALOG--- #
class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Subtitle Settings")
        self.setModal(True)
        self.resize(800, 600)

        layout = QVBoxLayout(self)

        # Create tab widget
        tabs = QTabWidget()

        # Font Settings Tab
        font_tab = QWidget()
        font_layout = QVBoxLayout(font_tab)

        self.font_group = QButtonGroup()
        self.font_enabled = QRadioButton("Use Custom Font Settings")
        self.font_disabled = QRadioButton("Use Default Font Settings")
        self.font_disabled.setChecked(True)
        self.font_group.addButton(self.font_enabled)
        self.font_group.addButton(self.font_disabled)

        font_layout.addWidget(self.font_enabled)
        font_layout.addWidget(self.font_disabled)

        self.font_settings_widget = QWidget()
        font_settings_layout = QFormLayout(self.font_settings_widget)

        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(16)
        self.font_size.valueChanged.connect(self.update_preview)
        font_settings_layout.addRow("Font Size:", self.font_size)

        # Font name
        self.font_name = QLineEdit("Arial")
        self.font_name.textChanged.connect(self.update_preview)
        font_btn = QPushButton("Choose Font")
        font_btn.clicked.connect(self.choose_font)
        font_name_layout = QHBoxLayout()
        font_name_layout.addWidget(self.font_name)
        font_name_layout.addWidget(font_btn)
        font_settings_layout.addRow("Font Family:", font_name_layout)

        font_layout.addWidget(self.font_settings_widget)
        self.font_settings_widget.setEnabled(False)
        tabs.addTab(font_tab, "Font")

        # Color Settings Tab
        color_tab = QWidget()
        color_layout = QVBoxLayout(color_tab)

        self.color_group = QButtonGroup()
        self.color_enabled = QRadioButton("Use Custom Color Settings")
        self.color_disabled = QRadioButton("Use Default Color Settings")
        self.color_disabled.setChecked(True)
        self.color_group.addButton(self.color_enabled)
        self.color_group.addButton(self.color_disabled)

        color_layout.addWidget(self.color_enabled)
        color_layout.addWidget(self.color_disabled)

        self.color_settings_widget = QWidget()
        color_settings_layout = QFormLayout(self.color_settings_widget)

        # Font color
        self.font_color = QLineEdit("#FFFFFF")
        self.font_color.textChanged.connect(self.update_preview)
        color_btn = QPushButton("Choose Color")
        color_btn.clicked.connect(self.choose_color)
        color_layout_h = QHBoxLayout()
        color_layout_h.addWidget(self.font_color)
        color_layout_h.addWidget(color_btn)
        color_settings_layout.addRow("Text Color:", color_layout_h)

        color_layout.addWidget(self.color_settings_widget)
        self.color_settings_widget.setEnabled(False)
        tabs.addTab(color_tab, "Color")

        # Border Settings Tab
        border_tab = QWidget()
        border_layout = QVBoxLayout(border_tab)

        self.border_group = QButtonGroup()
        self.border_enabled = QRadioButton("Use Custom Border Settings")
        self.border_disabled = QRadioButton("Use Default Border Settings")
        self.border_disabled.setChecked(True)
        self.border_group.addButton(self.border_enabled)
        self.border_group.addButton(self.border_disabled)

        border_layout.addWidget(self.border_enabled)
        border_layout.addWidget(self.border_disabled)

        self.border_settings_widget = QWidget()
        border_settings_layout = QFormLayout(self.border_settings_widget)

        # Border style
        self.border_style = QComboBox()
        self.border_style.addItems(["Outline", "Drop Shadow", "Box Background", "Outline + Drop Shadow"])
        self.border_style.setCurrentIndex(2)
        self.border_style.currentIndexChanged.connect(self.update_preview)
        border_settings_layout.addRow("Border Style:", self.border_style)

        border_layout.addWidget(self.border_settings_widget)
        self.border_settings_widget.setEnabled(False)
        tabs.addTab(border_tab, "Border")

        # Quality Settings Tab
        quality_tab = QWidget()
        quality_layout = QVBoxLayout(quality_tab)

        self.crf_group = QButtonGroup()
        self.crf_enabled = QRadioButton("Use Custom Quality Settings")
        self.crf_disabled = QRadioButton("Use Default Quality Settings")
        self.crf_disabled.setChecked(True)
        self.crf_group.addButton(self.crf_enabled)
        self.crf_group.addButton(self.crf_disabled)

        quality_layout.addWidget(self.crf_enabled)
        quality_layout.addWidget(self.crf_disabled)

        self.crf_settings_widget = QWidget()
        crf_settings_layout = QFormLayout(self.crf_settings_widget)

        # CRF slider with tooltip
        crf_layout = QHBoxLayout()
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(18, 28)
        self.crf_slider.setValue(23)
        self.crf_label = QLabel("23 (Balanced)")
        self.size_estimate_label = QLabel("~20-30% smaller than original")
        self.size_estimate_label.setStyleSheet("color: #666; font-size: 11px;")
        self.crf_slider.valueChanged.connect(self.update_crf_label)

        crf_layout.addWidget(self.crf_slider)
        crf_layout.addWidget(self.crf_label)
        crf_settings_layout.addRow("Video Quality (CRF):", crf_layout)
        crf_settings_layout.addRow("Size Estimate:", self.size_estimate_label)

        quality_layout.addWidget(self.crf_settings_widget)
        self.crf_settings_widget.setEnabled(False)
        tabs.addTab(quality_tab, "Quality")

        layout.addWidget(tabs)

        # Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_widget = SubtitlePreviewWidget()
        if parent:
            self.preview_widget.select_table_btn.clicked.connect(self.select_top_table_video)
            self.preview_widget.save_cfg_btn.clicked.connect(self.save_settings)
            self.preview_widget.load_cfg_btn.clicked.connect(self.load_settings)
        preview_layout.addWidget(self.preview_widget)
        layout.addWidget(preview_group)


        control_layout = QHBoxLayout()
        self.select_table_btn = QPushButton("Select Video")
        self.select_table_btn.clicked.connect(self.select_top_table_video)
        control_layout.addWidget(self.select_table_btn)

        self.browse_video_btn = QPushButton("Browse…")
        self.browse_video_btn.clicked.connect(self.preview_widget.browse_video_file)
        control_layout.addWidget(self.browse_video_btn)

        self.save_cfg_btn = QPushButton("💾 Save Settings")
        self.save_cfg_btn.clicked.connect(self.save_settings)
        control_layout.addWidget(self.save_cfg_btn)

        self.load_cfg_btn = QPushButton("📂 Load Settings")
        self.load_cfg_btn.clicked.connect(self.load_settings)
        control_layout.addWidget(self.load_cfg_btn)

        layout.addLayout(control_layout, 1)


        # Connect radio buttons
        self.font_enabled.toggled.connect(lambda checked: self.font_settings_widget.setEnabled(checked))
        self.color_enabled.toggled.connect(lambda checked: self.color_settings_widget.setEnabled(checked))
        self.border_enabled.toggled.connect(lambda checked: self.border_settings_widget.setEnabled(checked))
        self.crf_enabled.toggled.connect(lambda checked: self.crf_settings_widget.setEnabled(checked))

        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply Settings")
        cancel_btn = QPushButton("Cancel")
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # Initialize preview
        self.update_preview()

    def choose_font(self):
        font, ok = QFontDialog.getFont()
        if ok:
            self.font_name.setText(font.family())
            self.update_preview()

    def choose_color(self):
        color = QColorDialog.getColor()
        if color.isValid():
            self.font_color.setText(color.name())
            self.update_preview()

    def update_crf_label(self, value):
        quality_map = {
            18: "18 (Very High)", 19: "19 (High)", 20: "20 (High)",
            21: "21 (Good)", 22: "22 (Good)", 23: "23 (Balanced)",
            24: "24 (Balanced)", 25: "25 (Lower)", 26: "26 (Lower)",
            27: "27 (Low)", 28: "28 (Low)"
        }
        self.crf_label.setText(quality_map.get(value, f"{value}"))

        # Update size estimate
        size_estimates = {
            18: "~10-15% smaller", 19: "~15-20% smaller", 20: "~20-25% smaller",
            21: "~25-30% smaller", 22: "~30-35% smaller", 23: "~35-40% smaller",
            24: "~40-45% smaller", 25: "~45-50% smaller", 26: "~50-55% smaller",
            27: "~55-60% smaller", 28: "~60-65% smaller"
        }
        self.size_estimate_label.setText(size_estimates.get(value, "~35-40% smaller"))

    def update_preview(self):
        if hasattr(self, 'preview_widget'):
            self.preview_widget.update_preview(
                self.font_size.value(),
                self.font_color.text(),
                self.font_name.text(),
                self.border_style.currentIndex() + 1
            )

    def get_settings(self):
        return {
            'font_enabled': self.font_enabled.isChecked(),
            'font_size': self.font_size.value(),
            'font_name': self.font_name.text(),
            'color_enabled': self.color_enabled.isChecked(),
            'font_color': self.font_color.text(),
            'border_enabled': self.border_enabled.isChecked(),
            'border_style': self.border_style.currentIndex() + 1,
            'crf_enabled': self.crf_enabled.isChecked(),
            'crf_value': self.crf_slider.value()
        }

# ---MAIN GUI CLASS--- #
class HardSubberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_pairs = []
        self.processor_thread = None
        self.output_folder = None
        self.current_folder = None
        self.settings = QSettings("Nexus", "HardSubber")
        self.subtitle_settings = {}
        self.processing = False

        self.setWindowTitle("HardSubber Automator v4.3")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(900, 600)

        self.apply_modern_theme()
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.check_ffmpeg()
        self.load_settings()

    def apply_modern_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
                color: #333333;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: white;
                color: #333333;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #555555;
                font-size: 13px;
            }
            QTableWidget {
                gridline-color: #e0e0e0;
                background-color: white;
                alternate-background-color: #f8f8f8;
                border: 1px solid #d0d0d0;
                border-radius: 6px;
                color: #333333;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 8px 8px;
                border-bottom: 1px solid #e0e0e0;
                border-right: 1px solid #e0e0e0;
            }
            QTableWidget::item:hover {
                background-color: #f0f8ff;
            }
            QHeaderView::section {
                background-color: #4a5568;
                padding: 10px 8px;
                border: 1px solid #2d3748;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                background-color: #5a6578;
            }
            QStatusBar {
                background-color: #2d3748;
                color: white;
                font-weight: bold;
                border-top: 1px solid #d0d0d0;
            }
            QPushButton {
                background-color: #6c757d;
                color: white;
                border: none;
                border-radius: 6px;
                padding: 8px 16px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #5a6268;
            }
            QPushButton:pressed {
                background-color: #545b62;
            }
            QPushButton:disabled {
                background-color: #e9ecef;
                color: #6c757d;
            }
            QComboBox {
                border: 2px solid #d0d0d0;
                border-radius: 6px;
                padding: 5px;
                background-color: white;
                color: #333333;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
            QLabel {
                color: #333333;
            }
            QProgressBar {
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                height: 25px;
                background-color: #f8f8f8;
                color: #333333;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 6px;
            }
            QCheckBox {
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 12px;
                height: 12px;
                border: 2px solid #d0d0d0;
                border-radius: 3px;
                background-color: white;
                alignment: center;
            }
            QCheckBox::indicator:hover {
                border-color: #007bff;
                background-color: #e8f4fd;
            }
            QCheckBox::indicator:checked {
                background-color: #007bff;
                border-color: #007bff;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNiIgaGVpZ2h0PSIxNiIgZmlsbD0id2hpdGUiIHZpZXdCb3g9IjAgMCAxNiAxNiI+PHBhdGggZD0iTTEwLjk3IDQuOTdhLjc1Ljc1IDAgMCAxIDEuMDcxIDEuMDVsLTMuOTkyIDQuOTljLS4zMjkuNDEtLjg5Ni42NjQtMS40NzkuNjY0LS41ODMgMC0xLjE1LS4yNTMtMS40NzktLjY2NGwtMS45ODctMi40OGEuNzUuNzUgMCAwIDEgMS4xNjItLjk2TDYuNSAxMS4zOWwzLjQ3LTQuNDJhLjc1Ljc1IDAgMCAxIDEuMDctLjAwMXoiLz48L3N2Zz4=);
            }
        """)

    def setup_menu(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("File")

        open_action = QAction("Open Input Folder", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.select_input_folder)
        file_menu.addAction(open_action)

        settings_action = QAction("Advanced Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.triggered.connect(self.show_advanced_settings)
        file_menu.addAction(settings_action)

        file_menu.addSeparator()

        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        help_menu = menubar.addMenu("Help")

        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select an input folder to begin")

    def select_top_table_video(self):
        # pick the first checked/selected row:
        for row in range(self.files_table.rowCount()):
            cb = self.files_table.cellWidget(row, 0)
            if cb and cb.isChecked():
                path = self.files_table.item(row, 1).data(Qt.UserRole)
                if path:
                    self.preview_widget.load_video(path)
                    return

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top controls
        controls_layout = QHBoxLayout()

        self.input_folder_btn = QPushButton("Open Input Folder")
        self.input_folder_btn.setIcon(qta.icon('fa5s.folder-open', color='white'))
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        controls_layout.addWidget(self.input_folder_btn)

        self.output_folder_btn = QPushButton("Set Output Folder")
        self.output_folder_btn.setIcon(qta.icon('fa5s.save', color='white'))
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        controls_layout.addWidget(self.output_folder_btn)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Encoding Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.speed_combo.setCurrentText("medium")
        speed_layout.addWidget(self.speed_combo)
        controls_layout.addLayout(speed_layout)

        self.settings_btn = QPushButton("Advanced Settings")
        self.settings_btn.setIcon(qta.icon('fa5s.cog', color='white'))
        self.settings_btn.clicked.connect(self.show_advanced_settings)
        controls_layout.addWidget(self.settings_btn)

        main_layout.addLayout(controls_layout)

        # Folder display
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Input:"))
        self.input_folder_label = QLabel("No folder selected")
        self.input_folder_label.setStyleSheet("color: #6c757d; font-style: italic;")
        folder_layout.addWidget(self.input_folder_label)

        folder_layout.addWidget(QLabel("Output:"))
        self.output_folder_label = QLabel("Same as input folder")
        self.output_folder_label.setStyleSheet("color: #6c757d; font-style: italic;")
        folder_layout.addWidget(self.output_folder_label)

        main_layout.addLayout(folder_layout)

        # File explorer style table
        files_group = QGroupBox("Video and Subtitle Files")
        files_layout = QVBoxLayout(files_group)

        # Selection controls
        selection_layout = QHBoxLayout()
        self.toggle_selection_btn = QPushButton("Select All")
        self.toggle_selection_btn.clicked.connect(self.toggle_all_selection)
        self.toggle_selection_btn.setEnabled(False)
        selection_layout.addWidget(self.toggle_selection_btn)
        selection_layout.addStretch()
        files_layout.addLayout(selection_layout)

        self.files_table = DraggableTableWidget()
        self.files_table.setColumnCount(4)
        self.files_table.setHorizontalHeaderLabels(["✓", "Video File", "Subtitle File", "Status"])

        def _on_table_selection(self):
            selected = self.files_table.selectedItems()
            if not selected:
                return
            # column 1 is the video file
            video_item = selected[0]  # first selected cell
            if video_item.column() != 1:
                # find the video-cell in the same row
                video_item = self.files_table.item(video_item.row(), 1)
            path = video_item.data(Qt.ItemDataRole.UserRole)
            if path:
                self.preview_widget.load_video(path)

        # Configure table
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)

        self.files_table.setColumnWidth(0, 50)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setSelectionMode(QTableWidget.SelectionMode.NoSelection)
        self.files_table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.files_table.setSortingEnabled(True)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setShowGrid(True)
        self.files_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        
        

        files_layout.addWidget(self.files_table)
        main_layout.addWidget(files_group)

        # Progress section
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.current_video_label = QLabel("Ready to process videos...")
        self.current_video_label.setStyleSheet("font-weight: bold; color: #333333;")
        progress_layout.addWidget(self.current_video_label)

        self.progress_bar = QProgressBar()
        progress_layout.addWidget(self.progress_bar)

        info_layout = QHBoxLayout()
        self.size_info_label = QLabel("")
        self.size_info_label.setStyleSheet("color: #6c757d; font-size: 11px;")
        info_layout.addWidget(self.size_info_label)

        self.eta_label = QLabel("")
        self.eta_label.setStyleSheet("color: #28a745; font-size: 12px; font-weight: bold;")
        info_layout.addWidget(self.eta_label)
        info_layout.addStretch()

        progress_layout.addLayout(info_layout)
        main_layout.addWidget(progress_group)

        # Action buttons
        button_layout = QHBoxLayout()

        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setIcon(qta.icon('fa5s.play', color='white'))
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; } QPushButton:hover { background-color: #218838; }")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)

        self.skip_btn = QPushButton("Skip Current")
        self.skip_btn.setIcon(qta.icon('fa5s.forward', color='#000'))
        self.skip_btn.setStyleSheet("QPushButton { background-color: #ffc107; color: #000; } QPushButton:hover { background-color: #e0a800; }")
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setEnabled(False)
        button_layout.addWidget(self.skip_btn)

        self.cancel_btn = QPushButton("Cancel All")
        self.cancel_btn.setIcon(qta.icon('fa5s.stop', color='white'))
        self.cancel_btn.setStyleSheet("QPushButton { background-color: #dc3545; } QPushButton:hover { background-color: #c82333; }")
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addLayout(button_layout)

    def show_advanced_settings(self):
        dialog = AdvancedSettingsDialog(self)
        
        # Load current settings into dialog
        if hasattr(self, 'subtitle_settings') and self.subtitle_settings:
            if self.subtitle_settings.get('font_enabled', False):
                dialog.font_enabled.setChecked(True)
                dialog.font_size.setValue(self.subtitle_settings.get('font_size', 16))
                dialog.font_name.setText(self.subtitle_settings.get('font_name', 'Arial'))
            
            if self.subtitle_settings.get('color_enabled', False):
                dialog.color_enabled.setChecked(True)
                dialog.font_color.setText(self.subtitle_settings.get('font_color', '#FFFFFF'))
            
            if self.subtitle_settings.get('border_enabled', False):
                dialog.border_enabled.setChecked(True)
                dialog.border_style.setCurrentIndex(self.subtitle_settings.get('border_style', 3) - 1)
            
            if self.subtitle_settings.get('crf_enabled', False):
                dialog.crf_enabled.setChecked(True)
                dialog.crf_slider.setValue(self.subtitle_settings.get('crf_value', 23))
        
        dialog.update_preview()
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.subtitle_settings = dialog.get_settings()
            self.save_settings()

    def show_about(self):
        QMessageBox.about(self, "About HardSubber Automator",
                         "HardSubber Automator v4.3\n\n"
                         "A powerful tool for automatically hard-coding subtitles into video files.\n\n"
                         "Features:\n"
                         "• Drag & Drop reordering\n"
                         "• Advanced subtitle customization\n"
                         "• Real-time preview\n"
                         "• Batch processing\n"
                         "• Size estimation\n\n"
                         "Created by Nexus // MD-nexus\n"
                         "Built with PyQt6 and FFmpeg")

    def load_settings(self):
        speed = self.settings.value("speed_preset", "medium", type=str)
        if speed in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
            self.speed_combo.setCurrentText(speed)

    def save_settings(self):
        self.settings.setValue("speed_preset", self.speed_combo.currentText())

    def check_ffmpeg(self):
        try:
            result = subprocess.run(["ffmpeg", "-version"],
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE,
                                  text=True, timeout=10)
            version_line = result.stdout.split('\n')[0]
            self.status_bar.showMessage(f"FFmpeg detected: {version_line}")
        except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired):
            QMessageBox.critical(self, "FFmpeg Not Found",
                               "FFmpeg is required but not found in your system PATH.\n"
                               "Please install FFmpeg to use this application.")
            sys.exit(1)

    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.load_input_folder(folder)

    def load_input_folder(self, folder):
        self.current_folder = folder
        self.input_folder_label.setText(folder)
        self.input_folder_label.setStyleSheet("color: #28a745; font-weight: bold;")

        self.files_table.setRowCount(0)
        self.video_pairs.clear()

        video_exts = [".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"]
        video_files = []

        try:
            for file in os.listdir(folder):
                if any(file.lower().endswith(ext) for ext in video_exts):
                    video_files.append(os.path.join(folder, file))
        except PermissionError:
            QMessageBox.warning(self, "Permission Error",
                              "Cannot access the selected folder. Please check permissions.")
            return

        video_files.sort()

        subtitle_exts = [".srt", ".vtt", ".ass", ".ssa"]
        subtitle_files = []
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in subtitle_exts):
                subtitle_files.append(os.path.join(folder, file))

        self.files_table.setRowCount(len(video_files))

        for row, video_path in enumerate(video_files):
            video_name = os.path.basename(video_path)

            # Checkbox with proper styling
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_ui_state)
            self.files_table.setCellWidget(row, 0, checkbox)

            video_item = QTableWidgetItem(video_name)
            video_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            video_item.setData(Qt.ItemDataRole.UserRole, video_path)
            video_item.setToolTip(video_path)
            self.files_table.setItem(row, 1, video_item)

            subtitle_path = self.find_matching_subtitle(video_path, subtitle_files)
            if subtitle_path:
                subtitle_item = QTableWidgetItem(os.path.basename(subtitle_path))
                subtitle_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                subtitle_item.setData(Qt.ItemDataRole.UserRole, subtitle_path)
                subtitle_item.setToolTip(subtitle_path)
                subtitle_item.setBackground(QColor(40, 167, 69, 50))
                checkbox.setChecked(True)
                status_item = QTableWidgetItem("Ready")
                status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                status_item.setBackground(QColor(40, 167, 69, 50))
            else:
                # Show browse link instead of button
                browse_btn = QPushButton("Browse")
                browse_btn.setIcon(qta.icon('fa5s.folder-open', color='#007bff'))
                browse_btn.setStyleSheet("QPushButton { border: none; background: transparent; color: #007bff; text-decoration: underline; }")
                browse_btn.clicked.connect(lambda checked, r=row: self.browse_subtitle(r))
                self.files_table.setCellWidget(row, 2, browse_btn)

                status_item = QTableWidgetItem("No subtitle")
                status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                status_item.setBackground(QColor(220, 53, 69, 50))

            if subtitle_path:
                self.files_table.setItem(row, 2, subtitle_item)

            self.files_table.setItem(row, 3, status_item)

            self.video_pairs.append({
                'video_path': video_path,
                'subtitle_path': subtitle_path
            })

        self.toggle_selection_btn.setEnabled(len(video_files) > 0)
        self.update_ui_state()
        self.status_bar.showMessage(f"Loaded {len(video_files)} video files")

        if not video_files:
            QMessageBox.information(self, "No Videos Found",
                                  "No supported video files found in the selected folder.\n"
                                  "Supported formats: MP4, MKV, MOV, AVI, WMV, FLV, WebM")

    def find_matching_subtitle(self, video_path, subtitle_files):
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        best_match = None
        best_score = 0

        for subtitle_path in subtitle_files:
            subtitle_name = os.path.splitext(os.path.basename(subtitle_path))[0]
            similarity = difflib.SequenceMatcher(None,
                                               video_name.lower(),
                                               subtitle_name.lower()).ratio()
            if similarity > best_score and similarity > 0.4:
                best_score = similarity
                best_match = subtitle_path

        return best_match

    def browse_subtitle(self, row):
        video_path = self.files_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File",
            os.path.dirname(video_path),
            "Subtitle Files (*.srt *.vtt *.ass *.ssa);;All Files (*)"
        )
        if file_path:
            subtitle_item = QTableWidgetItem(os.path.basename(file_path))
            subtitle_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            subtitle_item.setData(Qt.ItemDataRole.UserRole, file_path)
            subtitle_item.setToolTip(file_path)
            subtitle_item.setBackground(QColor(40, 167, 69, 50))
            self.files_table.setItem(row, 2, subtitle_item)

            status_item = QTableWidgetItem("Ready")
            status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
            status_item.setBackground(QColor(40, 167, 69, 50))
            self.files_table.setItem(row, 3, status_item)

            checkbox = self.files_table.cellWidget(row, 0)
            checkbox.setChecked(True)

            self.video_pairs[row]['subtitle_path'] = file_path

    def toggle_all_selection(self):
        checked_count = 0
        total_available = 0

        for row in range(self.files_table.rowCount()):
            subtitle_item = self.files_table.item(row, 2)
            if subtitle_item and subtitle_item.data(Qt.ItemDataRole.UserRole):
                total_available += 1
                checkbox = self.files_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    checked_count += 1

        check_state = checked_count < total_available

        for row in range(self.files_table.rowCount()):
            subtitle_item = self.files_table.item(row, 2)
            if subtitle_item and subtitle_item.data(Qt.ItemDataRole.UserRole):
                checkbox = self.files_table.cellWidget(row, 0)
                checkbox.setChecked(check_state)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)
            self.output_folder_label.setStyleSheet("color: #28a745; font-weight: bold;")
        else:
            self.output_folder = None
            self.output_folder_label.setText("Same as input folder")
            self.output_folder_label.setStyleSheet("color: #6c757d; font-style: italic;")

    def update_ui_state(self):
        enabled_count = 0
        total_available = 0

        for row in range(self.files_table.rowCount()):
            subtitle_item = self.files_table.item(row, 2)
            if subtitle_item and subtitle_item.data(Qt.ItemDataRole.UserRole):
                total_available += 1
                checkbox = self.files_table.cellWidget(row, 0)
                if checkbox and checkbox.isChecked():
                    enabled_count += 1

        self.start_btn.setEnabled(enabled_count > 0 and not self.processing)

        if enabled_count > 0:
            self.start_btn.setText(f"Start Processing ({enabled_count} videos)")
        else:
            self.start_btn.setText("Start Processing")

        if total_available > 0:
            if enabled_count == total_available:
                self.toggle_selection_btn.setText("Unselect All")
            else:
                self.toggle_selection_btn.setText(f"Select All ({total_available} available)")

    def start_processing(self):
        enabled_pairs = []
        for row in range(self.files_table.rowCount()):
            checkbox = self.files_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                video_path = self.files_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                subtitle_path = self.files_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
                if subtitle_path:
                    enabled_pairs.append((video_path, subtitle_path))
                    status_item = QTableWidgetItem("Queued")
                    status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    status_item.setBackground(QColor(0, 123, 255, 50))
                    self.files_table.setItem(row, 3, status_item)

        if not enabled_pairs:
            QMessageBox.warning(self, "No Videos Selected",
                              "Please select at least one video-subtitle pair to process.")
            return

        self.processing = True
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.files_table.setEnabled(False)
        self.files_table.setStyleSheet(self.files_table.styleSheet() + "QTableWidget { opacity: 0.6; }")
        self.progress_bar.setValue(0)
        self.save_settings()

        self.processor_thread = VideoProcessor(
            enabled_pairs, self.output_folder, self.speed_combo.currentText(), self.subtitle_settings
        )
        self.processor_thread.progress_updated.connect(self.update_progress)
        self.processor_thread.video_completed.connect(self.video_completed)
        self.processor_thread.all_completed.connect(self.processing_completed)
        self.processor_thread.error_occurred.connect(self.handle_error)
        self.processor_thread.start()

    def handle_error(self, video_name, error_message):
        self.status_bar.showMessage(f"Error processing {video_name}: {error_message}")

    def skip_current(self):
        if self.processor_thread:
            self.processor_thread.skip()

    def cancel_processing(self):
        if self.processor_thread:
            self.processor_thread.stop()
            self.current_video_label.setText("Cancelling processing...")
            self.skip_btn.setEnabled(False)
            self.cancel_btn.setEnabled(False)
            self.status_bar.showMessage("Cancelling processing...")

    def update_progress(self, percent, video_name, output_size, input_size, original_video_size, eta):
        self.progress_bar.setValue(percent)
        self.current_video_label.setText(f"Processing: {video_name}")

        if input_size > 0:
            size_ratio = (output_size / input_size) * 100
            size_change = f"+{output_size - original_video_size:.1f}MB" if output_size > original_video_size else f"-{original_video_size - output_size:.1f}MB"

            self.size_info_label.setText(
                f"Output: {output_size:.1f}MB ({size_ratio:.1f}% of input) | "
                f"Original: {original_video_size:.1f}MB | Change: {size_change}"
            )

        if eta > 0:
            eta_hours = int(eta // 3600)
            eta_minutes = int((eta % 3600) // 60)
            eta_seconds = int(eta % 60)
            if eta_hours > 0:
                eta_text = f"ETA: {eta_hours}h {eta_minutes}m {eta_seconds}s"
            elif eta_minutes > 0:
                eta_text = f"ETA: {eta_minutes}m {eta_seconds}s"
            else:
                eta_text = f"ETA: {eta_seconds}s"
            self.eta_label.setText(eta_text)

        for row in range(self.files_table.rowCount()):
            video_item = self.files_table.item(row, 1)
            if video_item and os.path.basename(video_item.data(Qt.ItemDataRole.UserRole)) == video_name:
                status_item = QTableWidgetItem(f"Processing ({percent}%)")
                status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                status_item.setBackground(QColor(0, 123, 255, 50))
                self.files_table.setItem(row, 3, status_item)
                break

    def video_completed(self, video_name, success, output_path):
        status = "Completed" if success else "Failed/Skipped"
        self.current_video_label.setText(f"{status}: {video_name}")

        for row in range(self.files_table.rowCount()):
            video_item = self.files_table.item(row, 1)
            if video_item and os.path.basename(video_item.data(Qt.ItemDataRole.UserRole)) == video_name:
                if success:
                    status_item = QTableWidgetItem("Completed")
                    status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    status_item.setBackground(QColor(40, 167, 69, 50))
                    status_item.setToolTip(f"Output: {output_path}")
                else:
                    status_item = QTableWidgetItem("Failed")
                    status_item.setFlags(Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEnabled)
                    status_item.setBackground(QColor(220, 53, 69, 50))
                self.files_table.setItem(row, 3, status_item)
                break

        if success:
            self.status_bar.showMessage(f"Completed: {video_name}")

    def processing_completed(self, success_count, total_count):
        self.processing = False
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.files_table.setEnabled(True)
        self.files_table.setStyleSheet(self.files_table.styleSheet().replace("QTableWidget { opacity: 0.6; }", ""))
        self.progress_bar.setValue(100)
        self.current_video_label.setText(f"Processing completed! {success_count}/{total_count} successful")
        self.eta_label.setText("")
        self.status_bar.showMessage(f"All processing completed: {success_count}/{total_count} successful")
        self.update_ui_state()

        self.play_completion_sound()

        msg = QMessageBox(self)
        msg.setWindowTitle("Processing Complete")
        msg.setText(f"Processing completed!\n\nSuccessful: {success_count}\nTotal: {total_count}")
        msg.setIcon(QMessageBox.Icon.Information)

        open_folder_btn = msg.addButton("Open Output Folder", QMessageBox.ButtonRole.ActionRole)
        ok_btn = msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)

        msg.exec()

        if msg.clickedButton() == open_folder_btn:
            self.open_output_folder()

    def play_completion_sound(self):
        try:
            if sys.platform == "win32":
                import winsound
                winsound.Beep(800, 500)
            elif sys.platform == "darwin":  # macOS
                subprocess.run(["say", "Processing completed"], check=False)
            else:  # Linux and other UNIX-like systems
                # Try different methods for Linux sound notification
                try:
                    subprocess.run(["pactl", "upload-sample", "/usr/share/sounds/alsa/Front_Left.wav", "beep"], 
                                 check=True, timeout=1)
                    subprocess.run(["pactl", "play-sample", "beep"], check=True, timeout=1)
                except:
                    try:
                        subprocess.run(["aplay", "/usr/share/sounds/alsa/Front_Left.wav"], 
                                     check=True, timeout=2)
                    except:
                        # Fallback to terminal bell
                        print("\a", flush=True)
        except:
            # Final fallback to terminal bell
            print("\a", flush=True)

    

    def open_output_folder(self):
        folder_to_open = self.output_folder if self.output_folder else self.current_folder
        if folder_to_open and os.path.exists(folder_to_open):
            if sys.platform == "win32":
                os.startfile(folder_to_open)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_to_open])
            else:
                subprocess.run(["xdg-open", folder_to_open])

    

    def closeEvent(self, event):
        if self.processor_thread and self.processor_thread.isRunning():
            reply = QMessageBox.question(self, 'Confirm Exit',
                                       'Processing is still running. Are you sure you want to exit?',
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                                       QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.processor_thread.stop()
                self.processor_thread.wait()
                event.accept()
            else:
                event.ignore()
        else:
            self.save_settings()
            event.accept()

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HardSubber Automator v4.3")
    app.setOrganizationName("Nexus")
    app.setApplicationVersion("4.3")
    app.setStyle('Fusion')

    window = HardSubberGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
