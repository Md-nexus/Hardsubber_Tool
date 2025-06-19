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
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings, QMimeData, QUrl, QPoint, QRect
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction, QStandardItem, QDrag, QPainter, QFontMetrics

# --- Simple subtitle preview widget with static frame ---
class SubtitlePreviewWidget(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.subtitle_text = "Sample subtitle text to preview your styling changes"
        self.font_size = 16
        self.font_color = "#FFFFFF"
        self.font_name = "Arial"
        self.border_style = 3
        
        self.setMinimumSize(640, 360)
        self.setStyleSheet("background-color: #000000; border: 1px solid #333;")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Create a simple black frame for preview
        self.create_sample_frame()
        self.update_preview()

    def create_sample_frame(self):
        """Create a simple black frame for subtitle overlay"""
        self.sample_pixmap = QPixmap(640, 360)
        self.sample_pixmap.fill(QColor(0, 0, 0))

    def setSubtitle(self, text):
        """Set subtitle text and update preview"""
        self.subtitle_text = text
        self.update_preview()

    def updateSubtitleStyle(self, font_size=16, font_color="#FFFFFF", font_name="Arial", border_style=3):
        """Update subtitle styling and refresh preview"""
        self.font_size = font_size
        self.font_color = font_color
        self.font_name = font_name
        self.border_style = border_style
        self.update_preview()

    def update_preview(self):
        """Update the preview with subtitle overlay on black background"""
        if not self.subtitle_text:
            self.setPixmap(self.sample_pixmap.scaled(
                self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation))
            return

        # Create a copy of the frame to draw on
        preview_pixmap = self.sample_pixmap.copy()
        
        # Create painter for overlay
        painter = QPainter(preview_pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Set up font
        font = QFont(self.font_name, self.font_size, QFont.Weight.Bold)
        painter.setFont(font)
        
        # Calculate text position and size
        font_metrics = QFontMetrics(font)
        text_lines = self.subtitle_text.split('\n')
        
        # Calculate total text dimensions
        max_width = 0
        total_height = 0
        line_heights = []
        
        for line in text_lines:
            line_width = font_metrics.horizontalAdvance(line)
            line_height = font_metrics.height()
            max_width = max(max_width, line_width)
            total_height += line_height
            line_heights.append(line_height)
        
        # Position at bottom center with margin
        margin = 30
        frame_width = preview_pixmap.width()
        frame_height = preview_pixmap.height()
        
        text_x = (frame_width - max_width) // 2
        text_y = frame_height - margin - total_height
        
        # Apply border style background
        if self.border_style == 3:  # Box background
            box_padding = 15
            box_rect = QRect(
                text_x - box_padding,
                text_y - box_padding,
                max_width + (box_padding * 2),
                total_height + (box_padding * 2)
            )
            painter.fillRect(box_rect, QColor(0, 0, 0, 180))
            
            # Optional: Add border to box
            painter.setPen(QColor(255, 255, 255, 100))
            painter.drawRect(box_rect)
        
        # Draw each line of text
        current_y = text_y
        for i, line in enumerate(text_lines):
            line_width = font_metrics.horizontalAdvance(line)
            line_x = (frame_width - line_width) // 2  # Center each line
            
            # Draw outline if needed
            if self.border_style in [1, 4]:  # Outline or Outline + Drop shadow
                painter.setPen(QColor(0, 0, 0))
                # Draw outline in multiple positions
                for dx in [-2, -1, 0, 1, 2]:
                    for dy in [-2, -1, 0, 1, 2]:
                        if dx == 0 and dy == 0:
                            continue
                        painter.drawText(line_x + dx, current_y + dy, line)
            
            # Draw drop shadow if needed
            if self.border_style in [2, 4]:  # Drop shadow or Outline + Drop shadow
                painter.setPen(QColor(0, 0, 0, 150))
                painter.drawText(line_x + 3, current_y + 3, line)
            
            # Draw main text
            painter.setPen(QColor(self.font_color))
            painter.drawText(line_x, current_y, line)
            
            current_y += line_heights[i]
        
        painter.end()
        
        # Scale and set the final pixmap
        scaled_pixmap = preview_pixmap.scaled(
            self.size(), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)
        self.setPixmap(scaled_pixmap)

    def resizeEvent(self, event):
        """Handle resize events to maintain proper scaling"""
        super().resizeEvent(event)
        self.update_preview()

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
        # Simple implementation - return the row under mouse or -1
        return self.rowAt(self.mapFromGlobal(self.cursor().pos()).y())

# ---SUBTITLE PREVIEW CONTAINER--- #
class SubtitlePreviewContainer(QWidget):
    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Preview widget
        self.preview_widget = SubtitlePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # Preview controls
        controls_layout = QHBoxLayout()
        
        self.test_button = QPushButton("Test Subtitle")
        self.test_button.setIcon(qta.icon('fa5s.eye'))
        self.test_button.clicked.connect(self.test_subtitle)
        controls_layout.addWidget(self.test_button)
        
        controls_layout.addStretch()
        layout.addLayout(controls_layout)

    def update_preview(self, font_size=16, font_color="#FFFFFF", font_name="Arial", border_style=3):
        """Update the subtitle preview with new styling"""
        self.preview_widget.updateSubtitleStyle(font_size, font_color, font_name, border_style)

    def test_subtitle(self):
        """Test subtitle display with sample text"""
        sample_text = "This is a sample subtitle text\nshowing how your styling will look"
        self.preview_widget.setSubtitle(sample_text)

# ---ADVANCED SETTINGS DIALOG--- #
class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Subtitle Settings")
        self.setModal(True)
        self.resize(500, 600)
        
        # Default values
        self.font_size = 16
        self.font_color = "#FFFFFF"
        self.font_name = "Arial"
        self.border_style = 3
        self.crf_value = 23
        
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Font settings
        font_group = QGroupBox("Font Settings")
        font_layout = QFormLayout(font_group)
        
        self.font_enabled = QCheckBox("Enable custom font settings")
        font_layout.addRow(self.font_enabled)
        
        # Font size
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(8, 72)
        self.font_size_spin.setValue(self.font_size)
        self.font_size_spin.valueChanged.connect(self.update_preview)
        font_layout.addRow("Font Size:", self.font_size_spin)
        
        # Font name
        self.font_name_edit = QLineEdit(self.font_name)
        self.font_name_edit.textChanged.connect(self.update_preview)
        font_layout.addRow("Font Name:", self.font_name_edit)
        
        # Font chooser button
        self.choose_font_btn = QPushButton("Choose Font...")
        self.choose_font_btn.clicked.connect(self.choose_font)
        font_layout.addRow(self.choose_font_btn)
        
        layout.addWidget(font_group)
        
        # Color settings
        color_group = QGroupBox("Color Settings")
        color_layout = QFormLayout(color_group)
        
        self.color_enabled = QCheckBox("Enable custom color")
        color_layout.addRow(self.color_enabled)
        
        # Color picker
        color_picker_layout = QHBoxLayout()
        self.color_button = QPushButton()
        self.color_button.setFixedSize(50, 30)
        self.color_button.setStyleSheet(f"background-color: {self.font_color}; border: 1px solid black;")
        self.color_button.clicked.connect(self.choose_color)
        color_picker_layout.addWidget(self.color_button)
        
        self.color_label = QLabel(self.font_color)
        color_picker_layout.addWidget(self.color_label)
        color_picker_layout.addStretch()
        
        color_layout.addRow("Font Color:", color_picker_layout)
        layout.addWidget(color_group)
        
        # Border settings
        border_group = QGroupBox("Border/Outline Settings")
        border_layout = QFormLayout(border_group)
        
        self.border_enabled = QCheckBox("Enable border/outline")
        self.border_enabled.setChecked(True)
        border_layout.addRow(self.border_enabled)
        
        # Border style
        self.border_combo = QComboBox()
        self.border_combo.addItems([
            "0 - No border",
            "1 - Outline only", 
            "2 - Drop shadow only",
            "3 - Background box",
            "4 - Outline + Drop shadow"
        ])
        self.border_combo.setCurrentIndex(self.border_style)
        self.border_combo.currentIndexChanged.connect(self.update_preview)
        border_layout.addRow("Border Style:", self.border_combo)
        
        layout.addWidget(border_group)
        
        # Quality settings
        quality_group = QGroupBox("Video Quality Settings")
        quality_layout = QFormLayout(quality_group)
        
        self.crf_enabled = QCheckBox("Enable custom quality (CRF)")
        quality_layout.addRow(self.crf_enabled)
        
        # CRF slider
        crf_layout = QHBoxLayout()
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(0, 51)
        self.crf_slider.setValue(self.crf_value)
        self.crf_slider.valueChanged.connect(self.update_crf_label)
        crf_layout.addWidget(self.crf_slider)
        
        self.crf_label = QLabel()
        self.update_crf_label(self.crf_value)
        crf_layout.addWidget(self.crf_label)
        
        quality_layout.addRow("CRF Value:", crf_layout)
        layout.addWidget(quality_group)
        
        # Preview area
        self.preview_widget = SubtitlePreviewWidget()
        layout.addWidget(self.preview_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Initial preview update
        self.update_preview()

    def choose_font(self):
        """Open font chooser dialog"""
        current_font = QFont(self.font_name, self.font_size)
        font, ok = QFontDialog.getFont(current_font, self)
        
        if ok:
            self.font_name = font.family()
            self.font_size = font.pointSize()
            self.font_name_edit.setText(self.font_name)
            self.font_size_spin.setValue(self.font_size)
            self.update_preview()

    def choose_color(self):
        """Open color chooser dialog"""
        color = QColorDialog.getColor(QColor(self.font_color), self)
        
        if color.isValid():
            self.font_color = color.name()
            self.color_button.setStyleSheet(f"background-color: {self.font_color}; border: 1px solid black;")
            self.color_label.setText(self.font_color)
            self.update_preview()

    def update_crf_label(self, value):
        """Update CRF quality label"""
        quality_map = {
            0: "Lossless", 18: "Very High", 23: "High (Default)",
            28: "Medium", 35: "Low", 51: "Very Low"
        }
        
        # Find closest quality description
        closest = min(quality_map.keys(), key=lambda x: abs(x - value))
        description = quality_map.get(closest, "Custom")
        
        self.crf_label.setText(f"{value} ({description})")
        self.crf_value = value

    def update_preview(self):
        """Update the preview with current settings"""
        font_size = self.font_size_spin.value()
        font_name = self.font_name_edit.text()
        border_style = self.border_combo.currentIndex()
        
        self.font_size = font_size
        self.font_name = font_name
        self.border_style = border_style
        
        # Update preview widget
        self.preview_widget.update_preview(font_size, self.font_color, font_name, border_style)

    def get_settings(self):
        """Return current settings as dictionary"""
        return {
            'font_enabled': self.font_enabled.isChecked(),
            'font_size': self.font_size,
            'font_name': self.font_name,
            'color_enabled': self.color_enabled.isChecked(),
            'font_color': self.font_color,
            'border_enabled': self.border_enabled.isChecked(),
            'border_style': self.border_style,
            'crf_enabled': self.crf_enabled.isChecked(),
            'crf_value': self.crf_value
        }

# ---MAIN GUI CLASS--- #
class HardSubberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("HardSubber Automator v4.3")
        self.setGeometry(100, 100, 1400, 900)
        self.input_folder = ""
        self.output_folder = ""
        self.subtitle_settings = {}
        self.processor = None
        
        # Load settings
        self.settings = QSettings("HardSubber", "Automator")
        self.load_settings()
        
        self.apply_modern_theme()
        self.setup_menu()
        self.setup_status_bar()
        self.setup_ui()
        
        # Check for FFmpeg
        self.check_ffmpeg()

    def apply_modern_theme(self):
        """Apply modern dark theme"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #555555;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #3c3c3c;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                background-color: #3c3c3c;
                color: #ffffff;
            }
            QPushButton {
                background-color: #0078d4;
                border: none;
                color: white;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton:disabled {
                background-color: #666666;
                color: #999999;
            }
            QTableWidget {
                gridline-color: #555555;
                background-color: #404040;
                alternate-background-color: #4a4a4a;
                color: #ffffff;
                border: 1px solid #555555;
                border-radius: 4px;
            }
            QTableWidget::item {
                padding: 8px;
                border-bottom: 1px solid #555555;
            }
            QTableWidget::item:selected {
                background-color: #0078d4;
            }
            QHeaderView::section {
                background-color: #505050;
                padding: 8px;
                border: none;
                border-right: 1px solid #555555;
                font-weight: bold;
                color: #ffffff;
            }
            QProgressBar {
                border: 1px solid #555555;
                border-radius: 4px;
                text-align: center;
                background-color: #404040;
                color: #ffffff;
            }
            QProgressBar::chunk {
                background-color: #0078d4;
                border-radius: 3px;
            }
            QComboBox {
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                background-color: #404040;
                color: #ffffff;
                min-width: 120px;
            }
            QComboBox:hover {
                border-color: #0078d4;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox QAbstractItemView {
                background-color: #404040;
                color: #ffffff;
                selection-background-color: #0078d4;
            }
            QLineEdit, QSpinBox {
                border: 1px solid #555555;
                border-radius: 4px;
                padding: 5px;
                background-color: #404040;
                color: #ffffff;
            }
            QLineEdit:hover, QSpinBox:hover {
                border-color: #0078d4;
            }
            QLabel {
                color: #ffffff;
            }
            QCheckBox {
                color: #ffffff;
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 16px;
                height: 16px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #555555;
                background-color: #404040;
                border-radius: 3px;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #0078d4;
                background-color: #0078d4;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                border: 1px solid #555555;
                height: 8px;
                background-color: #404040;
                border-radius: 4px;
            }
            QSlider::handle:horizontal {
                background-color: #0078d4;
                border: 1px solid #0078d4;
                width: 18px;
                margin: -5px 0;
                border-radius: 9px;
            }
            QSlider::handle:horizontal:hover {
                background-color: #106ebe;
            }
            QSplitter::handle {
                background-color: #555555;
                width: 3px;
            }
            QSplitter::handle:hover {
                background-color: #777777;
            }
            QStatusBar {
                background-color: #505050;
                border-top: 1px solid #555555;
                color: #ffffff;
            }
            QTextEdit {
                border: 1px solid #555555;
                border-radius: 4px;
                background-color: #404040;
                color: #ffffff;
                font-family: "Consolas", "Monaco", monospace;
                font-size: 11px;
            }
        """)

    def setup_menu(self):
        """Setup application menu"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu('File')
        
        new_action = QAction('New Project', self)
        new_action.setShortcut('Ctrl+N')
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        open_action = QAction('Open Project', self)
        open_action.setShortcut('Ctrl+O')
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        save_action = QAction('Save Project', self)
        save_action.setShortcut('Ctrl+S')
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction('Exit', self)
        exit_action.setShortcut('Ctrl+Q')
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Tools menu
        tools_menu = menubar.addMenu('Tools')
        
        settings_action = QAction('Advanced Settings', self)
        settings_action.triggered.connect(self.show_advanced_settings)
        tools_menu.addAction(settings_action)
        
        # Help menu
        help_menu = menubar.addMenu('Help')
        
        about_action = QAction('About', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = self.statusBar()
        self.status_bar.showMessage("Ready")

    

    def setup_ui(self):
        """Setup the main user interface"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main horizontal layout
        main_layout = QHBoxLayout(central_widget)
        
        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)
        
        # Left panel
        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        # Input folder selection
        input_group = QGroupBox("Input Source")
        input_layout = QVBoxLayout(input_group)
        
        input_buttons_layout = QHBoxLayout()
        
        self.select_folder_btn = QPushButton("Select Input Folder")
        self.select_folder_btn.setIcon(qta.icon('fa5s.folder-open'))
        self.select_folder_btn.clicked.connect(self.select_input_folder)
        input_buttons_layout.addWidget(self.select_folder_btn)
        
        self.add_files_btn = QPushButton("Add Video Files")
        self.add_files_btn.setIcon(qta.icon('fa5s.plus'))
        self.add_files_btn.clicked.connect(self.add_video_files)
        input_buttons_layout.addWidget(self.add_files_btn)
        
        input_layout.addLayout(input_buttons_layout)
        
        self.input_folder_label = QLabel("No folder selected")
        input_layout.addWidget(self.input_folder_label)
        
        left_layout.addWidget(input_group)
        
        # Video pairs table
        table_group = QGroupBox("Video-Subtitle Pairs")
        table_layout = QVBoxLayout(table_group)
        
        # Table controls
        table_controls = QHBoxLayout()
        
        self.toggle_all_btn = QPushButton("Toggle All")
        self.toggle_all_btn.setIcon(qta.icon('fa5s.check-square'))
        self.toggle_all_btn.clicked.connect(self.toggle_all_selection)
        table_controls.addWidget(self.toggle_all_btn)
        
        table_controls.addStretch()
        
        table_layout.addLayout(table_controls)
        
        # Main table
        self.video_table = DraggableTableWidget()
        self.video_table.setColumnCount(4)
        self.video_table.setHorizontalHeaderLabels([
            "Select", "Video File", "Subtitle File", "Browse"
        ])
        
        # Setup table column widths
        header = self.video_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        
        self.video_table.setAlternatingRowColors(True)
        
        
        
        table_layout.addWidget(self.video_table)
        left_layout.addWidget(table_group)
        
        # Processing settings
        settings_group = QGroupBox("Processing Settings")
        settings_layout = QVBoxLayout(settings_group)
        
        # Output folder
        output_layout = QHBoxLayout()
        self.output_folder_btn = QPushButton("Select Output Folder")
        self.output_folder_btn.setIcon(qta.icon('fa5s.folder'))
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        output_layout.addWidget(self.output_folder_btn)
        
        self.output_folder_label = QLabel("Same as input")
        output_layout.addWidget(self.output_folder_label)
        settings_layout.addLayout(output_layout)
        
        # Speed preset
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed Preset:"))
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems([
            "ultrafast", "superfast", "veryfast", "faster", 
            "fast", "medium", "slow", "slower", "veryslow"
        ])
        self.speed_combo.setCurrentText("fast")
        speed_layout.addWidget(self.speed_combo)
        
        settings_layout.addLayout(speed_layout)
        
        # Advanced settings button
        self.advanced_settings_btn = QPushButton("Advanced Settings")
        self.advanced_settings_btn.setIcon(qta.icon('fa5s.cogs'))
        self.advanced_settings_btn.clicked.connect(self.show_advanced_settings)
        settings_layout.addWidget(self.advanced_settings_btn)
        
        left_layout.addWidget(settings_group)
        
        # Processing controls
        process_group = QGroupBox("Processing")
        process_layout = QVBoxLayout(process_group)
        
        # Main process button
        self.start_btn = QPushButton("Start Processing")
        self.start_btn.setIcon(qta.icon('fa5s.play'))
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setMinimumHeight(40)
        process_layout.addWidget(self.start_btn)
        
        # Control buttons
        control_layout = QHBoxLayout()
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setIcon(qta.icon('fa5s.stop'))
        self.cancel_btn.clicked.connect(self.cancel_processing)
        self.cancel_btn.setEnabled(False)
        control_layout.addWidget(self.cancel_btn)
        
        self.skip_btn = QPushButton("Skip Current")
        self.skip_btn.setIcon(qta.icon('fa5s.forward'))
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setEnabled(False)
        control_layout.addWidget(self.skip_btn)
        
        process_layout.addLayout(control_layout)
        
        # Progress bar
        self.progress_bar = QProgressBar()
        process_layout.addWidget(self.progress_bar)
        
        # Progress info
        self.progress_info = QLabel("Ready to process")
        process_layout.addWidget(self.progress_info)
        
        # Output folder button
        self.open_output_btn = QPushButton("Open Output Folder")
        self.open_output_btn.setIcon(qta.icon('fa5s.external-link-alt'))
        self.open_output_btn.clicked.connect(self.open_output_folder)
        process_layout.addWidget(self.open_output_btn)
        
        left_layout.addWidget(process_group)
        
        # Right panel - Preview
        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        
        preview_group = QGroupBox("Subtitle Preview")
        preview_layout = QVBoxLayout(preview_group)
        
        # Initialize preview widget
        self.preview_widget = SubtitlePreviewContainer()
        preview_layout.addWidget(self.preview_widget)
        
        right_layout.addWidget(preview_group)
        
        # Add panels to splitter
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        
        # Set initial splitter sizes (60% left, 40% right)
        splitter.setSizes([840, 560])
        
        # Update UI state
        self.update_ui_state()

    def show_advanced_settings(self):
        """Show advanced subtitle settings dialog"""
        dialog = AdvancedSettingsDialog(self)
        
        # Load current settings into dialog
        if hasattr(self, 'subtitle_settings'):
            # Set dialog values from current settings
            pass  # Dialog will use defaults for now
            
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.subtitle_settings = dialog.get_settings()
            
            # Update preview with new settings
            if hasattr(self, 'preview_widget'):
                self.preview_widget.update_preview(
                    self.subtitle_settings.get('font_size', 16),
                    self.subtitle_settings.get('font_color', '#FFFFFF'),
                    self.subtitle_settings.get('font_name', 'Arial'),
                    self.subtitle_settings.get('border_style', 3)
                )

    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(self, "About HardSubber Automator",
                         "HardSubber Automator v4.3\n\n"
                         "A powerful tool for embedding subtitles into videos.\n\n"
                         "Features:\n"
                         "• Batch processing of video files\n"
                         "• Real-time subtitle preview\n"
                         "• Advanced subtitle styling\n"
                         "• Drag & drop functionality\n"
                         "• Multiple format support\n\n"
                         "Created by Nexus // MD-nexus")

    def new_project(self):
        """Create new project"""
        reply = QMessageBox.question(self, "New Project", 
                                   "Clear all current videos and settings?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            self.video_table.setRowCount(0)
            self.input_folder = ""
            self.output_folder = ""
            self.input_folder_label.setText("No folder selected")
            self.output_folder_label.setText("Same as input")
            self.update_ui_state()

    def open_project(self):
        """Open project file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "HardSubber Project (*.hsb);;JSON Files (*.json)"
        )
        
        if file_path:
            try:
                with open(file_path, 'r') as f:
                    project_data = json.load(f)
                
                # Load project data
                self.load_project_data(project_data)
                self.status_bar.showMessage(f"Opened project: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to open project:\n{str(e)}")

    def save_project(self):
        """Save current project"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "HardSubber Project (*.hsb);;JSON Files (*.json)"
        )
        
        if file_path:
            try:
                project_data = self.get_project_data()
                
                with open(file_path, 'w') as f:
                    json.dump(project_data, f, indent=2)
                
                self.status_bar.showMessage(f"Saved project: {os.path.basename(file_path)}")
                
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Failed to save project:\n{str(e)}")

    def get_project_data(self):
        """Get current project data for saving"""
        video_pairs = []
        
        for row in range(self.video_table.rowCount()):
            checkbox = self.video_table.cellWidget(row, 0)
            video_item = self.video_table.item(row, 1)
            subtitle_item = self.video_table.item(row, 2)
            
            if video_item and subtitle_item:
                video_pairs.append({
                    'selected': checkbox.isChecked() if checkbox else False,
                    'video_path': video_item.data(Qt.ItemDataRole.UserRole),
                    'subtitle_path': subtitle_item.data(Qt.ItemDataRole.UserRole)
                })
        
        return {
            'input_folder': self.input_folder,
            'output_folder': self.output_folder,
            'video_pairs': video_pairs,
            'settings': self.subtitle_settings,
            'speed_preset': self.speed_combo.currentText()
        }

    def load_project_data(self, project_data):
        """Load project data"""
        # Clear current data
        self.video_table.setRowCount(0)
        
        # Load settings
        self.input_folder = project_data.get('input_folder', '')
        self.output_folder = project_data.get('output_folder', '')
        self.subtitle_settings = project_data.get('settings', {})
        
        # Update UI
        self.input_folder_label.setText(self.input_folder if self.input_folder else "No folder selected")
        self.output_folder_label.setText(self.output_folder if self.output_folder else "Same as input")
        
        speed_preset = project_data.get('speed_preset', 'fast')
        if speed_preset in [self.speed_combo.itemText(i) for i in range(self.speed_combo.count())]:
            self.speed_combo.setCurrentText(speed_preset)
        
        # Load video pairs
        for pair_data in project_data.get('video_pairs', []):
            video_path = pair_data.get('video_path')
            subtitle_path = pair_data.get('subtitle_path')
            selected = pair_data.get('selected', True)
            
            if video_path and subtitle_path:
                self.add_video_to_table(video_path, subtitle_path, selected)

    def load_settings(self):
        """Load application settings"""
        self.input_folder = self.settings.value('input_folder', '', str)
        self.output_folder = self.settings.value('output_folder', '', str)
        
        # Load subtitle settings
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
        """Save application settings"""
        self.settings.setValue('input_folder', self.input_folder)
        self.settings.setValue('output_folder', self.output_folder)
        
        # Save subtitle settings
        for key, value in self.subtitle_settings.items():
            self.settings.setValue(key, value)

    def check_ffmpeg(self):
        """Check if FFmpeg is available"""
        try:
            result = subprocess.run(['ffmpeg', '-version'], 
                                  capture_output=True, timeout=5)
            if result.returncode == 0:
                self.status_bar.showMessage("FFmpeg detected - Ready to process videos")
                return True
        except:
            pass
        
        self.status_bar.showMessage("Warning: FFmpeg not found - Please install FFmpeg")
        return False

    def select_input_folder(self):
        """Select input folder containing videos and subtitles"""
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        
        if folder:
            self.input_folder = folder
            self.input_folder_label.setText(folder)
            self.load_input_folder(folder)

    def load_input_folder(self, folder):
        """Load video and subtitle files from folder"""
        if not os.path.exists(folder):
            return
        
        try:
            # Find video files
            video_extensions = {'.mp4', '.mkv', '.avi', '.mov', '.wmv', '.flv', '.m4v'}
            subtitle_extensions = {'.srt', '.vtt', '.ass', '.ssa'}
            
            video_files = []
            subtitle_files = []
            
            for file in os.listdir(folder):
                file_path = os.path.join(folder, file)
                if os.path.isfile(file_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in video_extensions:
                        video_files.append(file_path)
                    elif ext in subtitle_extensions:
                        subtitle_files.append(file_path)
            
            # Clear existing table
            self.video_table.setRowCount(0)
            
            # Match videos with subtitles
            added_count = 0
            for video_path in sorted(video_files):
                subtitle_path = self.find_matching_subtitle(video_path, subtitle_files)
                self.add_video_to_table(video_path, subtitle_path)
                added_count += 1
            
            self.status_bar.showMessage(f"Loaded {added_count} video files from folder")
            self.update_ui_state()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to load folder:\n{str(e)}")

    def find_matching_subtitle(self, video_path, subtitle_files):
        """Find matching subtitle file for video"""
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        video_dir = os.path.dirname(video_path)
        
        # First try exact match
        for ext in ['.srt', '.vtt', '.ass', '.ssa']:
            subtitle_path = os.path.join(video_dir, video_name + ext)
            if subtitle_path in subtitle_files:
                return subtitle_path
        
        # Try fuzzy matching
        subtitle_names = [os.path.splitext(os.path.basename(sf))[0] for sf in subtitle_files]
        matches = difflib.get_close_matches(video_name, subtitle_names, n=1, cutoff=0.6)
        
        if matches:
            match_name = matches[0]
            for subtitle_file in subtitle_files:
                if os.path.splitext(os.path.basename(subtitle_file))[0] == match_name:
                    return subtitle_file
        
        return None

    def add_video_files(self):
        """Add individual video files"""
        files, _ = QFileDialog.getOpenFileNames(
            self, "Select Video Files", "",
            "Video Files (*.mp4 *.mkv *.avi *.mov *.wmv *.flv *.m4v);;All Files (*)"
        )
        
        if files:
            for video_path in files:
                # Try to find matching subtitle in same directory
                video_dir = os.path.dirname(video_path)
                subtitle_files = []
                
                try:
                    for file in os.listdir(video_dir):
                        if file.lower().endswith(('.srt', '.vtt', '.ass', '.ssa')):
                            subtitle_files.append(os.path.join(video_dir, file))
                except:
                    pass
                
                subtitle_path = self.find_matching_subtitle(video_path, subtitle_files)
                self.add_video_to_table(video_path, subtitle_path)
            
            self.status_bar.showMessage(f"Added {len(files)} video files")
            self.update_ui_state()

    def add_video_to_table(self, video_path, subtitle_path, selected=True):
        """Add video-subtitle pair to table"""
        row = self.video_table.rowCount()
        self.video_table.insertRow(row)
        
        # Selection checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(selected)
        checkbox.stateChanged.connect(self.update_ui_state)
        self.video_table.setCellWidget(row, 0, checkbox)
        
        # Video file
        video_item = QTableWidgetItem(os.path.basename(video_path))
        video_item.setData(Qt.ItemDataRole.UserRole, video_path)
        video_item.setToolTip(video_path)
        self.video_table.setItem(row, 1, video_item)
        
        # Subtitle file
        if subtitle_path and os.path.exists(subtitle_path):
            subtitle_item = QTableWidgetItem(os.path.basename(subtitle_path))
            subtitle_item.setData(Qt.ItemDataRole.UserRole, subtitle_path)
            subtitle_item.setToolTip(subtitle_path)
            self.video_table.setItem(row, 2, subtitle_item)
        else:
            subtitle_item = QTableWidgetItem("No subtitle found")
            subtitle_item.setData(Qt.ItemDataRole.UserRole, None)
            self.video_table.setItem(row, 2, subtitle_item)
        
        # Browse button
        browse_btn = QPushButton("Browse")
        browse_btn.setIcon(qta.icon('fa5s.folder-open'))
        browse_btn.clicked.connect(lambda checked, r=row: self.browse_subtitle(r))
        self.video_table.setCellWidget(row, 3, browse_btn)

    def browse_subtitle(self, row):
        """Browse for subtitle file for specific row"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File", "",
            "Subtitle Files (*.srt *.vtt *.ass *.ssa);;All Files (*)"
        )
        
        if file_path:
            subtitle_item = QTableWidgetItem(os.path.basename(file_path))
            subtitle_item.setData(Qt.ItemDataRole.UserRole, file_path)
            subtitle_item.setToolTip(file_path)
            self.video_table.setItem(row, 2, subtitle_item)

    def toggle_all_selection(self):
        """Toggle selection of all videos"""
        # Check if any are currently selected
        selected_count = 0
        total_count = self.video_table.rowCount()
        
        for row in range(total_count):
            checkbox = self.video_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                selected_count += 1
        
        # If all or most are selected, unselect all; otherwise select all
        new_state = selected_count < (total_count / 2)
        
        for row in range(total_count):
            checkbox = self.video_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(new_state)

    def select_output_folder(self):
        """Select output folder"""
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)

    def update_ui_state(self):
        """Update UI state based on current data"""
        # Count selected videos with subtitles
        selected_count = 0
        total_count = self.video_table.rowCount()
        
        for row in range(total_count):
            checkbox = self.video_table.cellWidget(row, 0)
            subtitle_item = self.video_table.item(row, 2)
            
            if (checkbox and checkbox.isChecked() and 
                subtitle_item and subtitle_item.data(Qt.ItemDataRole.UserRole)):
                selected_count += 1
        
        # Update start button
        can_process = selected_count > 0 and not (self.processor and self.processor.isRunning())
        self.start_btn.setEnabled(can_process)
        
        # Update status
        if total_count == 0:
            status = "No videos loaded"
        elif selected_count == 0:
            status = "No videos selected for processing"
        else:
            status = f"{selected_count} videos ready for processing"
        
        if not can_process and self.processor and self.processor.isRunning():
            status = "Processing in progress..."
        
        self.progress_info.setText(status)

    def start_processing(self):
        """Start video processing"""
        # Get selected video pairs
        video_pairs = []
        
        for row in range(self.video_table.rowCount()):
            checkbox = self.video_table.cellWidget(row, 0)
            video_item = self.video_table.item(row, 1)
            subtitle_item = self.video_table.item(row, 2)
            
            if (checkbox and checkbox.isChecked() and 
                video_item and subtitle_item):
                
                video_path = video_item.data(Qt.ItemDataRole.UserRole)
                subtitle_path = subtitle_item.data(Qt.ItemDataRole.UserRole)
                
                if video_path and subtitle_path and os.path.exists(video_path) and os.path.exists(subtitle_path):
                    video_pairs.append((video_path, subtitle_path))
        
        if not video_pairs:
            QMessageBox.warning(self, "Warning", 
                              "No valid video-subtitle pairs selected!\n\n"
                              "Make sure you have:\n"
                              "• Selected videos (checkbox checked)\n"
                              "• Valid subtitle files for selected videos")
            return
        
        # Confirm processing
        reply = QMessageBox.question(self, "Confirm Processing",
                                   f"Process {len(video_pairs)} video(s)?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply != QMessageBox.StandardButton.Yes:
            return
        
        # Start processing
        speed_preset = self.speed_combo.currentText()
        
        self.processor = VideoProcessor(video_pairs, self.output_folder, 
                                      speed_preset, self.subtitle_settings)
        
        # Connect signals
        self.processor.progress_updated.connect(self.update_progress)
        self.processor.video_completed.connect(self.video_completed)
        self.processor.all_completed.connect(self.processing_completed)
        self.processor.error_occurred.connect(self.handle_error)
        
        self.processor.start()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.cancel_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        self.status_bar.showMessage("Processing started...")

    def handle_error(self, video_name, error_message):
        """Handle processing error"""
        error_msg = f"Error processing {video_name}:\n{error_message}"
        QMessageBox.warning(self, "Processing Error", error_msg)
        self.status_bar.showMessage(f"Error: {video_name}")

    def skip_current(self):
        """Skip current video being processed"""
        if self.processor and self.processor.isRunning():
            self.processor.skip()
            self.status_bar.showMessage("Skipping current video...")

    def cancel_processing(self):
        """Cancel video processing"""
        if self.processor and self.processor.isRunning():
            reply = QMessageBox.question(self, "Cancel Processing",
                                       "Are you sure you want to cancel processing?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply == QMessageBox.StandardButton.Yes:
                self.processor.stop()
                self.processor.wait()
                
                self.start_btn.setEnabled(True)
                self.cancel_btn.setEnabled(False)
                self.skip_btn.setEnabled(False)
                self.progress_bar.setValue(0)
                self.progress_info.setText("Processing cancelled")
                self.status_bar.showMessage("Processing cancelled")

    def update_progress(self, percent, video_name, output_size, input_size, original_video_size, eta):
        """Update processing progress"""
        self.progress_bar.setValue(percent)
        
        # Format ETA
        if eta > 0:
            eta_hours = int(eta // 3600)
            eta_minutes = int((eta % 3600) // 60)
            if eta_hours > 0:
                eta_str = f"{eta_hours}h {eta_minutes}m"
            else:
                eta_str = f"{eta_minutes}m"
        else:
            eta_str = "Calculating..."
        
        progress_text = f"Processing: {video_name} ({percent}%) - ETA: {eta_str}"
        self.progress_info.setText(progress_text)
        self.status_bar.showMessage(f"Processing {video_name} - {percent}%")

    def video_completed(self, video_name, success, output_path):
        """Handle completed video"""
        if success:
            self.status_bar.showMessage(f"Completed: {video_name}")
        else:
            self.status_bar.showMessage(f"Failed: {video_name}")

    def processing_completed(self, success_count, total_count):
        """Handle processing completion"""
        self.progress_bar.setValue(100)
        self.progress_info.setText(f"Completed! {success_count}/{total_count} videos processed successfully")
        
        # Update UI
        self.start_btn.setEnabled(True)
        self.cancel_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        
        # Show completion message
        if success_count == total_count:
            QMessageBox.information(self, "Processing Complete", 
                                  f"Successfully processed all {total_count} videos!")
        else:
            QMessageBox.warning(self, "Processing Complete", 
                              f"Processed {success_count} out of {total_count} videos.\n"
                              f"{total_count - success_count} videos failed.")
        
        # Play completion sound
        self.play_completion_sound()
        
        self.status_bar.showMessage(f"Processing complete: {success_count}/{total_count} successful")

    def play_completion_sound(self):
        """Play completion sound"""
        try:
            # Try to play system sound
            if sys.platform == "win32":
                import winsound
                winsound.MessageBeep(winsound.MB_OK)
            elif sys.platform == "darwin":
                os.system("afplay /System/Library/Sounds/Glass.aiff")
            else:
                # Linux - try multiple options
                for cmd in ["paplay /usr/share/sounds/alsa/Front_Right.wav",
                           "aplay /usr/share/sounds/alsa/Front_Right.wav",
                           "echo -e '\\a'"]:
                    try:
                        os.system(cmd)
                        break
                    except:
                        continue
        except:
            pass  # Silently fail if sound cannot be played

    def open_output_folder(self):
        """Open output folder in file manager"""
        folder_to_open = self.output_folder if self.output_folder else self.input_folder
        
        if not folder_to_open:
            QMessageBox.information(self, "Info", "No output folder set")
            return
        
        try:
            if sys.platform == "win32":
                os.startfile(folder_to_open)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_to_open])
            else:
                subprocess.run(["xdg-open", folder_to_open])
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Could not open folder:\n{str(e)}")

    def closeEvent(self, event):
        """Handle application close"""
        if self.processor and self.processor.isRunning():
            reply = QMessageBox.question(self, "Exit Application",
                                       "Processing is in progress. Are you sure you want to exit?",
                                       QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            
            self.processor.stop()
            self.processor.wait()
        
        # Save settings
        self.save_settings()
        event.accept()

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    
    # Set application properties
    app.setApplicationName("HardSubber Automator")
    app.setApplicationVersion("4.3")
    app.setOrganizationName("MD-nexus")
    app.setOrganizationDomain("github.com/md-nexus")
    
    # Create and show main window
    window = HardSubberGUI()
    window.show()
    
    # Start event loop
    sys.exit(app.exec())

if __name__ == "__main__":
    main()