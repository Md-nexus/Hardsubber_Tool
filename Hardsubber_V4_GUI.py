
#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.0 ║
# ║  GUI Edition with PyQt6    ║
# ║  by Nexus // MD_nexus      ║
# ╚════════════════════════════╝

import sys
import os
import re
import time
import difflib
import subprocess
import threading
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
    QGridLayout, QLabel, QPushButton, QComboBox, QProgressBar, 
    QFileDialog, QScrollArea, QFrame, QTextEdit, QGroupBox,
    QMessageBox, QSplitter, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QFont, QPixmap, QIcon, QPalette, QColor

class VideoProcessor(QThread):
    progress_updated = pyqtSignal(int, str, float, float)
    video_completed = pyqtSignal(str, bool)
    all_completed = pyqtSignal()
    
    def __init__(self, video_pairs, output_folder, speed_preset):
        super().__init__()
        self.video_pairs = video_pairs
        self.output_folder = output_folder
        self.speed_preset = speed_preset
        self.is_running = True
    
    def stop(self):
        self.is_running = False
    
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
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
            )
            return float(result.stdout.strip())
        except:
            return None
    
    def break_proof_filename(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)
    
    def run(self):
        for i, (video_path, subtitle_path) in enumerate(self.video_pairs):
            if not self.is_running:
                break
                
            video_name = os.path.basename(video_path)
            name, ext = os.path.splitext(video_name)
            safe_name = self.break_proof_filename(name)
            
            if self.output_folder:
                output_path = os.path.join(self.output_folder, f"{safe_name}_subbed.mp4")
            else:
                output_path = os.path.join(os.path.dirname(video_path), f"{safe_name}_subbed.mp4")
            
            # Get video duration for progress calculation
            total_duration = self.get_duration(video_path)
            if not total_duration:
                self.video_completed.emit(video_name, False)
                continue
            
            # Get input file sizes
            video_size = self.get_file_size_mb(video_path)
            subtitle_size = self.get_file_size_mb(subtitle_path)
            input_total_size = video_size + subtitle_size
            
            # Prepare FFmpeg command
            subtitle_filter_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{subtitle_filter_path}'",
                "-c:v", "libx264", "-preset", self.speed_preset,
                "-c:a", "copy", output_path
            ]
            
            try:
                process = subprocess.Popen(
                    cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
                    universal_newlines=True, bufsize=0
                )
                
                for line in process.stderr:
                    if not self.is_running:
                        process.terminate()
                        break
                        
                    if "time=" in line:
                        match = re.search(r"time=(\d+):(\d+):(\d+.\d)", line)
                        if match:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = (current_sec / total_duration) * 100
                            output_size = self.get_file_size_mb(output_path)
                            
                            self.progress_updated.emit(
                                int(percent), video_name, output_size, input_total_size
                            )
                
                process.wait()
                success = process.returncode == 0 and self.is_running
                self.video_completed.emit(video_name, success)
                
            except Exception as e:
                self.video_completed.emit(video_name, False)
        
        if self.is_running:
            self.all_completed.emit()

class VideoSubtitlePair(QFrame):
    subtitle_changed = pyqtSignal()
    
    def __init__(self, video_path, parent=None):
        super().__init__(parent)
        self.video_path = video_path
        self.subtitle_path = None
        self.parent_window = parent
        
        self.setFrameStyle(QFrame.Shape.Box)
        self.setStyleSheet("""
            QFrame {
                border: 2px solid #cccccc;
                border-radius: 8px;
                margin: 5px;
                padding: 10px;
                background-color: #f9f9f9;
            }
        """)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QHBoxLayout(self)
        
        # Video info section
        video_section = QVBoxLayout()
        video_label = QLabel("📹 Video:")
        video_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        video_name = QLabel(os.path.basename(self.video_path))
        video_name.setWordWrap(True)
        video_name.setStyleSheet("color: #2c3e50; font-size: 11px;")
        
        video_section.addWidget(video_label)
        video_section.addWidget(video_name)
        
        # Subtitle section
        subtitle_section = QVBoxLayout()
        subtitle_label = QLabel("📄 Subtitle:")
        subtitle_label.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        
        self.subtitle_display = QLabel("No subtitle selected")
        self.subtitle_display.setWordWrap(True)
        self.subtitle_display.setStyleSheet("color: #e74c3c; font-style: italic; font-size: 11px;")
        
        self.select_subtitle_btn = QPushButton("Browse...")
        self.select_subtitle_btn.setMaximumWidth(80)
        self.select_subtitle_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 4px;
                padding: 5px;
                font-size: 10px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        self.select_subtitle_btn.clicked.connect(self.select_subtitle)
        
        subtitle_section.addWidget(subtitle_label)
        subtitle_section.addWidget(self.subtitle_display)
        subtitle_section.addWidget(self.select_subtitle_btn)
        
        # Enable checkbox
        self.enable_checkbox = QCheckBox("Process")
        self.enable_checkbox.setChecked(False)
        self.enable_checkbox.setStyleSheet("QCheckBox { font-weight: bold; color: #27ae60; }")
        
        layout.addLayout(video_section, 2)
        layout.addLayout(subtitle_section, 2)
        layout.addWidget(self.enable_checkbox, 0, Qt.AlignmentFlag.AlignCenter)
    
    def set_subtitle(self, subtitle_path):
        self.subtitle_path = subtitle_path
        if subtitle_path:
            self.subtitle_display.setText(os.path.basename(subtitle_path))
            self.subtitle_display.setStyleSheet("color: #27ae60; font-size: 11px;")
            self.enable_checkbox.setChecked(True)
        else:
            self.subtitle_display.setText("No subtitle selected")
            self.subtitle_display.setStyleSheet("color: #e74c3c; font-style: italic; font-size: 11px;")
            self.enable_checkbox.setChecked(False)
        self.subtitle_changed.emit()
    
    def select_subtitle(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File",
            os.path.dirname(self.video_path),
            "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        if file_path:
            self.set_subtitle(file_path)
    
    def is_enabled(self):
        return self.enable_checkbox.isChecked() and self.subtitle_path

class HardSubberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_pairs = []
        self.processor_thread = None
        self.output_folder = None
        
        self.setWindowTitle("HardSubber Automator v4.0 - GUI Edition")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ecf0f1;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #bdc3c7;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 15px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 10px 0 10px;
                color: #2c3e50;
            }
        """)
        
        self.setup_ui()
        self.check_ffmpeg()
    
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Top controls section
        controls_group = QGroupBox("📂 File Selection & Settings")
        controls_layout = QGridLayout(controls_group)
        
        # Input folder selection
        controls_layout.addWidget(QLabel("Input Folder:"), 0, 0)
        self.input_folder_btn = QPushButton("Browse Input Folder...")
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        controls_layout.addWidget(self.input_folder_btn, 0, 1)
        
        self.input_folder_label = QLabel("No folder selected")
        self.input_folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        controls_layout.addWidget(self.input_folder_label, 0, 2)
        
        # Output folder selection
        controls_layout.addWidget(QLabel("Output Folder:"), 1, 0)
        self.output_folder_btn = QPushButton("Browse Output Folder...")
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        controls_layout.addWidget(self.output_folder_btn, 1, 1)
        
        self.output_folder_label = QLabel("Same as input folder")
        self.output_folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        controls_layout.addWidget(self.output_folder_label, 1, 2)
        
        # Speed preset selection
        controls_layout.addWidget(QLabel("Encoding Speed:"), 2, 0)
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["ultrafast", "fast", "medium", "slow"])
        self.speed_combo.setCurrentText("medium")
        self.speed_combo.setToolTip("Faster = larger file size, Slower = smaller file size")
        controls_layout.addWidget(self.speed_combo, 2, 1)
        
        # Auto-match button
        self.auto_match_btn = QPushButton("🔍 Auto-Match Subtitles")
        self.auto_match_btn.clicked.connect(self.auto_match_subtitles)
        self.auto_match_btn.setEnabled(False)
        controls_layout.addWidget(self.auto_match_btn, 2, 2)
        
        main_layout.addWidget(controls_group)
        
        # Video pairs section
        pairs_group = QGroupBox("📹 Video and Subtitle Pairs")
        pairs_layout = QVBoxLayout(pairs_group)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self.pairs_widget = QWidget()
        self.pairs_layout = QVBoxLayout(self.pairs_widget)
        self.pairs_layout.addStretch()
        
        self.scroll_area.setWidget(self.pairs_widget)
        pairs_layout.addWidget(self.scroll_area)
        
        main_layout.addWidget(pairs_group)
        
        # Progress section
        progress_group = QGroupBox("⚡ Processing Progress")
        progress_layout = QVBoxLayout(progress_group)
        
        self.current_video_label = QLabel("Ready to process...")
        self.current_video_label.setStyleSheet("font-weight: bold; color: #2c3e50;")
        progress_layout.addWidget(self.current_video_label)
        
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #bdc3c7;
                border-radius: 5px;
                text-align: center;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: #3498db;
                border-radius: 3px;
            }
        """)
        progress_layout.addWidget(self.progress_bar)
        
        self.size_info_label = QLabel("")
        self.size_info_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        progress_layout.addWidget(self.size_info_label)
        
        main_layout.addWidget(progress_group)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("🚀 Start Processing")
        self.start_btn.setMinimumHeight(40)
        self.start_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #229954;
            }
            QPushButton:disabled {
                background-color: #bdc3c7;
            }
        """)
        self.start_btn.clicked.connect(self.start_processing)
        self.start_btn.setEnabled(False)
        
        self.stop_btn = QPushButton("⏹️ Stop Processing")
        self.stop_btn.setMinimumHeight(40)
        self.stop_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        self.stop_btn.clicked.connect(self.stop_processing)
        self.stop_btn.setEnabled(False)
        
        button_layout.addWidget(self.start_btn)
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
    
    def check_ffmpeg(self):
        try:
            subprocess.run(["ffmpeg", "-version"], 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL, 
                         check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            QMessageBox.critical(self, "FFmpeg Not Found", 
                               "FFmpeg is required but not found in your system PATH.\n"
                               "Please install FFmpeg to use this application.")
            sys.exit(1)
    
    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.load_input_folder(folder)
    
    def load_input_folder(self, folder):
        self.input_folder_label.setText(folder)
        self.input_folder_label.setStyleSheet("color: #27ae60;")
        
        # Clear existing pairs
        for i in reversed(range(self.pairs_layout.count() - 1)):
            child = self.pairs_layout.itemAt(i).widget()
            if child:
                child.setParent(None)
        
        self.video_pairs.clear()
        
        # Find video files
        video_exts = [".mp4", ".mkv", ".mov"]
        video_files = []
        
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in video_exts):
                video_files.append(os.path.join(folder, file))
        
        video_files.sort()
        
        # Create pairs widgets
        for video_path in video_files:
            pair_widget = VideoSubtitlePair(video_path, self)
            pair_widget.subtitle_changed.connect(self.update_start_button)
            self.pairs_layout.insertWidget(self.pairs_layout.count() - 1, pair_widget)
            self.video_pairs.append(pair_widget)
        
        self.auto_match_btn.setEnabled(len(self.video_pairs) > 0)
        self.update_start_button()
        
        if not video_files:
            QMessageBox.information(self, "No Videos Found", 
                                  "No supported video files found in the selected folder.\n"
                                  "Supported formats: MP4, MKV, MOV")
    
    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_folder_label.setText(folder)
            self.output_folder_label.setStyleSheet("color: #27ae60;")
        else:
            self.output_folder = None
            self.output_folder_label.setText("Same as input folder")
            self.output_folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
    
    def auto_match_subtitles(self):
        if not self.video_pairs:
            return
        
        # Get folder from first video
        folder = os.path.dirname(self.video_pairs[0].video_path)
        subtitle_exts = [".srt", ".vtt"]
        
        # Find all subtitle files
        subtitle_files = []
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in subtitle_exts):
                subtitle_files.append(os.path.join(folder, file))
        
        matched_count = 0
        
        for pair in self.video_pairs:
            video_name = os.path.splitext(os.path.basename(pair.video_path))[0]
            
            # Try to find matching subtitle
            best_match = None
            best_score = 0
            
            for subtitle_path in subtitle_files:
                subtitle_name = os.path.splitext(os.path.basename(subtitle_path))[0]
                
                # Calculate similarity
                similarity = difflib.SequenceMatcher(None, 
                                                   video_name.lower(), 
                                                   subtitle_name.lower()).ratio()
                
                if similarity > best_score and similarity > 0.3:
                    best_score = similarity
                    best_match = subtitle_path
            
            if best_match:
                pair.set_subtitle(best_match)
                matched_count += 1
        
        QMessageBox.information(self, "Auto-Match Complete", 
                              f"Automatically matched {matched_count} out of {len(self.video_pairs)} videos.")
        
        self.update_start_button()
    
    def update_start_button(self):
        enabled_pairs = sum(1 for pair in self.video_pairs if pair.is_enabled())
        self.start_btn.setEnabled(enabled_pairs > 0)
        
        if enabled_pairs > 0:
            self.start_btn.setText(f"🚀 Start Processing ({enabled_pairs} videos)")
        else:
            self.start_btn.setText("🚀 Start Processing")
    
    def start_processing(self):
        enabled_pairs = [(pair.video_path, pair.subtitle_path) 
                        for pair in self.video_pairs if pair.is_enabled()]
        
        if not enabled_pairs:
            QMessageBox.warning(self, "No Videos Selected", 
                              "Please select at least one video-subtitle pair to process.")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # Start processing thread
        self.processor_thread = VideoProcessor(
            enabled_pairs, self.output_folder, self.speed_combo.currentText()
        )
        self.processor_thread.progress_updated.connect(self.update_progress)
        self.processor_thread.video_completed.connect(self.video_completed)
        self.processor_thread.all_completed.connect(self.processing_completed)
        self.processor_thread.start()
    
    def stop_processing(self):
        if self.processor_thread:
            self.processor_thread.stop()
            self.current_video_label.setText("Stopping...")
    
    def update_progress(self, percent, video_name, output_size, input_size):
        self.progress_bar.setValue(percent)
        self.current_video_label.setText(f"Processing: {video_name}")
        
        if input_size > 0:
            size_ratio = (output_size / input_size) * 100
            self.size_info_label.setText(
                f"Output: {output_size:.1f}MB ({size_ratio:.1f}% of input size)"
            )
    
    def video_completed(self, video_name, success):
        status = "✅ Completed" if success else "❌ Failed"
        self.current_video_label.setText(f"{status}: {video_name}")
    
    def processing_completed(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.current_video_label.setText("🎉 All processing completed!")
        
        QMessageBox.information(self, "Processing Complete", 
                              "All video processing has been completed successfully!")

def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HardSubber Automator v4.0")
    app.setOrganizationName("Nexus")
    app.setApplicationVersion("4.0")
    
    # Set application style
    app.setStyle('Fusion')
    
    window = HardSubberGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
