import sys
import os
import subprocess
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QFileDialog, QTableWidget, QTableWidgetItem,
    QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QComboBox, QTextEdit,
    QLabel, QProgressBar, QAbstractItemView
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

class FFmpegWorker(QThread):
    progress = pyqtSignal(int, float, float)  # percent, current MB, %size
    finished = pyqtSignal(str, float)         # status msg, size delta MB

    def __init__(self, video_path, sub_path, output_path, preset):
        super().__init__()
        self.video_path = video_path
        self.sub_path = sub_path
        self.output_path = output_path
        self.preset = preset

    def run(self):
        original_size = os.path.getsize(self.video_path) / (1024 * 1024)
        cmd = [
            "ffmpeg", "-i", self.video_path,
            "-vf", f"subtitles={self.sub_path}",
            "-preset", self.preset,
            self.output_path
        ]
        process = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True)

        for line in process.stderr:
            if "time=" in line:
                self.progress.emit(50, 0.0, 0.0)  # Placeholder
        process.wait()

        new_size = os.path.getsize(self.output_path) / (1024 * 1024)
        delta = new_size - original_size
        self.finished.emit("Done", delta)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Video + Subtitle Processor")
        self.resize(900, 600)

        self.folder_path = ""
        self.output_folder = ""

        # Widgets
        self.table = QTableWidget(0, 3)
        self.table.setHorizontalHeaderLabels(["✔", "Video", "Subtitle"])
        self.table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        self.scan_btn = QPushButton("Scan Folder")
        self.output_btn = QPushButton("Output Folder")
        self.start_btn = QPushButton("Start")
        self.cancel_btn = QPushButton("Cancel")
        self.preset_box = QComboBox()
        self.preset_box.addItems(["ultrafast", "fast", "medium", "slow"])
        self.log = QTextEdit()
        self.log.setReadOnly(True)

        # Layouts
        top_bar = QHBoxLayout()
        top_bar.addWidget(self.scan_btn)
        top_bar.addWidget(self.output_btn)
        top_bar.addWidget(QLabel("Preset:"))
        top_bar.addWidget(self.preset_box)
        top_bar.addWidget(self.start_btn)
        top_bar.addWidget(self.cancel_btn)

        layout = QVBoxLayout()
        layout.addLayout(top_bar)
        layout.addWidget(self.table)
        layout.addWidget(QLabel("Status Log:"))
        layout.addWidget(self.log)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        # Connect
        self.scan_btn.clicked.connect(self.scan_folder)
        self.output_btn.clicked.connect(self.select_output_folder)
        self.start_btn.clicked.connect(self.start_processing)
        self.cancel_btn.clicked.connect(self.cancel_all)

    def scan_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Input Folder")
        if folder:
            self.folder_path = folder
            self.populate_table()

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder = folder

    def populate_table(self):
        self.table.setRowCount(0)
        for filename in os.listdir(self.folder_path):
            if filename.lower().endswith(('.mp4', '.mkv', '.mov')):
                base = os.path.splitext(filename)[0]
                sub_file = next((f for f in os.listdir(self.folder_path)
                                 if f.startswith(base) and f.endswith(('.srt', '.ass'))), "")
                row = self.table.rowCount()
                self.table.insertRow(row)

                chk = QTableWidgetItem()
                chk.setFlags(Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsEnabled)
                chk.setCheckState(Qt.CheckState.Checked)
                self.table.setItem(row, 0, chk)
                self.table.setItem(row, 1, QTableWidgetItem(filename))
                self.table.setItem(row, 2, QTableWidgetItem(sub_file))

    def start_processing(self):
        for row in range(self.table.rowCount()):
            if self.table.item(row, 0).checkState() == Qt.CheckState.Checked:
                video = self.table.item(row, 1).text()
                sub = self.table.item(row, 2).text()
                preset = self.preset_box.currentText()
                input_path = os.path.join(self.folder_path, video)
                sub_path = os.path.join(self.folder_path, sub)
                output_path = os.path.join(self.output_folder or self.folder_path, f"out_{video}")

                worker = FFmpegWorker(input_path, sub_path, output_path, preset)
                worker.progress.connect(self.update_progress)
                worker.finished.connect(self.show_result)
                worker.start()

    def update_progress(self, percent, size, size_percent):
        self.log.append(f"Progress: {percent}% | Size: {size:.2f}MB")

    def show_result(self, msg, size_diff):
        self.log.append(f"Done: {msg} | ΔSize: {size_diff:.2f}MB")

    def cancel_all(self):
        self.log.append("Cancel clicked — feature WIP")

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
