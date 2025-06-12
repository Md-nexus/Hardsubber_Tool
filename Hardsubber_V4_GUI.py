
#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.2 ║
# ║  GUI Edition with PyQt6    ║
# ║  by Nexus // MD-nexus      ║
# ╚════════════════════════════╝

import sys
import os
import re
import time
import difflib
import subprocess
import threading
import webbrowser
import json
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QComboBox, QProgressBar, 
    QFileDialog, QScrollArea, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox, QLineEdit, QSlider,
    QStatusBar, QMenuBar, QMenu, QDialog, QFormLayout, QTabWidget,
    QColorDialog, QFontDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QSettings
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor, QAction, QStandardItem

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

    def stop(self):
        self.is_running = False

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
            if not self.is_running:
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
            force_style_parts = []
            
            if self.subtitle_settings.get('use_custom', False):
                if self.subtitle_settings.get('font_size'):
                    force_style_parts.append(f"FontSize={self.subtitle_settings['font_size']}")
                if self.subtitle_settings.get('font_color'):
                    force_style_parts.append(f"PrimaryColour={self.subtitle_settings['font_color']}")
                if self.subtitle_settings.get('border_style'):
                    force_style_parts.append(f"BorderStyle={self.subtitle_settings['border_style']}")
                if self.subtitle_settings.get('font_name'):
                    force_style_parts.append(f"FontName={self.subtitle_settings['font_name']}")
            else:
                force_style_parts = ["FontSize=16", "BorderStyle=3"]

            force_style = ",".join(force_style_parts)
            
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{subtitle_filter_path}':force_style='{force_style}'",
                "-c:v", "libx264", "-preset", self.speed_preset,
                "-c:a", "copy",
                "-movflags", "+faststart",
                output_path
            ]

            # Add CRF only if custom settings are enabled
            if self.subtitle_settings.get('use_custom', False) and self.subtitle_settings.get('crf_value'):
                cmd.insert(-3, "-crf")
                cmd.insert(-3, str(self.subtitle_settings['crf_value']))

            try:
                process = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    universal_newlines=True, bufsize=0
                )

                for line in process.stderr:
                    if not self.is_running or self.skip_requested:
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

                if not self.skip_requested:
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

        if self.is_running:
            self.all_completed.emit(success_count, total_videos)

# ---SUBTITLE PREVIEW WIDGET--- #
class SubtitlePreviewWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.setFixedSize(300, 200)
        self.setStyleSheet("""
            QWidget {
                background-color: #000000;
                border: 2px solid #555;
                border-radius: 8px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.addStretch()
        
        self.subtitle_label = QLabel("Sample Subtitle Text")
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.subtitle_label.setWordWrap(True)
        self.update_preview()
        
        layout.addWidget(self.subtitle_label)
        layout.addStretch()
    
    def update_preview(self, font_size=16, font_color="#FFFFFF", font_name="Arial"):
        style = f"""
            QLabel {{
                color: {font_color};
                font-family: {font_name};
                font-size: {font_size}px;
                font-weight: bold;
                background-color: transparent;
                border: 2px solid #333;
                border-radius: 4px;
                padding: 8px;
            }}
        """
        self.subtitle_label.setStyleSheet(style)

# ---ADVANCED SETTINGS DIALOG--- #
class AdvancedSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Advanced Subtitle Settings")
        self.setModal(True)
        self.resize(600, 500)
        
        layout = QVBoxLayout(self)
        
        # Enable custom settings checkbox
        self.use_custom_cb = QCheckBox("Use Custom Settings")
        self.use_custom_cb.setToolTip("Enable this to use custom subtitle and video settings")
        self.use_custom_cb.stateChanged.connect(self.toggle_custom_settings)
        layout.addWidget(self.use_custom_cb)
        
        # Settings container
        self.settings_widget = QWidget()
        settings_layout = QHBoxLayout(self.settings_widget)
        
        # Left side - Settings
        settings_form = QFormLayout()
        
        # Font size
        self.font_size = QSpinBox()
        self.font_size.setRange(8, 48)
        self.font_size.setValue(16)
        self.font_size.setToolTip("Size of subtitle text")
        self.font_size.valueChanged.connect(self.update_preview)
        settings_form.addRow("Font Size:", self.font_size)
        
        # Font selection
        font_layout = QHBoxLayout()
        self.font_name = QLineEdit("Arial")
        self.font_name.setToolTip("Font family name")
        self.font_name.textChanged.connect(self.update_preview)
        font_btn = QPushButton("Choose Font")
        font_btn.setToolTip("Select font from system fonts")
        font_btn.clicked.connect(self.choose_font)
        font_layout.addWidget(self.font_name)
        font_layout.addWidget(font_btn)
        settings_form.addRow("Font:", font_layout)
        
        # Font color
        color_layout = QHBoxLayout()
        self.font_color = QLineEdit("#FFFFFF")
        self.font_color.setToolTip("Subtitle text color in hex format")
        self.font_color.textChanged.connect(self.update_preview)
        color_btn = QPushButton("Choose Color")
        color_btn.setToolTip("Pick color from color dialog")
        color_btn.clicked.connect(self.choose_color)
        color_layout.addWidget(self.font_color)
        color_layout.addWidget(color_btn)
        settings_form.addRow("Font Color:", color_layout)
        
        # Border style
        self.border_style = QComboBox()
        self.border_style.addItems(["1 - Outline", "2 - Drop Shadow", "3 - Box Background", "4 - Outline + Drop Shadow"])
        self.border_style.setCurrentIndex(2)
        self.border_style.setToolTip("Subtitle border/background style")
        self.border_style.currentTextChanged.connect(self.update_preview)
        settings_form.addRow("Border Style:", self.border_style)
        
        # Video quality (CRF)
        crf_layout = QHBoxLayout()
        self.crf_slider = QSlider(Qt.Orientation.Horizontal)
        self.crf_slider.setRange(18, 28)
        self.crf_slider.setValue(23)
        self.crf_slider.setToolTip("Lower values = higher quality, larger file size")
        self.crf_label = QLabel("23 (Balanced)")
        self.crf_slider.valueChanged.connect(self.update_crf_label)
        crf_layout.addWidget(self.crf_slider)
        crf_layout.addWidget(self.crf_label)
        settings_form.addRow("Video Quality (CRF):", crf_layout)
        
        settings_layout.addLayout(settings_form)
        
        # Right side - Preview
        preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(preview_group)
        self.preview_widget = SubtitlePreviewWidget()
        preview_layout.addWidget(self.preview_widget)
        settings_layout.addWidget(preview_group)
        
        layout.addWidget(self.settings_widget)
        
        # Buttons
        button_layout = QHBoxLayout()
        ok_btn = QPushButton("Apply Settings")
        ok_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton))
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCancelButton))
        ok_btn.clicked.connect(self.accept)
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(ok_btn)
        button_layout.addWidget(cancel_btn)
        layout.addWidget(QWidget())  # Spacer
        layout.addLayout(button_layout)
        
        # Initially disable settings
        self.settings_widget.setEnabled(False)
    
    def toggle_custom_settings(self, state):
        self.settings_widget.setEnabled(state == Qt.CheckState.Checked.value)
    
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
    
    def update_preview(self):
        if hasattr(self, 'preview_widget'):
            self.preview_widget.update_preview(
                self.font_size.value(),
                self.font_color.text(),
                self.font_name.text()
            )
    
    def get_settings(self):
        return {
            'use_custom': self.use_custom_cb.isChecked(),
            'font_size': self.font_size.value(),
            'font_name': self.font_name.text(),
            'font_color': self.font_color.text(),
            'border_style': self.border_style.currentIndex() + 1,
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
        self.subtitle_settings = {'use_custom': False}
        
        self.setWindowTitle("HardSubber Automator v4.2")
        self.setGeometry(100, 100, 360, 640)
        self.setMinimumSize(360, 600)

        self.apply_modern_theme()
        self.setup_ui()
        self.setup_menu()
        self.setup_status_bar()
        self.check_ffmpeg()
        self.load_settings()

    def apply_modern_theme(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e9ecef;
                border-radius: 8px;
                margin-top: 15px;
                padding-top: 15px;
                background-color: white;
                color: #2c3e50;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #495057;
                font-size: 13px;
            }
            QTableWidget {
                gridline-color: #dee2e6;
                background-color: white;
                alternate-background-color: #f8f9fa;
                border: 1px solid #dee2e6;
                border-radius: 6px;
                color: #2c3e50;
                selection-background-color: #007bff;
                selection-color: white;
            }
            QTableWidget::item {
                padding: 12px 8px;
                border-bottom: 1px solid #dee2e6;
                border-right: 1px solid #dee2e6;
                color: #2c3e50;
            }
            QTableWidget::item:selected {
                background-color: #007bff;
                color: white;
            }
            QTableWidget::item:hover {
                background-color: #e9ecef;
            }
            QHeaderView::section {
                background-color: #495057;
                padding: 10px 8px;
                border: 1px solid #343a40;
                color: white;
                font-weight: bold;
                font-size: 12px;
            }
            QHeaderView::section:hover {
                background-color: #5a6268;
            }
            QStatusBar {
                background-color: #343a40;
                color: white;
                font-weight: bold;
                border-top: 1px solid #dee2e6;
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
                border: 2px solid #e9ecef;
                border-radius: 6px;
                padding: 5px;
                background-color: white;
                color: #2c3e50;
            }
            QComboBox:focus {
                border-color: #007bff;
            }
            QLabel {
                color: #2c3e50;
            }
            QProgressBar {
                border: 2px solid #e9ecef;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                height: 25px;
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QProgressBar::chunk {
                background-color: #28a745;
                border-radius: 6px;
            }
        """)

    def setup_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("File")
        
        open_action = QAction("Open Input Folder", self)
        open_action.setShortcut("Ctrl+O")
        open_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DirOpenIcon))
        open_action.triggered.connect(self.select_input_folder)
        file_menu.addAction(open_action)
        
        settings_action = QAction("Advanced Settings", self)
        settings_action.setShortcut("Ctrl+,")
        settings_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        settings_action.triggered.connect(self.show_advanced_settings)
        file_menu.addAction(settings_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCloseButton))
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        help_menu = menubar.addMenu("Help")
        
        about_action = QAction("About", self)
        about_action.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MessageBoxInformation))
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready - Select an input folder to begin")

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # Top controls
        controls_layout = QHBoxLayout()
        
        self.input_folder_btn = QPushButton("Open Input Folder")
        self.input_folder_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DirOpenIcon))
        self.input_folder_btn.setToolTip("Select folder containing video and subtitle files")
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        controls_layout.addWidget(self.input_folder_btn)

        self.output_folder_btn = QPushButton("Set Output Folder")
        self.output_folder_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogSaveButton))
        self.output_folder_btn.setToolTip("Choose where to save processed videos (optional)")
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        controls_layout.addWidget(self.output_folder_btn)

        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Encoding Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        self.speed_combo.setCurrentText("medium")
        self.speed_combo.setToolTip("Faster = larger files, Slower = smaller files")
        speed_layout.addWidget(self.speed_combo)
        controls_layout.addLayout(speed_layout)

        self.settings_btn = QPushButton("Advanced Settings")
        self.settings_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        self.settings_btn.setToolTip("Configure subtitle appearance and video quality")
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
        self.toggle_selection_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton))
        self.toggle_selection_btn.setToolTip("Toggle selection of all available video-subtitle pairs")
        self.toggle_selection_btn.clicked.connect(self.toggle_all_selection)
        self.toggle_selection_btn.setEnabled(False)
        selection_layout.addWidget(self.toggle_selection_btn)
        selection_layout.addStretch()
        files_layout.addLayout(selection_layout)

        self.files_table = QTableWidget()
        self.files_table.setColumnCount(5)
        self.files_table.setHorizontalHeaderLabels(["✓", "Video File", "Subtitle File", "Status", "Actions"])
        
        # Configure table like file explorer
        header = self.files_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)
        
        self.files_table.setColumnWidth(0, 50)
        self.files_table.setColumnWidth(4, 80)
        self.files_table.setAlternatingRowColors(True)
        self.files_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.files_table.setSortingEnabled(True)
        self.files_table.verticalHeader().setVisible(False)
        self.files_table.setShowGrid(True)
        
        files_layout.addWidget(self.files_table)
        main_layout.addWidget(files_group)

        # Progress section
        progress_group = QGroupBox("Processing Progress")
        progress_layout = QVBoxLayout(progress_group)

        self.current_video_label = QLabel("Ready to process videos...")
        self.current_video_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
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
        self.start_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaPlay))
        self.start_btn.setStyleSheet("QPushButton { background-color: #28a745; } QPushButton:hover { background-color: #218838; }")
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        button_layout.addWidget(self.start_btn)

        self.skip_btn = QPushButton("Skip Current")
        self.skip_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaSkipForward))
        self.skip_btn.setStyleSheet("QPushButton { background-color: #ffc107; } QPushButton:hover { background-color: #e0a800; }")
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setEnabled(False)
        button_layout.addWidget(self.skip_btn)

        self.stop_btn = QPushButton("Stop Processing")
        self.stop_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_MediaStop))
        self.stop_btn.setStyleSheet("QPushButton { background-color: #dc3545; } QPushButton:hover { background-color: #c82333; }")
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        button_layout.addWidget(self.stop_btn)

        main_layout.addLayout(button_layout)

    def show_advanced_settings(self):
        dialog = AdvancedSettingsDialog(self)
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.subtitle_settings = dialog.get_settings()
            self.save_settings()

    def show_about(self):
        QMessageBox.about(self, "About HardSubber Automator",
                         "HardSubber Automator v4.2\n\n"
                         "A powerful tool for automatically hard-coding subtitles into video files.\n\n"
                         "Features:\n"
                         "• Automatic subtitle matching\n"
                         "• Customizable subtitle appearance\n"
                         "• Batch processing\n"
                         "• Real-time progress tracking\n\n"
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

            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_ui_state)
            self.files_table.setCellWidget(row, 0, checkbox)

            video_item = QTableWidgetItem(video_name)
            video_item.setData(Qt.ItemDataRole.UserRole, video_path)
            video_item.setToolTip(video_path)
            self.files_table.setItem(row, 1, video_item)

            subtitle_path = self.find_matching_subtitle(video_path, subtitle_files)
            if subtitle_path:
                subtitle_item = QTableWidgetItem(os.path.basename(subtitle_path))
                subtitle_item.setData(Qt.ItemDataRole.UserRole, subtitle_path)
                subtitle_item.setToolTip(subtitle_path)
                subtitle_item.setBackground(QColor(40, 167, 69, 50))
                checkbox.setChecked(True)
                status_item = QTableWidgetItem("Ready")
                status_item.setBackground(QColor(40, 167, 69, 50))
            else:
                subtitle_item = QTableWidgetItem("No subtitle found")
                subtitle_item.setData(Qt.ItemDataRole.UserRole, None)
                subtitle_item.setBackground(QColor(220, 53, 69, 50))
                status_item = QTableWidgetItem("No subtitle")
                status_item.setBackground(QColor(220, 53, 69, 50))

            self.files_table.setItem(row, 2, subtitle_item)
            self.files_table.setItem(row, 3, status_item)

            browse_btn = QPushButton("Browse...")
            browse_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_FileDialogDetailedView))
            browse_btn.setToolTip("Select a different subtitle file")
            browse_btn.clicked.connect(lambda checked, r=row: self.browse_subtitle(r))
            self.files_table.setCellWidget(row, 4, browse_btn)

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
            subtitle_item.setData(Qt.ItemDataRole.UserRole, file_path)
            subtitle_item.setToolTip(file_path)
            subtitle_item.setBackground(QColor(40, 167, 69, 50))
            self.files_table.setItem(row, 2, subtitle_item)

            status_item = QTableWidgetItem("Ready")
            status_item.setBackground(QColor(40, 167, 69, 50))
            self.files_table.setItem(row, 3, status_item)

            checkbox = self.files_table.cellWidget(row, 0)
            checkbox.setChecked(True)

            self.video_pairs[row]['subtitle_path'] = file_path

    def toggle_all_selection(self):
        # Check current state
        checked_count = 0
        total_available = 0
        
        for row in range(self.files_table.rowCount()):
            subtitle_item = self.files_table.item(row, 2)
            if subtitle_item and subtitle_item.data(Qt.ItemDataRole.UserRole):
                total_available += 1
                checkbox = self.files_table.cellWidget(row, 0)
                if checkbox.isChecked():
                    checked_count += 1
        
        # If all are checked, uncheck all. Otherwise, check all available
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

        self.start_btn.setEnabled(enabled_count > 0)
        
        if enabled_count > 0:
            self.start_btn.setText(f"Start Processing ({enabled_count} videos)")
        else:
            self.start_btn.setText("Start Processing")
        
        # Update toggle button text
        if total_available > 0:
            if enabled_count == total_available:
                self.toggle_selection_btn.setText("Unselect All")
                self.toggle_selection_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogCancelButton))
            else:
                self.toggle_selection_btn.setText(f"Select All ({total_available} available)")
                self.toggle_selection_btn.setIcon(self.style().standardIcon(self.style().StandardPixmap.SP_DialogApplyButton))

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
                    status_item.setBackground(QColor(0, 123, 255, 50))
                    self.files_table.setItem(row, 3, status_item)

        if not enabled_pairs:
            QMessageBox.warning(self, "No Videos Selected", 
                              "Please select at least one video-subtitle pair to process.")
            return

        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
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

    def stop_processing(self):
        if self.processor_thread:
            self.processor_thread.stop()
            self.current_video_label.setText("Stopping processing...")
            self.skip_btn.setEnabled(False)
            self.status_bar.showMessage("Stopping processing...")

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

        # Update table status
        for row in range(self.files_table.rowCount()):
            video_item = self.files_table.item(row, 1)
            if video_item and os.path.basename(video_item.data(Qt.ItemDataRole.UserRole)) == video_name:
                status_item = QTableWidgetItem(f"Processing ({percent}%)")
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
                    status_item.setBackground(QColor(40, 167, 69, 50))
                    status_item.setToolTip(f"Output: {output_path}")
                else:
                    status_item = QTableWidgetItem("Failed")
                    status_item.setBackground(QColor(220, 53, 69, 50))
                self.files_table.setItem(row, 3, status_item)
                break

        if success:
            self.status_bar.showMessage(f"Completed: {video_name}")

    def processing_completed(self, success_count, total_count):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.current_video_label.setText(f"Processing completed! {success_count}/{total_count} successful")
        self.eta_label.setText("")
        self.status_bar.showMessage(f"All processing completed: {success_count}/{total_count} successful")

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
                winsound.Beep(800, 1000)
            else:
                print("\a")
        except:
            pass

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
    app.setApplicationName("HardSubber Automator v4.2")
    app.setOrganizationName("Nexus")
    app.setApplicationVersion("4.2")
    app.setStyle('Fusion')

    window = HardSubberGUI()
    window.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()
