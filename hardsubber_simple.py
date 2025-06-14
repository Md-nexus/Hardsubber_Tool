#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.3 ║
# ║  Simple GUI Edition        ║
# ║  by Nexus // MD-nexus      ║
# ╚════════════════════════════╝

import sys
import os
import re
import time
import json
import difflib
import subprocess
from pathlib import Path
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, colorchooser
import threading

class SubtitlePreviewWidget:
    def __init__(self, parent):
        self.parent = parent
        self.subtitle_text = ""
        self.subtitle_style = {
            'font_size': 16,
            'font_name': 'Arial',
            'font_color': '#FFFFFF',
            'border_enabled': True,
            'border_style': 3
        }
        
        # Create preview frame with integrated subtitle display
        self.preview_frame = ttk.LabelFrame(parent, text="Subtitle Preview", padding=10)
        
        # Video preview area (simulated black background like video player)
        self.video_canvas = tk.Canvas(
            self.preview_frame, 
            width=640, 
            height=360, 
            bg='black',
            relief='ridge',
            bd=2
        )
        self.video_canvas.pack(pady=5)
        
        # Add placeholder text
        self.video_canvas.create_text(
            320, 180, 
            text="Video Preview Area\n\nSubtitles will appear here overlaid like in VLC", 
            fill='gray',
            font=('Arial', 12),
            justify='center'
        )
        
        # Single set of preview controls (no duplicates)
        controls_frame = ttk.Frame(self.preview_frame)
        controls_frame.pack(fill='x', pady=5)
        
        self.test_btn = ttk.Button(
            controls_frame,
            text="Test Subtitle Preview",
            command=self.test_subtitle
        )
        self.test_btn.pack(side='left', padx=5)
        
        # Subtitle text will be overlaid on the canvas
        self.subtitle_id = None
        
    def set_subtitle(self, text, style_dict=None):
        self.subtitle_text = text
        if style_dict:
            self.subtitle_style.update(style_dict)
        self.update_preview()
        
    def update_preview(self):
        # Clear previous subtitle
        if self.subtitle_id:
            self.video_canvas.delete(self.subtitle_id)
            
        if not self.subtitle_text:
            return
            
        # Position subtitle at bottom like VLC
        canvas_width = self.video_canvas.winfo_width() or 640
        canvas_height = self.video_canvas.winfo_height() or 360
        
        # Subtitle positioning
        x = canvas_width // 2
        y = canvas_height - 50  # Bottom margin
        
        # Font settings
        font_size = self.subtitle_style.get('font_size', 16)
        font_name = self.subtitle_style.get('font_name', 'Arial')
        font_color = self.subtitle_style.get('font_color', '#FFFFFF')
        
        # Create subtitle with background if border enabled
        if self.subtitle_style.get('border_enabled', True):
            # Create background rectangle
            text_bbox = self.video_canvas.create_text(
                x, y, text=self.subtitle_text, 
                fill=font_color,
                font=(font_name, font_size, 'bold'),
                justify='center',
                anchor='center'
            )
            bbox = self.video_canvas.bbox(text_bbox)
            if bbox:
                # Add padding and create background
                padding = 8
                bg_rect = self.video_canvas.create_rectangle(
                    bbox[0] - padding, bbox[1] - padding,
                    bbox[2] + padding, bbox[3] + padding,
                    fill='black', outline='white', width=1
                )
                # Bring text to front
                self.video_canvas.tag_raise(text_bbox, bg_rect)
                self.subtitle_id = [bg_rect, text_bbox]
            else:
                self.subtitle_id = [text_bbox]
        else:
            # Just text without background
            self.subtitle_id = [self.video_canvas.create_text(
                x, y, text=self.subtitle_text,
                fill=font_color,
                font=(font_name, font_size, 'bold'),
                justify='center',
                anchor='center'
            )]
            
    def test_subtitle(self):
        test_text = "This is a sample subtitle text.\nIt shows how your subtitles will look overlaid on the video."
        self.set_subtitle(test_text)
        
    def pack(self, **kwargs):
        self.preview_frame.pack(**kwargs)

class VideoProcessor(threading.Thread):
    def __init__(self, video_pairs, output_folder, speed_preset, subtitle_settings, gui):
        super().__init__(daemon=True)
        self.video_pairs = video_pairs
        self.output_folder = output_folder
        self.speed_preset = speed_preset
        self.subtitle_settings = subtitle_settings
        self.gui = gui
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
                self.gui.update_status(f"Error: Could not determine duration for {video_name}")
                continue

            # Build FFmpeg command
            subtitle_filter_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
            force_style_parts = []

            if self.subtitle_settings.get('font_enabled', False):
                font_size = self.subtitle_settings.get('font_size', 16)
                font_name = self.subtitle_settings.get('font_name', 'Arial')
                force_style_parts.append(f"FontSize={font_size}")
                force_style_parts.append(f"FontName={font_name}")

            if self.subtitle_settings.get('color_enabled', False):
                color = self.subtitle_settings.get('font_color', '#FFFFFF')
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

            if not force_style_parts:
                force_style_parts = ["FontSize=16", "BorderStyle=3", "Outline=2"]

            force_style = ",".join(force_style_parts)

            cmd = [
                "ffmpeg", "-y", "-i", video_path,
                "-vf", f"subtitles='{subtitle_filter_path}':force_style='{force_style}'",
                "-c:v", "libx264", "-preset", self.speed_preset,
                "-c:a", "copy", "-movflags", "+faststart", output_path
            ]

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
                    if not self.is_running or self.skip_requested:
                        process.terminate()
                        if self.skip_requested:
                            self.gui.update_status(f"Skipped: {video_name}")
                        break

                    if "time=" in line:
                        match = re.search(r"time=(\d+):(\d+):(\d+.\d)", line)
                        if match:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = min((current_sec / total_duration) * 100, 99)
                            eta = self.calculate_eta(percent, total_videos)
                            
                            eta_text = f" (ETA: {eta/60:.1f}m)" if eta > 0 else ""
                            self.gui.update_progress(
                                percent, 
                                f"Processing: {video_name} - {percent:.1f}%{eta_text}"
                            )

                if not self.skip_requested:
                    process.wait()
                    success = process.returncode == 0 and self.is_running
                    if success:
                        success_count += 1
                        self.gui.update_status(f"Completed: {video_name}")
                    else:
                        self.gui.update_status(f"Failed: {video_name}")

            except Exception as e:
                self.gui.update_status(f"Error processing {video_name}: {str(e)}")

            self.processed_count += 1

        if self.is_running:
            self.gui.processing_completed(success_count, total_videos)

class SubtitleSettingsDialog:
    def __init__(self, parent, current_settings=None):
        self.parent = parent
        self.settings = current_settings or {}
        self.result = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("Subtitle Settings")
        self.dialog.geometry("400x500")
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.setup_ui()
        
    def setup_ui(self):
        main_frame = ttk.Frame(self.dialog, padding=10)
        main_frame.pack(fill='both', expand=True)
        
        # Font Settings
        font_frame = ttk.LabelFrame(main_frame, text="Font Settings", padding=10)
        font_frame.pack(fill='x', pady=5)
        
        self.font_enabled = tk.BooleanVar(value=self.settings.get('font_enabled', False))
        ttk.Checkbutton(font_frame, text="Enable Custom Font", variable=self.font_enabled).pack(anchor='w')
        
        ttk.Label(font_frame, text="Font Size:").pack(anchor='w', pady=(10,0))
        self.font_size = tk.IntVar(value=self.settings.get('font_size', 16))
        font_size_spin = ttk.Spinbox(font_frame, from_=8, to=72, textvariable=self.font_size, width=10)
        font_size_spin.pack(anchor='w')
        
        ttk.Label(font_frame, text="Font Name:").pack(anchor='w', pady=(10,0))
        self.font_name = tk.StringVar(value=self.settings.get('font_name', 'Arial'))
        ttk.Entry(font_frame, textvariable=self.font_name, width=20).pack(anchor='w')
        
        # Color Settings
        color_frame = ttk.LabelFrame(main_frame, text="Color Settings", padding=10)
        color_frame.pack(fill='x', pady=5)
        
        self.color_enabled = tk.BooleanVar(value=self.settings.get('color_enabled', False))
        ttk.Checkbutton(color_frame, text="Enable Custom Color", variable=self.color_enabled).pack(anchor='w')
        
        color_btn_frame = ttk.Frame(color_frame)
        color_btn_frame.pack(anchor='w', pady=(10,0))
        ttk.Label(color_btn_frame, text="Font Color:").pack(side='left')
        
        self.font_color = self.settings.get('font_color', '#FFFFFF')
        self.color_btn = tk.Button(
            color_btn_frame, 
            text="    ", 
            bg=self.font_color, 
            command=self.choose_color,
            width=5
        )
        self.color_btn.pack(side='left', padx=(10,0))
        
        # Border Settings
        border_frame = ttk.LabelFrame(main_frame, text="Border Settings", padding=10)
        border_frame.pack(fill='x', pady=5)
        
        self.border_enabled = tk.BooleanVar(value=self.settings.get('border_enabled', True))
        ttk.Checkbutton(border_frame, text="Enable Border/Outline", variable=self.border_enabled).pack(anchor='w')
        
        ttk.Label(border_frame, text="Border Style:").pack(anchor='w', pady=(10,0))
        self.border_style = tk.IntVar(value=self.settings.get('border_style', 3))
        border_spin = ttk.Spinbox(border_frame, from_=0, to=4, textvariable=self.border_style, width=10)
        border_spin.pack(anchor='w')
        
        # Quality Settings
        quality_frame = ttk.LabelFrame(main_frame, text="Video Quality Settings", padding=10)
        quality_frame.pack(fill='x', pady=5)
        
        self.crf_enabled = tk.BooleanVar(value=self.settings.get('crf_enabled', False))
        ttk.Checkbutton(quality_frame, text="Enable Custom Quality (CRF)", variable=self.crf_enabled).pack(anchor='w')
        
        ttk.Label(quality_frame, text="CRF Value:").pack(anchor='w', pady=(10,0))
        self.crf_value = tk.IntVar(value=self.settings.get('crf_value', 23))
        crf_frame = ttk.Frame(quality_frame)
        crf_frame.pack(anchor='w')
        
        crf_scale = ttk.Scale(crf_frame, from_=0, to=51, variable=self.crf_value, orient='horizontal', length=200)
        crf_scale.pack(side='left')
        
        self.crf_label = ttk.Label(crf_frame, text="23 (High)")
        self.crf_label.pack(side='left', padx=(10,0))
        
        crf_scale.configure(command=self.update_crf_label)
        self.update_crf_label(self.crf_value.get())
        
        # Buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill='x', pady=(20,0))
        
        ttk.Button(btn_frame, text="OK", command=self.ok_clicked).pack(side='right', padx=(5,0))
        ttk.Button(btn_frame, text="Cancel", command=self.cancel_clicked).pack(side='right')
        
    def choose_color(self):
        color = colorchooser.askcolor(color=self.font_color, parent=self.dialog)
        if color[1]:  # color[1] is the hex value
            self.font_color = color[1]
            self.color_btn.configure(bg=self.font_color)
            
    def update_crf_label(self, value):
        value = int(float(value))
        quality_descriptions = {
            0: "Lossless", 18: "Very High", 23: "High (Default)",
            28: "Medium", 35: "Low", 51: "Very Low"
        }
        closest_key = min(quality_descriptions.keys(), key=lambda x: abs(x - value))
        description = quality_descriptions.get(closest_key, "Custom")
        self.crf_label.configure(text=f"{value} ({description})")
        
    def ok_clicked(self):
        self.result = {
            'font_enabled': self.font_enabled.get(),
            'font_size': self.font_size.get(),
            'font_name': self.font_name.get(),
            'color_enabled': self.color_enabled.get(),
            'font_color': self.font_color,
            'border_enabled': self.border_enabled.get(),
            'border_style': self.border_style.get(),
            'crf_enabled': self.crf_enabled.get(),
            'crf_value': self.crf_value.get()
        }
        self.dialog.destroy()
        
    def cancel_clicked(self):
        self.result = None
        self.dialog.destroy()

class HardSubberGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("HardSubber Automator v4.3")
        self.root.geometry("1200x800")
        
        self.subtitle_settings = {}
        self.processor = None
        self.output_folder = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main paned window
        main_paned = ttk.PanedWindow(self.root, orient='horizontal')
        main_paned.pack(fill='both', expand=True, padx=5, pady=5)
        
        # Left panel
        left_frame = ttk.Frame(main_paned)
        main_paned.add(left_frame, weight=1)
        
        # File management
        file_frame = ttk.LabelFrame(left_frame, text="Video File Management", padding=10)
        file_frame.pack(fill='both', expand=True, pady=5)
        
        btn_frame = ttk.Frame(file_frame)
        btn_frame.pack(fill='x', pady=5)
        
        ttk.Button(btn_frame, text="Add Video Files", command=self.add_video_files).pack(side='left', padx=5)
        ttk.Button(btn_frame, text="Clear All", command=self.clear_all_videos).pack(side='left', padx=5)
        
        # Video table
        table_frame = ttk.Frame(file_frame)
        table_frame.pack(fill='both', expand=True, pady=5)
        
        # Treeview for videos
        columns = ('Select', 'Video File', 'Subtitle File')
        self.video_tree = ttk.Treeview(table_frame, columns=columns, show='headings', height=8)
        
        for col in columns:
            self.video_tree.heading(col, text=col)
            self.video_tree.column(col, width=150)
            
        scrollbar = ttk.Scrollbar(table_frame, orient='vertical', command=self.video_tree.yview)
        self.video_tree.configure(yscrollcommand=scrollbar.set)
        
        self.video_tree.pack(side='left', fill='both', expand=True)
        scrollbar.pack(side='right', fill='y')
        
        # Settings
        settings_frame = ttk.LabelFrame(left_frame, text="Processing Settings", padding=10)
        settings_frame.pack(fill='x', pady=5)
        
        # Output folder
        output_frame = ttk.Frame(settings_frame)
        output_frame.pack(fill='x', pady=5)
        
        ttk.Button(output_frame, text="Set Output Folder", command=self.set_output_folder).pack(side='left')
        self.output_label = ttk.Label(output_frame, text="No output folder selected")
        self.output_label.pack(side='left', padx=(10,0))
        
        # Speed preset
        speed_frame = ttk.Frame(settings_frame)
        speed_frame.pack(fill='x', pady=5)
        
        ttk.Label(speed_frame, text="Speed Preset:").pack(side='left')
        self.speed_combo = ttk.Combobox(
            speed_frame, 
            values=["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"],
            state='readonly'
        )
        self.speed_combo.set("fast")
        self.speed_combo.pack(side='left', padx=(10,0))
        
        ttk.Button(settings_frame, text="Subtitle Settings", command=self.open_subtitle_settings).pack(pady=5)
        
        # Processing controls
        process_frame = ttk.LabelFrame(left_frame, text="Processing Controls", padding=10)
        process_frame.pack(fill='x', pady=5)
        
        self.start_btn = ttk.Button(process_frame, text="Start Processing", command=self.start_processing)
        self.start_btn.pack(pady=5)
        
        control_frame = ttk.Frame(process_frame)
        control_frame.pack(fill='x', pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="Stop", command=self.stop_processing, state='disabled')
        self.stop_btn.pack(side='left', padx=5)
        
        self.skip_btn = ttk.Button(control_frame, text="Skip Current", command=self.skip_current, state='disabled')
        self.skip_btn.pack(side='left', padx=5)
        
        # Progress
        self.progress_var = tk.DoubleVar()
        self.progress_bar = ttk.Progressbar(process_frame, variable=self.progress_var, length=300)
        self.progress_bar.pack(fill='x', pady=5)
        
        self.status_label = ttk.Label(process_frame, text="Ready to process videos")
        self.status_label.pack()
        
        # Right panel - Integrated subtitle preview
        right_frame = ttk.Frame(main_paned)
        main_paned.add(right_frame, weight=1)
        
        self.preview_widget = SubtitlePreviewWidget(right_frame)
        self.preview_widget.pack(fill='both', expand=True, pady=5)
        
    def add_video_files(self):
        files = filedialog.askopenfilenames(
            title="Select Video Files",
            filetypes=[("Video Files", "*.mp4 *.mkv *.avi *.mov"), ("All Files", "*.*")]
        )
        
        for video_path in files:
            subtitle_path = self.find_matching_subtitle(video_path)
            self.add_video_to_tree(video_path, subtitle_path)
            
    def add_video_to_tree(self, video_path, subtitle_path):
        subtitle_name = os.path.basename(subtitle_path) if subtitle_path else "No subtitle"
        
        item_id = self.video_tree.insert('', 'end', values=(
            "✓",  # Selected by default
            os.path.basename(video_path),
            subtitle_name
        ))
        
        # Store full paths as tags
        self.video_tree.set(item_id, '#1', video_path)  # Store full video path
        if subtitle_path:
            self.video_tree.set(item_id, '#2', subtitle_path)  # Store full subtitle path
            
    def find_matching_subtitle(self, video_path):
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        for ext in ['.srt', '.vtt']:
            subtitle_path = os.path.join(video_dir, video_name + ext)
            if os.path.exists(subtitle_path):
                return subtitle_path
                
        subtitle_files = [f for f in os.listdir(video_dir) if f.lower().endswith(('.srt', '.vtt'))]
        if subtitle_files:
            matches = difflib.get_close_matches(video_name, 
                [os.path.splitext(f)[0] for f in subtitle_files], 
                n=1, cutoff=0.6)
            if matches:
                for file in subtitle_files:
                    if os.path.splitext(file)[0] == matches[0]:
                        return os.path.join(video_dir, file)
        return None
        
    def clear_all_videos(self):
        for item in self.video_tree.get_children():
            self.video_tree.delete(item)
            
    def set_output_folder(self):
        folder = filedialog.askdirectory(title="Select Output Folder")
        if folder:
            self.output_folder = folder
            self.output_label.configure(text=f"Output: {folder}")
            
    def open_subtitle_settings(self):
        dialog = SubtitleSettingsDialog(self.root, self.subtitle_settings)
        self.root.wait_window(dialog.dialog)
        if dialog.result:
            self.subtitle_settings = dialog.result
            self.preview_widget.subtitle_style.update(self.subtitle_settings)
            
    def start_processing(self):
        # Get selected video pairs
        video_pairs = []
        for item in self.video_tree.get_children():
            values = self.video_tree.item(item, 'values')
            if values[0] == "✓":  # Selected
                video_path = self.video_tree.set(item, '#1')
                subtitle_path = self.video_tree.set(item, '#2')
                if video_path and subtitle_path and subtitle_path != "No subtitle":
                    video_pairs.append((video_path, subtitle_path))
                    
        if not video_pairs:
            messagebox.showwarning("Warning", "No valid video-subtitle pairs selected!")
            return
            
        speed_preset = self.speed_combo.get()
        
        self.processor = VideoProcessor(video_pairs, self.output_folder, speed_preset, self.subtitle_settings, self)
        self.processor.start()
        
        self.start_btn.configure(state='disabled')
        self.stop_btn.configure(state='normal')
        self.skip_btn.configure(state='normal')
        
    def stop_processing(self):
        if self.processor:
            self.processor.stop()
            
        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.skip_btn.configure(state='disabled')
        self.progress_var.set(0)
        self.status_label.configure(text="Processing stopped")
        
    def skip_current(self):
        if self.processor:
            self.processor.skip()
            
    def update_progress(self, percent, status_text):
        self.progress_var.set(percent)
        self.status_label.configure(text=status_text)
        
    def update_status(self, text):
        self.status_label.configure(text=text)
        
    def processing_completed(self, success_count, total_count):
        self.progress_var.set(100)
        self.status_label.configure(text=f"Processing complete! {success_count}/{total_count} videos processed successfully")
        
        self.start_btn.configure(state='normal')
        self.stop_btn.configure(state='disabled')
        self.skip_btn.configure(state='disabled')
        
        messagebox.showinfo("Processing Complete", 
                          f"Successfully processed {success_count} out of {total_count} videos!")
        
    def run(self):
        self.root.mainloop()

def main():
    app = HardSubberGUI()
    app.run()

if __name__ == "__main__":
    main()