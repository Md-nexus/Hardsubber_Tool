
#!/usr/bin/env python3
"""
Web-based HardSubber Interface
A Flask web application for the HardSubber tool
"""

import os
import subprocess
import threading
import json
from flask import Flask, render_template, request, jsonify, send_file
from werkzeug.utils import secure_filename
import tempfile
import shutil

app = Flask(__name__)
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024  # 500MB max file size

# Global variables for processing state
processing_state = {
    'is_processing': False,
    'current_video': '',
    'progress': 0,
    'message': 'Ready'
}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_files():
    if 'video' not in request.files or 'subtitle' not in request.files:
        return jsonify({'error': 'Missing video or subtitle file'}), 400
    
    video_file = request.files['video']
    subtitle_file = request.files['subtitle']
    
    if video_file.filename == '' or subtitle_file.filename == '':
        return jsonify({'error': 'No files selected'}), 400
    
    # Create temporary directory
    temp_dir = tempfile.mkdtemp()
    
    try:
        # Save uploaded files
        video_path = os.path.join(temp_dir, secure_filename(video_file.filename))
        subtitle_path = os.path.join(temp_dir, secure_filename(subtitle_file.filename))
        
        video_file.save(video_path)
        subtitle_file.save(subtitle_path)
        
        # Start processing in background
        threading.Thread(target=process_video, args=(video_path, subtitle_path, temp_dir)).start()
        
        return jsonify({'success': True, 'message': 'Processing started'})
    
    except Exception as e:
        shutil.rmtree(temp_dir, ignore_errors=True)
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_status():
    return jsonify(processing_state)

def process_video(video_path, subtitle_path, temp_dir):
    global processing_state
    
    processing_state['is_processing'] = True
    processing_state['current_video'] = os.path.basename(video_path)
    processing_state['progress'] = 0
    processing_state['message'] = 'Starting processing...'
    
    try:
        # Get output path
        name, ext = os.path.splitext(os.path.basename(video_path))
        output_path = os.path.join(temp_dir, f"{name}_subbed.mp4")
        
        # Prepare FFmpeg command
        subtitle_filter_path = subtitle_path.replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-y", "-i", video_path,
            "-vf", f"subtitles='{subtitle_filter_path}'",
            "-c:v", "libx264", "-preset", "medium",
            "-c:a", "copy", output_path
        ]
        
        # Run FFmpeg with progress tracking
        process = subprocess.Popen(
            cmd, stderr=subprocess.PIPE, stdout=subprocess.DEVNULL,
            universal_newlines=True
        )
        
        # Get video duration for progress calculation
        duration = get_video_duration(video_path)
        
        for line in process.stderr:
            if "time=" in line:
                import re
                match = re.search(r"time=(\d+):(\d+):(\d+.\d)", line)
                if match and duration:
                    h, m, s = map(float, match.groups())
                    current_sec = h * 3600 + m * 60 + s
                    progress = min(int((current_sec / duration) * 100), 100)
                    processing_state['progress'] = progress
                    processing_state['message'] = f'Processing... {progress}%'
        
        process.wait()
        
        if process.returncode == 0:
            processing_state['message'] = 'Processing completed successfully!'
            processing_state['output_file'] = output_path
        else:
            processing_state['message'] = 'Processing failed'
            
    except Exception as e:
        processing_state['message'] = f'Error: {str(e)}'
    
    finally:
        processing_state['is_processing'] = False
        processing_state['progress'] = 100

def get_video_duration(video_path):
    try:
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", video_path],
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
        )
        return float(result.stdout.strip())
    except:
        return None

if __name__ == '__main__':
    # Check for FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        print("FFmpeg found - starting web interface...")
        app.run(host='0.0.0.0', port=5000, debug=True)
    except FileNotFoundError:
        print("FFmpeg not found. Please install FFmpeg to use this application.")
