import os
import subprocess
import re
from pathlib import Path
from typing import Optional

from PyQt6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog,
    QListWidget, QHBoxLayout, QComboBox, QTextEdit, QProgressBar, QMessageBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class FFmpegThread(QThread):
    progress = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(self, video_path, subtitle_path, preset, output_path):
        super().__init__()
        self.video_path = video_path
        self.subtitle_path = subtitle_path
        self.preset = preset
        self.output_path = output_path

    def run(self):
        command = [
            "ffmpeg",
            "-i", str(self.video_path),
            "-vf", f"subtitles={self.subtitle_path}",
            "-preset", self.preset,
            str(self.output_path)
        ]

        process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)

        for line in process.stdout:
            self.progress.emit(line.strip())
        process.wait()
        self.finished.emit()

class VideoSubtitleProcessor(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video + Subtitle Encoder")
        self.resize(800, 600)
        self.video_dir = None
        self.subtitle_dir = None
        self.output_dir = None
        self.videos = []
        self.subtitle_map = {}
        self.active_threads = []

        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        self.folder_label = QLabel("Choose video and subtitle folders")
        layout.addWidget(self.folder_label)

        self.select_video_button = QPushButton("Select Video Folder")
        self.select_video_button.clicked.connect(self.select_video_folder)
        layout.addWidget(self.select_video_button)

        self.select_subtitle_button = QPushButton("Select Subtitle Folder")
        self.select_subtitle_button.clicked.connect(self.select_subtitle_folder)
        layout.addWidget(self.select_subtitle_button)

        self.select_output_button = QPushButton("Select Output Folder")
        self.select_output_button.clicked.connect(self.select_output_folder)
        layout.addWidget(self.select_output_button)

        self.preset_box = QComboBox()
        self.preset_box.addItems(["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"])
        layout.addWidget(self.preset_box)

        self.scan_button = QPushButton("Scan & Match")
        self.scan_button.clicked.connect(self.scan_and_match)
        layout.addWidget(self.scan_button)

        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)

        self.encode_button = QPushButton("Encode Matched Pairs")
        self.encode_button.clicked.connect(self.encode_all)
        layout.addWidget(self.encode_button)

        self.log_output = QTextEdit()
        self.log_output.setReadOnly(True)
        layout.addWidget(self.log_output)

        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)

        self.setLayout(layout)

    def select_video_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Video Folder")
        if folder:
            self.video_dir = Path(folder)

    def select_subtitle_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Subtitle Folder")
        if folder:
            self.subtitle_dir = Path(folder)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_dir = Path(folder)

    def scan_and_match(self):
        if not self.video_dir or not self.subtitle_dir:
            QMessageBox.warning(self, "Missing Folders", "Select both video and subtitle folders.")
            return

        self.videos = list(self.video_dir.glob("*.mp4"))
        subtitles = list(self.subtitle_dir.glob("*.srt"))

        self.subtitle_map.clear()
        self.list_widget.clear()

        for video in self.videos:
            match = self.loose_match(video.stem, subtitles)
            if match:
                self.subtitle_map[video] = match
                self.list_widget.addItem(f"{video.name} <--> {match.name}")
            else:
                self.list_widget.addItem(f"{video.name} <--> No match found")

    def loose_match(self, vid_name, subtitle_list):
        for sub in subtitle_list:
            if vid_name in sub.stem or sub.stem in vid_name:
                return sub
        return None

    def encode_all(self):
        if not self.output_dir:
            QMessageBox.warning(self, "Missing Output Folder", "Select an output folder.")
            return

        preset = self.preset_box.currentText()
        for video, subtitle in self.subtitle_map.items():
            output_name = self.output_dir / f"{video.stem}_encoded.mp4"
            thread = FFmpegThread(video, subtitle, preset, output_name)
            thread.progress.connect(self.log_output.append)
            thread.finished.connect(lambda: self.progress_bar.setValue(self.progress_bar.value() + 100 // len(self.subtitle_map)))
            self.active_threads.append(thread)
            thread.start()

if __name__ == '__main__':
    app = QApplication([])
    processor = VideoSubtitleProcessor()
    processor.show()
    app.exec()
