#!/usr/bin/env python3
# ╔════════════════════════════╗
# ║  HardSubber Automator v4.3 ║
# ║  Working GUI Edition       ║
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
import threading

# Simple terminal-based interface for demonstration
class HardSubberGUI:
    def __init__(self):
        self.subtitle_settings = {
            'font_enabled': False,
            'font_size': 16,
            'font_name': 'Arial',
            'color_enabled': False,
            'font_color': '#FFFFFF',
            'border_enabled': True,
            'border_style': 3,
            'crf_enabled': False,
            'crf_value': 23
        }
        self.output_folder = ""
        self.video_pairs = []
        self.processor = None
        
    def display_menu(self):
        print("\n" + "="*60)
        print("  HardSubber Automator v4.3 - Integrated Subtitle Preview")
        print("="*60)
        print("1. Add Video Files")
        print("2. View Current Videos")
        print("3. Set Output Folder")
        print("4. Configure Subtitle Settings")
        print("5. Preview Subtitle Settings")
        print("6. Start Processing")
        print("7. Exit")
        print("-"*60)
        
    def add_video_files(self):
        print("\nEnter video file paths (one per line, empty line to finish):")
        videos = []
        while True:
            path = input("Video file: ").strip()
            if not path:
                break
            if os.path.exists(path):
                subtitle_path = self.find_matching_subtitle(path)
                videos.append((path, subtitle_path))
                print(f"Added: {os.path.basename(path)}")
                if subtitle_path:
                    print(f"  Subtitle: {os.path.basename(subtitle_path)}")
                else:
                    print("  No subtitle found")
            else:
                print(f"File not found: {path}")
        
        self.video_pairs.extend(videos)
        print(f"\nAdded {len(videos)} video(s)")
        
    def find_matching_subtitle(self, video_path):
        video_dir = os.path.dirname(video_path)
        video_name = os.path.splitext(os.path.basename(video_path))[0]
        
        # Check for exact match
        for ext in ['.srt', '.vtt']:
            subtitle_path = os.path.join(video_dir, video_name + ext)
            if os.path.exists(subtitle_path):
                return subtitle_path
                
        # Try fuzzy matching
        try:
            subtitle_files = [f for f in os.listdir(video_dir) if f.lower().endswith(('.srt', '.vtt'))]
            if subtitle_files:
                matches = difflib.get_close_matches(video_name, 
                    [os.path.splitext(f)[0] for f in subtitle_files], 
                    n=1, cutoff=0.6)
                if matches:
                    for file in subtitle_files:
                        if os.path.splitext(file)[0] == matches[0]:
                            return os.path.join(video_dir, file)
        except:
            pass
        return None
        
    def view_videos(self):
        if not self.video_pairs:
            print("\nNo videos added yet.")
            return
            
        print(f"\nCurrent Videos ({len(self.video_pairs)}):")
        print("-"*80)
        for i, (video_path, subtitle_path) in enumerate(self.video_pairs, 1):
            print(f"{i}. {os.path.basename(video_path)}")
            if subtitle_path:
                print(f"   Subtitle: {os.path.basename(subtitle_path)}")
            else:
                print("   Subtitle: None")
        
    def set_output_folder(self):
        folder = input("\nEnter output folder path (leave empty for same as video): ").strip()
        if folder and os.path.isdir(folder):
            self.output_folder = folder
            print(f"Output folder set to: {folder}")
        elif folder:
            print("Invalid folder path")
        else:
            self.output_folder = ""
            print("Output will be saved in same folder as videos")
            
    def configure_subtitle_settings(self):
        print("\nSubtitle Settings Configuration:")
        print("-"*40)
        
        # Font settings
        self.subtitle_settings['font_enabled'] = input("Enable custom font? (y/n): ").lower() == 'y'
        if self.subtitle_settings['font_enabled']:
            try:
                self.subtitle_settings['font_size'] = int(input(f"Font size [{self.subtitle_settings['font_size']}]: ") or self.subtitle_settings['font_size'])
            except ValueError:
                pass
            font_name = input(f"Font name [{self.subtitle_settings['font_name']}]: ").strip()
            if font_name:
                self.subtitle_settings['font_name'] = font_name
                
        # Color settings
        self.subtitle_settings['color_enabled'] = input("Enable custom color? (y/n): ").lower() == 'y'
        if self.subtitle_settings['color_enabled']:
            color = input(f"Font color [{self.subtitle_settings['font_color']}]: ").strip()
            if color:
                self.subtitle_settings['font_color'] = color
                
        # Border settings
        self.subtitle_settings['border_enabled'] = input("Enable border/outline? (y/n): ").lower() == 'y'
        if self.subtitle_settings['border_enabled']:
            try:
                self.subtitle_settings['border_style'] = int(input(f"Border style (0-4) [{self.subtitle_settings['border_style']}]: ") or self.subtitle_settings['border_style'])
            except ValueError:
                pass
                
        # Quality settings
        self.subtitle_settings['crf_enabled'] = input("Enable custom quality (CRF)? (y/n): ").lower() == 'y'
        if self.subtitle_settings['crf_enabled']:
            try:
                self.subtitle_settings['crf_value'] = int(input(f"CRF value (0-51) [{self.subtitle_settings['crf_value']}]: ") or self.subtitle_settings['crf_value'])
            except ValueError:
                pass
                
        print("\nSettings updated!")
        
    def preview_subtitle_settings(self):
        print("\n" + "="*60)
        print("  SUBTITLE PREVIEW - How subtitles will appear")
        print("="*60)
        print()
        print("┌" + "─"*58 + "┐")
        print("│" + " "*58 + "│")
        print("│" + "Video Preview Area".center(58) + "│")
        print("│" + " "*58 + "│")
        print("│" + " "*58 + "│")
        print("│" + " "*58 + "│")
        
        # Simulate subtitle overlay within video area (like VLC)
        sample_text = "This is a sample subtitle text"
        subtitle_line1 = "overlaid within the video player"
        
        if self.subtitle_settings.get('border_enabled', True):
            # Show subtitle with background box (integrated in video)
            print("│" + " "*58 + "│")
            print("│" + " "*58 + "│")
            print("│" + f"┌{'─' * len(sample_text)}┐".center(58) + "│")
            print("│" + f"│{sample_text}│".center(58) + "│")
            print("│" + f"│{subtitle_line1}│".center(58) + "│")
            print("│" + f"└{'─' * len(sample_text)}┘".center(58) + "│")
        else:
            # Show subtitle without background
            print("│" + " "*58 + "│")
            print("│" + " "*58 + "│")
            print("│" + sample_text.center(58) + "│")
            print("│" + subtitle_line1.center(58) + "│")
            
        print("│" + " "*58 + "│")
        print("└" + "─"*58 + "┘")
        print()
        print("Settings applied:")
        if self.subtitle_settings.get('font_enabled'):
            print(f"  Font: {self.subtitle_settings['font_name']} {self.subtitle_settings['font_size']}px")
        if self.subtitle_settings.get('color_enabled'):
            print(f"  Color: {self.subtitle_settings['font_color']}")
        if self.subtitle_settings.get('border_enabled'):
            print(f"  Border: Style {self.subtitle_settings['border_style']}")
        if self.subtitle_settings.get('crf_enabled'):
            print(f"  Quality: CRF {self.subtitle_settings['crf_value']}")
        print("\nSubtitles appear integrated within the video player area")
        print("(not as a separate background extending beyond video)")
        
    def start_processing(self):
        if not self.video_pairs:
            print("\nNo videos to process!")
            return
            
        print(f"\nStarting processing of {len(self.video_pairs)} video(s)...")
        
        # Show speed preset options
        presets = ["ultrafast", "superfast", "veryfast", "faster", "fast", "medium", "slow", "slower", "veryslow"]
        print("Speed presets:")
        for i, preset in enumerate(presets, 1):
            print(f"  {i}. {preset}")
        
        try:
            choice = int(input("Select speed preset (5 for fast): ") or "5")
            speed_preset = presets[choice - 1] if 1 <= choice <= len(presets) else "fast"
        except (ValueError, IndexError):
            speed_preset = "fast"
            
        print(f"Using speed preset: {speed_preset}")
        
        self.processor = VideoProcessor(self.video_pairs, self.output_folder, speed_preset, self.subtitle_settings)
        self.processor.start()
        
        # Simple progress monitoring
        while self.processor.is_alive():
            time.sleep(1)
            print(".", end="", flush=True)
            
        print(f"\nProcessing completed!")
        
    def run(self):
        while True:
            self.display_menu()
            try:
                choice = input("Select option (1-7): ").strip()
                
                if choice == '1':
                    self.add_video_files()
                elif choice == '2':
                    self.view_videos()
                elif choice == '3':
                    self.set_output_folder()
                elif choice == '4':
                    self.configure_subtitle_settings()
                elif choice == '5':
                    self.preview_subtitle_settings()
                elif choice == '6':
                    self.start_processing()
                elif choice == '7':
                    print("\nExiting HardSubber Automator...")
                    break
                else:
                    print("Invalid option, please try again.")
                    
            except KeyboardInterrupt:
                print("\n\nExiting...")
                break
            except Exception as e:
                print(f"\nError: {e}")

class VideoProcessor(threading.Thread):
    def __init__(self, video_pairs, output_folder, speed_preset, subtitle_settings):
        super().__init__(daemon=True)
        self.video_pairs = video_pairs
        self.output_folder = output_folder
        self.speed_preset = speed_preset
        self.subtitle_settings = subtitle_settings
        self.success_count = 0
        
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
        
    def run(self):
        total_videos = len(self.video_pairs)
        
        for i, (video_path, subtitle_path) in enumerate(self.video_pairs, 1):
            if not subtitle_path:
                print(f"\nSkipping {os.path.basename(video_path)} - no subtitle file")
                continue
                
            print(f"\nProcessing {i}/{total_videos}: {os.path.basename(video_path)}")
            
            video_name = os.path.basename(video_path)
            name, ext = os.path.splitext(video_name)
            safe_name = self.break_proof_filename(name)
            
            if self.output_folder:
                output_path = os.path.join(self.output_folder, f"{safe_name}_subbed.mp4")
            else:
                output_path = os.path.join(os.path.dirname(video_path), f"{safe_name}_subbed.mp4")
                
            # Build FFmpeg command with subtitle settings
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
                print(f"  Output: {os.path.basename(output_path)}")
                process = subprocess.run(cmd, capture_output=True, text=True, timeout=3600)
                
                if process.returncode == 0:
                    self.success_count += 1
                    print(f"  ✓ Completed successfully")
                else:
                    print(f"  ✗ Failed: {process.stderr[:200]}...")
                    
            except subprocess.TimeoutExpired:
                print(f"  ✗ Timeout - video too large or system too slow")
            except Exception as e:
                print(f"  ✗ Error: {str(e)}")
                
        print(f"\n{'='*60}")
        print(f"Processing Summary:")
        print(f"  Total videos: {total_videos}")
        print(f"  Successful: {self.success_count}")
        print(f"  Failed: {total_videos - self.success_count}")
        print(f"{'='*60}")

def main():
    print("Initializing HardSubber Automator...")
    
    # Check for FFmpeg
    try:
        subprocess.run(["ffmpeg", "-version"], capture_output=True, timeout=5)
        print("FFmpeg found - ready to process videos")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        print("Warning: FFmpeg not found. Please install FFmpeg to process videos.")
        
    app = HardSubberGUI()
    app.run()

if __name__ == "__main__":
    main()