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
try:
    import qtawesome as qta
except ImportError:
    # Fallback for missing qtawesome
    class MockQtAwesome:
        def icon(self, name, **kwargs):
            return QIcon()  # Return empty icon
    qta = MockQtAwesome()
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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings, QMimeData, QUrl
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction, QStandardItem, QDrag, QPainter, QPen, QBrush, QPaintEvent

# Basic video widget for preview (without multimedia dependencies)
class SubtitleVideoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subtitle_text = ""
        self.subtitle_style = {}
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: black; border: 2px solid #dee2e6; border-radius: 8px;")
        
        # Create a label to show "Video Preview" text
        self.preview_label = QLabel("Video Preview Area\n\nSubtitles will appear here overlaid on the video", self)
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setStyleSheet("color: white; font-size: 14px; background: transparent;")
        
        layout = QVBoxLayout(self)
        layout.addWidget(self.preview_label)
        
    def setSubtitle(self, text, style_dict=None):
        self.subtitle_text = text
        if style_dict:
            self.subtitle_style = style_dict
        self.update()  # trigger repaint

    def paintEvent(self, event: QPaintEvent):
        super().paintEvent(event)
        if not self.subtitle_text:
            return
            
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Get video widget dimensions
        widget_rect = self.rect()
        
        # Set up font based on style settings
        font_size = self.subtitle_style.get('font_size', 16)
        font_name = self.subtitle_style.get('font_name', 'Arial')
        font = QFont(font_name, font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Get text metrics
        font_metrics = painter.fontMetrics()
        text_rect = font_metrics.boundingRect(widget_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.subtitle_text)
        
        # Position subtitle at bottom of video area with margin
        margin = 20
        subtitle_height = text_rect.height() + 20  # Add padding
        subtitle_y = widget_rect.height() - subtitle_height - margin
        
        # Create subtitle area rectangle
        subtitle_rect = widget_rect.adjusted(margin, subtitle_y, -margin, -margin)
        
        # Draw background if border is enabled
        if self.subtitle_style.get('border_enabled', True):
            # Semi-transparent black background
            background_brush = QBrush(QColor(0, 0, 0, 180))
            painter.fillRect(subtitle_rect, background_brush)
            
            # Draw border
            border_pen = QPen(QColor(255, 255, 255, 100), 2)
            painter.setPen(border_pen)
            painter.drawRect(subtitle_rect)
        
        # Set text color
        font_color = self.subtitle_style.get('font_color', '#FFFFFF')
        text_color = QColor(font_color)
        
        # Draw outline/shadow for better visibility
        if self.subtitle_style.get('border_enabled', True):
            # Draw text outline
            outline_pen = QPen(QColor(0, 0, 0), 3)
            painter.setPen(outline_pen)
            painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.subtitle_text)
        
        # Draw main text
        painter.setPen(QPen(text_color))
        painter.drawText(subtitle_rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, self.subtitle_text)
        
        painter.end()

# ---VIDEO PROCESSOR THREAD CLASS--- #
class VideoProcessor(QThread):
    progress_updated = pyqtSignal(int, str, float, float, float, float)
    video_completed = pyqtSignal(str, bool, str)
    all_completed = pyqtSignal(int, int)
    processing_completed = pyqtSignal(int, int)  # Added missing signal
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
            self.processing_completed.emit(success_count, total_videos)

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
        # Simple implementation - return the row under mouse or -1
        return self.rowAt(self.mapFromGlobal(self.cursor().pos()).y())

# ---SUBTITLE SETTINGS DIALOG--- #
class SubtitleSettingsDialog(QDialog):
    def __init__(self, parent=None, current_settings=None):
        super().__init__(parent)
        self.setWindowTitle("Subtitle Settings")
        self.setModal(True)
        self.resize(400, 500)
        
        self.settings = current_settings or {}
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Font Settings Group
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)
        
        self.font_enabled = QCheckBox("Enable Custom Font")
        self.font_enabled.setChecked(self.settings.get('font_enabled', False))
        font_layout.addRow(self.font_enabled)
        
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(self.settings.get('font_size', 16))
        font_layout.addRow("Font Size:", self.font_size_spin)
        
        self.font_name_edit = QLineEdit()
        self.font_name_edit.setText(self.settings.get('font_name', 'Arial'))
        font_layout.addRow("Font Name:", self.font_name_edit)
        
        layout.addWidget(font_group)
        
        # Color Settings Group
        color_group = QGroupBox("Color Settings")
        color_layout = QFormLayout(color_group)
        
        self.color_enabled = QCheckBox("Enable Custom Color")
        self.color_enabled.setChecked(self.settings.get('color_enabled', False))
        color_layout.addRow(self.color_enabled)
        
        color_layout_h = QHBoxLayout()
        self.color_label = QLabel("Font Color:")
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 30)
        current_color = self.settings.get('font_color', '#FFFFFF')
        self.color_button.setStyleSheet(f"background-color: {current_color}; border: 1px solid black;")
        self.color_button.clicked.connect(self.choose_color)
        color_layout_h.addWidget(self.color_label)
        color_layout_h.addWidget(self.color_button)
        color_layout_h.addStretch()
        color_layout.addRow(color_layout_h)
        
        layout.addWidget(color_group)
        
        # Border Settings Group
        border_group = QGroupBox("Border Settings")
        border_layout = QFormLayout(border_group)
        
        self.border_enabled = QCheckBox("Enable Border/Outline")
        self.border_enabled.setChecked(self.settings.get('border_enabled', True))
        border_layout.addRow(self.border_enabled)
        
        self.border_style_spin = QSpinBox()
        self.border_style_spin.setRange(0, 4)
        self.border_style_spin.setValue(self.settings.get('border_style', 3))
        border_layout.addRow("Border Style:", self.border_style_spin)
        
        layout.addWidget(border_group)
        
        # Quality Settings Group
        quality_group = QGroupBox("Video Quality Settings")
        quality_layout = QFormLayout(quality_group)
        
        self.crf_enabled = QCheckBox("Enable Custom Quality (CRF)")
        self.crf_enabled.setChecked(self.settings.get('crf_enabled', False))
        quality_layout.addRow(self.crf_enabled)
        
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(self.settings.get('crf_value', 23))
        self.crf_slider.valueChanged.connect(self.update_crf_label)
        
        self.crf_label = QLabel()
        self.update_crf_label(self.crf_slider.value())
        
        crf_layout = QHBoxLayout()
        crf_layout.addWidget(self.crf_slider)
        crf_layout.addWidget(self.crf_label)
        quality_layout.addRow("CRF Value:", crf_layout)
        
        layout.addWidget(quality_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
    def choose_color(self):
        current_color = self.settings.get('font_color', '#FFFFFF')
        color = QColorDialog.getColor(QColor(current_color), self)
        if color.isValid():
            color_hex = color.name()
            self.settings['font_color'] = color_hex
            self.color_button.setStyleSheet(f"background-color: {color_hex}; border: 1px solid black;")
            
    def update_crf_label(self, value):
        quality_descriptions = {
            0: "Lossless",
            18: "Very High",
            23: "High (Default)",
            28: "Medium",
            35: "Low",
            51: "Very Low"
        }
        
        # Find closest description
        closest_key = min(quality_descriptions.keys(), key=lambda x: abs(x - value))
        description = quality_descriptions.get(closest_key, "Custom")
        
        self.crf_label.setText(f"{value} ({description})")
        
    def get_settings(self):
        return {
            'font_enabled': self.font_enabled.isChecked(),
            'font_size': self.font_size_spin.value(),
            'font_name': self.font_name_edit.text(),
            'color_enabled': self.color_enabled.isChecked(),
            'font_color': self.settings.get('font_color', '#FFFFFF'),
            'border_enabled': self.border_enabled.isChecked(),
            'border_style': self.border_style_spin.value(),
            'crf_enabled': self.crf_enabled.isChecked(),
            'crf_value': self.crf_slider.value()
        }

# ---MAIN GUI CLASS--- #
class HardSubberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HardSubber Automator v4.3")
        self.setGeometry(100, 100, 1200, 800)
        
        # Initialize variables
        self.input_folder = ""
        self.output_folder = ""
        self.subtitle_settings = {}
        self.processor = None
        self.settings = QSettings("HardSubber", "Automator")
        
        # Load saved settings
        self.load_settings()
        
        self.setup_ui()
        self.update_ui_state()
        
    def setup_ui(self):
        # Main widget and layout
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        main_layout = QHBoxLayout(main_widget)
        
        # Create splitter for resizable panes
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel for file management
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # File management section
        file_group = QGroupBox("Video File Management")
        file_layout = QVBoxLayout(file_group)
        
        # Add video files button
        add_video_btn = QPushButton("Add Video Files")
        add_video_btn.setObjectName("add_video_btn")
        add_video_btn.setIcon(qta.icon('fa5s.plus'))
        add_video_btn.clicked.connect(self.add_video_files)
        file_layout.addWidget(add_video_btn)
        
        # Clear all button
        clear_all_btn = QPushButton("Clear All")
        clear_all_btn.setObjectName("clear_all_btn")
        clear_all_btn.setIcon(qta.icon('fa5s.trash'))
        clear_all_btn.clicked.connect(self.clear_all_videos)
        file_layout.addWidget(clear_all_btn)
        
        # Video table
        self.video_table = DraggableTableWidget()
        self.video_table.setColumnCount(3)
        self.video_table.setHorizontalHeaderLabels(["Select", "Video File", "Subtitle File"])
        
        header = self.video_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        
        file_layout.addWidget(self.video_table)
        
        left_layout.addWidget(file_group)
        
        # Settings section
        settings_group = QGroupBox("Processing Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Output folder
        output_layout = QHBoxLayout()
        self.output_folder_btn = QPushButton("Set Output Folder")
        self.output_folder_btn.setObjectName("output_folder_btn")
        self.output_folder_btn.setIcon(qta.icon('fa5s.folder'))
        self.output_folder_btn.clicked.connect(self.set_output_folder)
        output_layout.addWidget(self.output_folder_btn)
        
        self.output_label = QLabel("No output folder selected")
        output_layout.addWidget(self.output_label)
        settings_layout.addLayout(output_layout)
        
        # Speed preset
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed Preset:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.speed_combo.setCurrentText("fast")
        speed_layout.addWidget(self.speed_combo)
        settings_layout.addLayout(speed_layout)
        
        # Subtitle settings
        subtitle_settings_btn = QPushButton("Subtitle Settings")
        subtitle_settings_btn.setIcon(qta.icon('fa5s.cog'))
        subtitle_settings_btn.clicked.connect(self.open_subtitle_settings)
        settings_layout.addWidget(subtitle_settings_btn)
        
        left_layout.addWidget(settings_group)
        
        # Processing controls
        process_group = QGroupBox("Processing Controls")
        process_layout = QVBoxLayout(process_group)
        
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setIcon(qta.icon('fa5s.play'))
        self.start_btn.clicked.connect(self.start_processing)
        process_layout.addWidget(self.start_btn)
        
        control_layout = QHBoxLayout()
        self.stop_btn = QPushButton("Stop")
        self.stop_btn.setObjectName("stop_btn")
        self.stop_btn.setIcon(qta.icon('fa5s.stop'))
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        control_layout.addWidget(self.stop_btn)
        
        self.skip_btn = QPushButton("Skip Current")
        self.skip_btn.setObjectName("skip_btn")
        self.skip_btn.setIcon(qta.icon('fa5s.forward'))
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setEnabled(False)
        control_layout.addWidget(self.skip_btn)
        
        process_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        process_layout.addWidget(self.progress_bar)
        
        self.progress_label = QLabel("Ready to process videos")
        process_layout.addWidget(self.progress_label)
        
        left_layout.addWidget(process_group)
        
        # Right panel for preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        # Preview section
        preview_group = QGroupBox("Subtitle Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Video preview widget (integrated subtitle display)
        self.video_preview = SubtitleVideoWidget()
        preview_layout.addWidget(self.video_preview)
        
        # Preview controls (only one set beside the media player)
        preview_controls_layout = QHBoxLayout()
        
        self.test_subtitle_btn = QPushButton("Test Subtitle")
        self.test_subtitle_btn.setIcon(qta.icon('fa5s.eye'))
        self.test_subtitle_btn.clicked.connect(self.test_subtitle_preview)
        preview_controls_layout.addWidget(self.test_subtitle_btn)
        
        preview_controls_layout.addStretch()
        
        preview_layout.addLayout(preview_controls_layout)
        
        right_layout.addWidget(preview_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([600, 600])  # Equal split
        
        # Apply stylesheet
        with open('styles.qss', 'r') as f:
            self.setStyleSheet(f.read())
            
    def add_video_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov);;All Files (*)"
        )
        
        for video_path in files:
            # Try to find matching subtitle
            subtitle_path = self.find_matching_subtitle(video_path)
            self.add_video_to_table(video_path, subtitle_path)
            
    def add_video_to_table(self, video_path, subtitle_path):
        row = self.video_table.rowCount()
        self.video_table.insertRow(row)
        
        # Checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(True)
        checkbox.stateChanged.connect(self.update_ui_state)
        self.video_table.setCellWidget(row, 0, checkbox)
        
        # Video file path
        video_item = QTableWidgetItem(os.path.basename(video_path))
        video_item.setData(Qt.ItemDataRole.UserRole, video_path)
        self.video_table.setItem(row, 1, video_item)
        
        # Subtitle file
        if subtitle_path:
            subtitle_item = QTableWidgetItem(os.path.basename(subtitle_path))
            subtitle_item.setData(Qt.ItemDataRole.UserRole, subtitle_path)
            self.video_table.setItem(row, 2, subtitle_item)
        else:
            browse_btn = QPushButton("Browse")
            browse_btn.setIcon(qta.icon('fa5s.folder-open', color='#007bff'))
            browse_btn.setStyleSheet("QPushButton { border: none; background: transparent; color: #007bff; text-decoration: underline; }")
            browse_btn.clicked.connect(lambda checked, r=row: self.browse_subtitle(r))
            self.video_table.setCellWidget(row, 2, browse_btn)
            
    def find_matching_subtitle(self, video_path):
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Look for subtitle files
        for ext in ['.srt', '.vtt']:
            subtitle_path = os.path.join(video_dir, video_name + ext)
            if os.path.exists(subtitle_path):
                return subtitle_path
                
        # Try fuzzy matching
        subtitle_files = []
        for file in os.listdir(video_dir):
            if file.lower().endswith(('.srt', '.vtt')):
                subtitle_files.append(file)
                
        if subtitle_files:
            matches = difflib.get_close_matches(video_name, 
                [os.path.splitext(f)[0] for f in subtitle_files], 
                n=1, cutoff=0.6)
            if matches:
                for file in subtitle_files:
                    if os.path.splitext(file)[0] == matches[0]:
                        return os.path.join(video_dir, file)
                        
        return None
        
    def browse_subtitle(self, row):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", "",
            "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        
        if file_path:
            subtitle_item = QTableWidgetItem(os.path.basename(file_path))
            subtitle_item.setData(Qt.ItemDataRole.UserRole, file_path)
            self.video_table.setItem(row, 2, subtitle_item)
            
    def clear_all_videos(self):
        self.video_table.setRowCount(0)
        self.update_ui_state()
        
    def set_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.setText(f"Output: {folder}")
            
    def open_subtitle_settings(self):
        dialog = SubtitleSettingsDialog(self, self.subtitle_settings)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.subtitle_settings = dialog.get_settings()
            self.update_subtitle_preview()
            
    def update_ui_state(self):
        # Check if any videos are selected
        selected_count = 0
        for row in range(self.video_table.rowCount()):
            checkbox = self.video_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
                
        # Enable/disable start button
        self.start_btn.setEnabled(selected_count > 0 and not (self.processor and self.processor.isRunning()))
        
    def start_processing(self):
        # Get selected video pairs
        video_pairs = []
        for row in range(self.video_table.rowCount()):
            checkbox = self.video_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                video_item = self.video_table.item(row, 1)
                subtitle_item = self.video_table.item(row, 2)
                
                if video_item and subtitle_item:
                    video_path = video_item.data(Qt.ItemDataRole.UserRole)
                    subtitle_path = subtitle_item.data(Qt.ItemDataRole.UserRole)
                    if video_path and subtitle_path:
                        video_pairs.append((video_path, subtitle_path))
                        
        if not video_pairs:
            QMessageBox.warning(self, "Warning", "No valid video-subtitle pairs selected!")
            return
            
        # Start processing
        speed_preset = self.speed_combo.currentText()
        
        self.processor = VideoProcessor(video_pairs, self.output_folder, speed_preset, self.subtitle_settings)
        self.processor.progress_updated.connect(self.update_progress)
        self.processor.video_completed.connect(self.video_completed)
        self.processor.processing_completed.connect(self.processing_completed)
        self.processor.error_occurred.connect(self.processing_error)
        
        self.processor.start()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        
    def stop_processing(self):
        if self.processor:
            self.processor.stop()
            self.processor.wait()
            
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_bar.setValue(0)
        self.progress_label.setText("Processing stopped")
        
    def skip_current(self):
        if self.processor:
            self.processor.skip()
            
    def update_progress(self, percent, video_name, output_size, input_size, video_size, eta):
        self.progress_bar.setValue(percent)
        eta_text = f" (ETA: {eta/60:.1f}m)" if eta > 0 else ""
        self.progress_label.setText(f"Processing: {video_name} - {percent}%{eta_text}")
        
    def video_completed(self, video_name, success, output_path):
        status = "completed" if success else "failed"
        self.progress_label.setText(f"Video {video_name} {status}")
        
    def processing_completed(self, success_count, total_count):
        self.progress_bar.setValue(100)
        self.progress_label.setText(f"Processing complete! {success_count}/{total_count} videos processed successfully")
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        QMessageBox.information(self, "Processing Complete", 
                              f"Successfully processed {success_count} out of {total_count} videos!")
        
    def processing_error(self, video_name, error_message):
        QMessageBox.warning(self, "Processing Error", 
                          f"Error processing {video_name}:\n{error_message}")
        
    def test_subtitle_preview(self):
        # Show test subtitle text with current settings
        test_text = "This is a sample subtitle text.\nIt shows how your subtitles will look."
        self.video_preview.setSubtitle(test_text, self.subtitle_settings)
        
    def update_subtitle_preview(self):
        # Update preview with current settings
        if hasattr(self, 'video_preview'):
            current_text = self.video_preview.subtitle_text
            if current_text:
                self.video_preview.setSubtitle(current_text, self.subtitle_settings)
                
    def load_settings(self):
        # Load saved settings
        self.subtitle_settings = {
            'font_enabled': self.settings.value('font_enabled', False, bool),
            'font_size': self.settings.value('font_size', 16, int),
            'font_name': self.settings.value('font_name', 'Arial', str),
            'color_enabled': self.settings.value('color_enabled', False, bool),
            'font_color': self.settings.value('font_color', '#FFFFFF', str),
            'border_enabled': self.settings.value('border_enabled', True, bool),
            'border_style': self.settings.value('border_style', 3, int),
            'crf_enabled': self.settings.value('crf_enabled', False, bool),
            'crf_value': self.settings.value('crf_value', 23, int)
        }
        
    def save_settings(self):
        # Save current settings
        for key, value in self.subtitle_settings.items():
            self.settings.setValue(key, value)
            
    def closeEvent(self, event):
        # Save settings and stop processing
        self.save_settings()
        if self.processor and self.processor.isRunning():
            self.processor.stop()
            self.processor.wait()
        event.accept()

def main():
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("HardSubber Automator")
    app.setApplicationVersion("4.3")
    app.setOrganizationName("MD-nexus")
    
    window = HardSubberGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()