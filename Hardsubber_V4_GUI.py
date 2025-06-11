
#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.0 ║
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
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtCore import QUrl

# ---VIDEO PROCESSOR THREAD CLASS--- #
class VideoProcessor(QThread):
    progress_updated = pyqtSignal(int, str, float, float, float)
    video_completed = pyqtSignal(str, bool)
    all_completed = pyqtSignal()
    skip_current = pyqtSignal()
    
    def __init__(self, video_pairs, output_folder, speed_preset):
        super().__init__()
        self.video_pairs = video_pairs
        self.output_folder = output_folder
        self.speed_preset = speed_preset
        self.is_running = True
        self.skip_requested = False
    
    def stop(self):
        self.is_running = False
    
    def skip(self):
        self.skip_requested = True
    
    # ---GET FILE SIZE--- #
    def get_file_size_mb(self, path):
        try:
            return os.path.getsize(path) / (1024 * 1024)
        except:
            return 0.0
    
    # ---GET VIDEO DURATION--- #
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
    
    # ---BREAK-PROOF FILE NAME--- #
    def break_proof_filename(self, name):
        return re.sub(r'[<>:"/\\|?*]', "_", name)
    
    # ---MAIN PROCESSING THREAD--- #
    def run(self):
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
            
            # --[Get video duration for progress calculation]-- #
            total_duration = self.get_duration(video_path)
            if not total_duration:
                self.video_completed.emit(video_name, False)
                continue
            
            # --[Get input file sizes]-- #
            video_size = self.get_file_size_mb(video_path)
            subtitle_size = self.get_file_size_mb(subtitle_path)
            input_total_size = video_size + subtitle_size
            
            # --[Prepare FFmpeg command]-- #
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
                    if not self.is_running or self.skip_requested:
                        process.terminate()
                        if self.skip_requested:
                            self.video_completed.emit(video_name, False)
                        break
                        
                    if "time=" in line:
                        match = re.search(r"time=(\d+):(\d+):(\d+.\d)", line)
                        if match:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = (current_sec / total_duration) * 100
                            output_size = self.get_file_size_mb(output_path)
                            
                            self.progress_updated.emit(
                                int(percent), video_name, output_size, input_total_size, video_size
                            )
                
                if not self.skip_requested:
                    process.wait()
                    success = process.returncode == 0 and self.is_running
                    self.video_completed.emit(video_name, success)
                
            except Exception as e:
                self.video_completed.emit(video_name, False)
        
        if self.is_running:
            self.all_completed.emit()

# ---MAIN GUI CLASS--- #
class HardSubberGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_pairs = []
        self.processor_thread = None
        self.output_folder = None
        self.current_folder = None
        
        self.setWindowTitle("HardSubber Automator v4.0 - GUI Edition")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(900, 700)
        
        # --[Set application style]-- #
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
            QTableWidget {
                gridline-color: #bdc3c7;
                background-color: white;
                alternate-background-color: #f8f9fa;
            }
            QTableWidget::item {
                padding: 8px;
                border: none;
            }
            QTableWidget::item:selected {
                background-color: #3498db;
                color: white;
            }
        """)
        
        self.setup_ui()
        self.check_ffmpeg()
    
    # ---SETUP UI COMPONENTS--- #
    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # ---TOP CONTROLS SECTION--- #
        controls_layout = QHBoxLayout()
        
        # --[Input folder button]-- #
        self.input_folder_btn = QPushButton("📂 Browse Input Folder")
        self.input_folder_btn.setMinimumHeight(35)
        self.input_folder_btn.clicked.connect(self.select_input_folder)
        controls_layout.addWidget(self.input_folder_btn)
        
        # --[Output folder button]-- #
        self.output_folder_btn = QPushButton("📁 Browse Output Folder")
        self.output_folder_btn.setMinimumHeight(35)
        self.output_folder_btn.clicked.connect(self.select_output_folder)
        controls_layout.addWidget(self.output_folder_btn)
        
        # --[Speed preset]-- #
        speed_layout = QHBoxLayout()
        speed_layout.addWidget(QLabel("Speed:"))
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["ultrafast", "fast", "medium", "slow"])
        self.speed_combo.setCurrentText("medium")
        self.speed_combo.setToolTip("Faster = larger file size, Slower = smaller file size")
        speed_layout.addWidget(self.speed_combo)
        controls_layout.addLayout(speed_layout)
        
        # --[Select/Unselect buttons]-- #
        self.select_all_btn = QPushButton("✅ Select All")
        self.select_all_btn.setMinimumHeight(35)
        self.select_all_btn.clicked.connect(self.select_all)
        self.select_all_btn.setEnabled(False)
        controls_layout.addWidget(self.select_all_btn)
        
        self.unselect_all_btn = QPushButton("❌ Unselect All")
        self.unselect_all_btn.setMinimumHeight(35)
        self.unselect_all_btn.clicked.connect(self.unselect_all)
        self.unselect_all_btn.setEnabled(False)
        controls_layout.addWidget(self.unselect_all_btn)
        
        main_layout.addLayout(controls_layout)
        
        # ---FOLDER DISPLAY--- #
        folder_layout = QHBoxLayout()
        folder_layout.addWidget(QLabel("Input:"))
        self.input_folder_label = QLabel("No folder selected")
        self.input_folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        folder_layout.addWidget(self.input_folder_label)
        
        folder_layout.addWidget(QLabel("Output:"))
        self.output_folder_label = QLabel("Same as input folder")
        self.output_folder_label.setStyleSheet("color: #7f8c8d; font-style: italic;")
        folder_layout.addWidget(self.output_folder_label)
        
        main_layout.addLayout(folder_layout)
        
        # ---VIDEO PAIRS TABLE--- #
        pairs_group = QGroupBox("📹 Video and Subtitle Pairs")
        pairs_layout = QVBoxLayout(pairs_group)
        
        self.pairs_table = QTableWidget()
        self.pairs_table.setColumnCount(4)
        self.pairs_table.setHorizontalHeaderLabels(["Process", "Video File", "Subtitle File", "Browse"])
        self.pairs_table.horizontalHeader().setStretchLastSection(False)
        self.pairs_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.pairs_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.pairs_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.pairs_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)
        self.pairs_table.setColumnWidth(0, 80)
        self.pairs_table.setColumnWidth(3, 100)
        self.pairs_table.setAlternatingRowColors(True)
        
        pairs_layout.addWidget(self.pairs_table)
        main_layout.addWidget(pairs_group)
        
        # ---PROGRESS SECTION--- #
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
        
        # ---ACTION BUTTONS--- #
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
        button_layout.addWidget(self.start_btn)
        
        self.skip_btn = QPushButton("⏭️ Skip Current")
        self.skip_btn.setMinimumHeight(40)
        self.skip_btn.setStyleSheet("""
            QPushButton {
                background-color: #f39c12;
                color: white;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #e67e22;
            }
        """)
        self.skip_btn.clicked.connect(self.skip_current)
        self.skip_btn.setEnabled(False)
        button_layout.addWidget(self.skip_btn)
        
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
        button_layout.addWidget(self.stop_btn)
        
        main_layout.addLayout(button_layout)
    
    # ---CHECK FFMPEG INSTALLATION--- #
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
    
    # ---SELECT INPUT FOLDER--- #
    def select_input_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.load_input_folder(folder)
    
    # ---LOAD INPUT FOLDER--- #
    def load_input_folder(self, folder):
        self.current_folder = folder
        self.input_folder_label.setText(folder)
        self.input_folder_label.setStyleSheet("color: #27ae60;")
        
        # --[Clear existing table]-- #
        self.pairs_table.setRowCount(0)
        self.video_pairs.clear()
        
        # --[Find video files]-- #
        video_exts = [".mp4", ".mkv", ".mov"]
        video_files = []
        
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in video_exts):
                video_files.append(os.path.join(folder, file))
        
        video_files.sort()
        
        # --[Find subtitle files for auto-matching]-- #
        subtitle_exts = [".srt", ".vtt"]
        subtitle_files = []
        for file in os.listdir(folder):
            if any(file.lower().endswith(ext) for ext in subtitle_exts):
                subtitle_files.append(os.path.join(folder, file))
        
        # --[Create table rows]-- #
        self.pairs_table.setRowCount(len(video_files))
        
        for row, video_path in enumerate(video_files):
            video_name = os.path.basename(video_path)
            
            # --[Process checkbox]-- #
            checkbox = QCheckBox()
            checkbox.stateChanged.connect(self.update_start_button)
            self.pairs_table.setCellWidget(row, 0, checkbox)
            
            # --[Video file name]-- #
            video_item = QTableWidgetItem(video_name)
            video_item.setData(Qt.ItemDataRole.UserRole, video_path)
            self.pairs_table.setItem(row, 1, video_item)
            
            # --[Auto-match subtitle]-- #
            subtitle_path = self.find_matching_subtitle(video_path, subtitle_files)
            if subtitle_path:
                subtitle_item = QTableWidgetItem(os.path.basename(subtitle_path))
                subtitle_item.setData(Qt.ItemDataRole.UserRole, subtitle_path)
                subtitle_item.setBackground(QColor(231, 76, 60, 50))
                checkbox.setChecked(True)
            else:
                subtitle_item = QTableWidgetItem("No subtitle found")
                subtitle_item.setData(Qt.ItemDataRole.UserRole, None)
                subtitle_item.setBackground(QColor(231, 76, 60, 50))
            
            self.pairs_table.setItem(row, 2, subtitle_item)
            
            # --[Browse button]-- #
            browse_btn = QPushButton("Browse...")
            browse_btn.clicked.connect(lambda checked, r=row: self.browse_subtitle(r))
            self.pairs_table.setCellWidget(row, 3, browse_btn)
            
            self.video_pairs.append({
                'video_path': video_path,
                'subtitle_path': subtitle_path
            })
        
        self.select_all_btn.setEnabled(len(video_files) > 0)
        self.unselect_all_btn.setEnabled(len(video_files) > 0)
        self.update_start_button()
        
        if not video_files:
            QMessageBox.information(self, "No Videos Found", 
                                  "No supported video files found in the selected folder.\n"
                                  "Supported formats: MP4, MKV, MOV")
    
    # ---FIND MATCHING SUBTITLE--- #
    def find_matching_subtitle(self, video_path, subtitle_files):
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        best_match = None
        best_score = 0
        
        for subtitle_path in subtitle_files:
            subtitle_name = os.path.splitext(os.path.basename(subtitle_path))[0]
            
            # --[Calculate similarity]-- #
            similarity = difflib.SequenceMatcher(None, 
                                               video_name.lower(), 
                                               subtitle_name.lower()).ratio()
            
            if similarity > best_score and similarity > 0.3:
                best_score = similarity
                best_match = subtitle_path
        
        return best_match
    
    # ---BROWSE SUBTITLE--- #
    def browse_subtitle(self, row):
        video_path = self.pairs_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Subtitle File",
            os.path.dirname(video_path),
            "Subtitle Files (*.srt *.vtt);;All Files (*)"
        )
        if file_path:
            subtitle_item = QTableWidgetItem(os.path.basename(file_path))
            subtitle_item.setData(Qt.ItemDataRole.UserRole, file_path)
            subtitle_item.setBackground(QColor(39, 174, 96, 50))
            self.pairs_table.setItem(row, 2, subtitle_item)
            
            # --[Enable checkbox]-- #
            checkbox = self.pairs_table.cellWidget(row, 0)
            checkbox.setChecked(True)
            
            self.video_pairs[row]['subtitle_path'] = file_path
    
    # ---SELECT ALL--- #
    def select_all(self):
        for row in range(self.pairs_table.rowCount()):
            checkbox = self.pairs_table.cellWidget(row, 0)
            if self.pairs_table.item(row, 2).data(Qt.ItemDataRole.UserRole):
                checkbox.setChecked(True)
    
    # ---UNSELECT ALL--- #
    def unselect_all(self):
        for row in range(self.pairs_table.rowCount()):
            checkbox = self.pairs_table.cellWidget(row, 0)
            checkbox.setChecked(False)
    
    # ---SELECT OUTPUT FOLDER--- #
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
    
    # ---UPDATE START BUTTON--- #
    def update_start_button(self):
        enabled_count = 0
        for row in range(self.pairs_table.rowCount()):
            checkbox = self.pairs_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                subtitle_item = self.pairs_table.item(row, 2)
                if subtitle_item:
                    subtitle_path = subtitle_item.data(Qt.ItemDataRole.UserRole)
                    if subtitle_path:
                        enabled_count += 1
        
        self.start_btn.setEnabled(enabled_count > 0)
        
        if enabled_count > 0:
            self.start_btn.setText(f"🚀 Start Processing ({enabled_count} videos)")
        else:
            self.start_btn.setText("🚀 Start Processing")
    
    # ---START PROCESSING--- #
    def start_processing(self):
        enabled_pairs = []
        for row in range(self.pairs_table.rowCount()):
            checkbox = self.pairs_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                video_path = self.pairs_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
                subtitle_path = self.pairs_table.item(row, 2).data(Qt.ItemDataRole.UserRole)
                if subtitle_path:
                    enabled_pairs.append((video_path, subtitle_path))
        
        if not enabled_pairs:
            QMessageBox.warning(self, "No Videos Selected", 
                              "Please select at least one video-subtitle pair to process.")
            return
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.skip_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        
        # --[Start processing thread]-- #
        self.processor_thread = VideoProcessor(
            enabled_pairs, self.output_folder, self.speed_combo.currentText()
        )
        self.processor_thread.progress_updated.connect(self.update_progress)
        self.processor_thread.video_completed.connect(self.video_completed)
        self.processor_thread.all_completed.connect(self.processing_completed)
        self.processor_thread.start()
    
    # ---SKIP CURRENT--- #
    def skip_current(self):
        if self.processor_thread:
            self.processor_thread.skip()
    
    # ---STOP PROCESSING--- #
    def stop_processing(self):
        if self.processor_thread:
            self.processor_thread.stop()
            self.current_video_label.setText("Stopping...")
            self.skip_btn.setEnabled(False)
    
    # ---UPDATE PROGRESS--- #
    def update_progress(self, percent, video_name, output_size, input_size, original_video_size):
        self.progress_bar.setValue(percent)
        self.current_video_label.setText(f"Processing: {video_name}")
        
        if input_size > 0:
            size_ratio = (output_size / input_size) * 100
            if output_size > original_video_size:
                size_change = f"+{output_size - original_video_size:.1f}MB"
            else:
                size_change = f"-{original_video_size - output_size:.1f}MB"
            
            self.size_info_label.setText(
                f"Output: {output_size:.1f}MB ({size_ratio:.1f}% of input) | "
                f"Original video: {original_video_size:.1f}MB | Change: {size_change}"
            )
    
    # ---VIDEO COMPLETED--- #
    def video_completed(self, video_name, success):
        status = "✅ Completed" if success else "❌ Failed/Skipped"
        self.current_video_label.setText(f"{status}: {video_name}")
    
    # ---PROCESSING COMPLETED--- #
    def processing_completed(self):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        self.current_video_label.setText("🎉 All processing completed!")
        
        # --[Play completion sound]-- #
        self.play_completion_sound()
        
        # --[Show completion dialog with options]-- #
        msg = QMessageBox(self)
        msg.setWindowTitle("Processing Complete")
        msg.setText("All video processing has been completed successfully!")
        msg.setIcon(QMessageBox.Icon.Information)
        
        open_folder_btn = msg.addButton("📁 Open Output Folder", QMessageBox.ButtonRole.ActionRole)
        ok_btn = msg.addButton("OK", QMessageBox.ButtonRole.AcceptRole)
        
        msg.exec()
        
        if msg.clickedButton() == open_folder_btn:
            self.open_output_folder()
    
    # ---PLAY COMPLETION SOUND--- #
    def play_completion_sound(self):
        try:
            # --[Simple beep sound using system]-- #
            if sys.platform == "win32":
                import winsound
                winsound.Beep(800, 1000)
            else:
                # --[For Linux/Mac - simple bell]-- #
                print("\a")
        except:
            pass
    
    # ---OPEN OUTPUT FOLDER--- #
    def open_output_folder(self):
        folder_to_open = self.output_folder if self.output_folder else self.current_folder
        if folder_to_open and os.path.exists(folder_to_open):
            if sys.platform == "win32":
                os.startfile(folder_to_open)
            elif sys.platform == "darwin":
                subprocess.run(["open", folder_to_open])
            else:
                subprocess.run(["xdg-open", folder_to_open])

# ---MAIN FUNCTION--- #
def main():
    app = QApplication(sys.argv)
    app.setApplicationName("HardSubber Automator v4.0")
    app.setOrganizationName("Nexus")
    app.setApplicationVersion("4.0")
    
    # --[Set application style]-- #
    app.setStyle('Fusion')
    
    window = HardSubberGUI()
    window.show()
    
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
