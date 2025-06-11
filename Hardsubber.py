# ╔════════════════════════════╗
# ║  HardSubber Automator v2.5 ║
# ║  by Nexus // MD-nexus      ║
# ╚════════════════════════════╝

import re
import os
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
input("Press Enter to continue if you're sure...")

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
MFP = input("Do you want to Manually set the location of your files? [Y/N]: ").lower()
if MFP == "y":
    MF = input("Set files location: ")
MOP = input("Do you want to Manually set the output location? [Y/N]: ").lower()
if MOP == "y":
    MO = input("Set your desired output location: ")

# ---GET CURRENT FOLDER--- #
if MFP == "y":
    folder = MF + "/"
else:
    folder = os.getcwd()
print(f"\nScanning: {folder}\n")

# ---GET SUBTITLE FILES LIST--- #
subtitle_files = [
    f for f in os.listdir(folder) if os.path.splitext(f)[1].lower() in subtitle_exts
]


# ---LOOSE MATCH SUBTITLES--- #
def find_loose_subtitle(video_name):
    matches = difflib.get_close_matches(video_name, subtitle_files, n=1, cutoff=0.3)
    return matches[0] if matches else None


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
            if MOP == "y":
                output_path = os.path.join(MO, f"{name}_subbed.mp4")
            else:
                output_path = os.path.join(folder, f"{name}_subbed.mp4")
            print(f"Processing: {file} + {os.path.basename(subtitle_path)}")

            cmd = [
                "ffmpeg",
                "-hide_banner",
                "-loglevel",
                "error",
                "-i",
                video_path,
                "-vf",
                f"subtitles='{subtitle_path}'",
                "-c:v",
                "libx264",
                "-preset",
                f"{Speed}",
                # "-crf", "24",
                "-c:a",
                "copy",
                output_path,
            ]
            subprocess.run(cmd)
            print(f"Saved: {os.path.basename(output_path)} (^,^)\n")
        else:
            print(f"Skipped: {file} (No subtitle selected) (.;)\n")

print(" (^o^) All done. Press Enter to exit.")
input()
