# main.py

import os
from core import (
    scan_videos,
    find_matching_subtitle,
    process_video,
    estimate_size,
    get_duration
)

def main():
    print("🎞️  HardSubber Test Mode")
    folder = input("📂 Enter the full path to the video folder: ").strip()

    if not os.path.isdir(folder):
        print("❌ Invalid folder. Exiting.")
        return

    videos = scan_videos(folder)
    if not videos:
        print("😔 No videos found.")
        return

    print(f"✅ Found {len(videos)} video(s):\n")
    for idx, v in enumerate(videos):
        print(f"{idx+1}. {os.path.basename(v)}")

    print("\n⚙️  Choose encoding speed (ultrafast / fast / medium / slow):")
    speed = input("👉 Enter speed [default=medium]: ").strip().lower()
    if speed not in ['ultrafast', 'fast', 'medium', 'slow']:
        speed = 'medium'

    output_dir = os.path.join(folder, "hardsubbed")
    os.makedirs(output_dir, exist_ok=True)

    print("\n🚀 Starting encoding...\n")

    for video in videos:
        sub = find_matching_subtitle(video)
        print(f"🎬 {os.path.basename(video)}")

        if not sub:
            print("   ⚠️ No matching subtitle. Skipped.\n")
            continue

        dur_vid = get_duration(video)
        dur_sub = get_duration(sub)
        size = estimate_size(video)

        print(f"   ⏱ Duration: {int(dur_vid)}s | 📁 Size: {size:.2f} MB | 📄 Sub: {os.path.basename(sub)}")

        success, result = process_video(video, sub, speed, output_dir)

        if success:
            print(f"   ✅ Done: {os.path.basename(result)}\n")
        else:
            print(f"   ❌ Failed: {result}\n")

    print("\n🎉 All done! Check your output folder.")

if __name__ == "__main__":
    main()
