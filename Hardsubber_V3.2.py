# ╔════════════════════════════╗
# ║  HardSubber Automator v3.5 ║
# ║  by Nexus // MD_nexus      ║
# ╚════════════════════════════╝

import re
import os
import sys
import time
import shlex
import difflib
import threading
import subprocess

# ---SUPPORTED FORMATS--- #
video_exts = [".mp4", ".mkv", ".mov"]
subtitle_exts = [".srt", ".vtt"]

# ---WARNINGS--- #
print(
    " (@.@) WARNING: This script will hard-sub videos using FFmpeg.\n"
    " (@.@) Make sure every video file has a matching subtitle file with the SAME or similar name.\n"
    " ('-') Example: 'Episode1-360p.mp4' ↔ 'Episode1-360p.srt' or 'episode1 english.vtt'\n"
)
# input("Press Enter to continue if you're sure...")

# ---MANUAL CONFIGS--- #
Speed = (
    input(
        "Warning: A faster mode will result in larger file sizes. (default: Medium)\nChoose mode[Slow, Medium, Fast, Ultrafast]: "
    )
    .strip()
    .lower()
)
if not Speed:
    Speed = "medium"
valid_speeds = ["slow", "medium", "fast", "ultrafast"]
if Speed not in valid_speeds:
    print(f"Invalid speed '{Speed}'. Defaulting to 'medium'.")
    Speed = "medium"
MFP = input("Do you want to Manually set the location of your files? [Y/N]: ").lower()
if MFP == "y":
    MF = input("Set files location: ")
MOP = input("Do you want to Manually set the output location? [Y/N]: ").lower()
if MOP == "y":
    MO = input("Set your desired output location: ")

# ---GET CURRENT FOLDER--- #
if MFP == "y":
    folder = MF
else:
    folder = os.getcwd()
print(f"\nScanning: {folder}\n")

# ---GET SUBTITLE FILES LIST--- #
subtitle_files = [
    f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in subtitle_exts
]


# ---BREAK-PROOF FILE NAME--- #
def break_proof_filename(name):
    return re.sub(r'[<>:"/\\|?*]', "_", name)

# ---LOOSE MATCH SUBTITLES--- #
def find_loose_subtitle(video_name):
    video_name = video_name.lower()
    lowercase_subs = {sub.lower(): sub for sub in subtitle_files}
    matches = difflib.get_close_matches(
        video_name, lowercase_subs.keys(), n=1, cutoff=0.3
    )
    return lowercase_subs[matches[0]] if matches else None


# ---MANUAL SELECTOR--- #
def manual_subtitle_select(video_name):
    print(f"\n (00) Base name of video is: [{video_name}]")
    print("Available subtitle files:")

    numbered_subs = []
    for i, f in enumerate(subtitle_files):
        print(f"  {i + 1}. {f}")
        numbered_subs.append(f)

    choice = input(
        " (.^.)  Enter the number of the subtitle to match, or press Enter to skip: "
    ).strip()
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(numbered_subs):
            return numbered_subs[idx]
    return None


# ---PROCESS EACH VIDEO FILE--- #
for file in os.listdir(folder):
    name, ext = os.path.splitext(file)
    if ext.lower() in video_exts:
        video_path = os.path.join(folder, file)
        subtitle_path = None

        # --[Try loose match]-- #
        loose_match = find_loose_subtitle(name)
        if loose_match:
            subtitle_path = os.path.join(folder, loose_match)
        else:
            # --[Prompt if not found]-- #
            print(f" (;_;)About to skip: {file} (No matching subtitle found)")
            decision = input(
                " (*-¿) Type 'n' to list and select subtitle file, or press Enter to skip: "
            ).lower()
            if decision == "n":
                manual_choice = manual_subtitle_select(name)
                if manual_choice:
                    subtitle_path = os.path.join(folder, manual_choice)

        if subtitle_path:
            safe_name = break_proof_filename(name)
            if MOP == "y":
                output_path = os.path.join(MO, f"{safe_name}_subbed.mp4")
                os.makedirs(os.path.dirname(output_path), exist_ok=True)
            else:
                output_path = os.path.join(folder, f"{safe_name}_subbed.mp4")

            # ---FFMPEG PROGRESS BAR--- #
            def run_ffmpeg_with_progress(video, sub, out_file):
                print(f"\nMerging: {video} + {sub}\n")

                cmd = [
                    "ffmpeg",
                    "-i", video_path,
                    "-vf", f"subtitles={subtitle_path.replace(os.sep, '/').replace(':', '\\:').replace("'", r"'\''")}",
                    "-c:v",
                    "libx264",
                    "-preset", Speed,
                    "-c:a",
                    "copy",
                    output_path
                ]

                # Get total duration
                def get_duration(path):
                    result = subprocess.run(
                        ["ffprobe", "-v", "error", "-show_entries", "format=duration",
                         "-of", "default=noprint_wrappers=1:nokey=1", path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.STDOUT
                    )
                    try:
                        return float(result.stdout.decode().strip())
                    except:
                        return None

                total_duration = get_duration(os.path.join(folder, video))
                if not total_duration:
                    print(" (X.X) Couldn't get video duration.")
                    return

                process = subprocess.Popen(
                    cmd,
                    stderr=subprocess.PIPE,
                    stdout=subprocess.DEVNULL,
                    universal_newlines=True,
                    bufsize=1
                )

                for line in process.stderr:
                    if "time=" in line:
                        match = re.search(r"time=(\d+):(\d+):(\d+.\d+)", line)
                        if match:
                            h, m, s = map(float, match.groups())
                            current_sec = h * 3600 + m * 60 + s
                            percent = (current_sec / total_duration) * 100
                            draw_bar(percent, video, sub, out_file)
                process.wait()
                print(f"\n{out_file} Done (^,^)\n")


            def draw_bar(percent, video, sub, out_file):
                percent = min(100, percent)
                i = int(percent)
                bar = '=' * (i // 2) + '-' * ((100 - i) // 2)
                eta = time.strftime("%H:%M:%S", time.gmtime((100 - i) * 2 // 100))
                sys.stdout.write("\r")
                sys.stdout.write(
                    f"Processing: {video} + {sub} |{bar}| {i:3.0f}% E.T.A: {eta}"
                )
                sys.stdout.flush()

            # --[CLI Animation]-- #
            run_ffmpeg_with_progress(
                file, os.path.basename(subtitle_path), os.path.basename(output_path)
            )
        else:
            print(f"Skipped: {file} (No subtitle selected) (.;)\n")

print(" (^o^) All done. Press Enter to exit.")
input()
