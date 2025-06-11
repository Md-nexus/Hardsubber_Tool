
# HardSubber Automator

<div align="center">

![Version](https://img.shields.io/badge/version-3.5-blue.svg)
![Python](https://img.shields.io/badge/python-3.6+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)
![FFmpeg](https://img.shields.io/badge/FFmpeg-required-red.svg)

**A powerful Python tool for automatically hard-coding subtitles into video files using FFmpeg**

[Features](#features) • [Installation](#installation) • [Usage](#usage) • [Configuration](#configuration) • [Contributing](#contributing)

</div>

---

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Usage](#usage)
- [Configuration Options](#configuration-options)
- [Supported Formats](#supported-formats)
- [Examples](#examples)
- [Progress Tracking](#progress-tracking)
- [Troubleshooting](#troubleshooting)
- [Version History](#version-history)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

HardSubber Automator is a sophisticated Python script that automatically matches video files with their corresponding subtitle files and hard-codes the subtitles directly into the video using FFmpeg. The tool features intelligent subtitle matching, real-time progress tracking, and flexible configuration options.

## ✨ Features

- **🔍 Intelligent Subtitle Matching**: Automatically finds matching subtitle files using fuzzy string matching
- **📊 Real-time Progress Tracking**: Live progress bar with ETA and file size monitoring
- **⚙️ Flexible Configuration**: Customizable encoding speeds and file locations
- **🎯 Manual Override**: Manual subtitle selection when automatic matching fails
- **📁 Batch Processing**: Process multiple video files in one run
- **💾 Size Monitoring**: Track input vs output file sizes
- **🔄 Restart Capability**: Easy restart functionality after completion

## 📋 Prerequisites

Before using HardSubber Automator, ensure you have:

- **Python 3.6+** installed on your system
- **FFmpeg** installed and accessible from command line
- Video files and corresponding subtitle files in supported formats

### Installing FFmpeg

#### Windows
```bash
# Using Chocolatey
choco install ffmpeg

# Or download from https://ffmpeg.org/download.html
```

#### macOS
```bash
# Using Homebrew
brew install ffmpeg
```

#### Linux
```bash
# Ubuntu/Debian
sudo apt update && sudo apt install ffmpeg

# CentOS/RHEL
sudo yum install ffmpeg
```

## 🚀 Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/yourusername/hardsubber-automator.git
   cd hardsubber-automator
   ```

2. **Verify FFmpeg installation**:
   ```bash
   ffmpeg -version
   ```

3. **Run the script**:
   ```bash
   python Hardsubber_V3.5.py
   ```

## 🎮 Usage

### Basic Usage

1. **Place your files**: Put video files and subtitle files in the same directory
2. **Run the script**: Execute `python Hardsubber_V3.5.py`
3. **Configure settings**: Choose encoding speed and file locations
4. **Monitor progress**: Watch the real-time progress bar
5. **Collect output**: Find your hard-subbed videos with `_subbed.mp4` suffix

### Quick Start Example

```bash
# Your folder structure should look like:
📁 MyVideos/
├── Episode01.mp4
├── Episode01.srt
├── Episode02.mkv
├── Episode02.vtt
└── Hardsubber_V3.5.py

# Run the script
python Hardsubber_V3.5.py
```

## ⚙️ Configuration Options

### Encoding Speed Settings

| Speed | Quality | File Size | Processing Time |
|-------|---------|-----------|----------------|
| **Slow** | Highest | Smallest | Longest |
| **Medium** (default) | High | Moderate | Moderate |
| **Fast** | Good | Large | Fast |
| **Ultrafast** | Lower | Largest | Fastest |

### File Location Options

- **Automatic**: Uses current working directory
- **Manual Input**: Specify custom input directory
- **Manual Output**: Specify custom output directory

## 📁 Supported Formats

### Video Formats
- `.mp4` - MPEG-4 Video
- `.mkv` - Matroska Video
- `.mov` - QuickTime Movie

### Subtitle Formats
- `.srt` - SubRip Subtitle
- `.vtt` - WebVTT Subtitle

## 💡 Examples

### Example 1: Basic Processing
```
Input Files:
- Movie.mp4
- Movie.srt

Output:
- Movie_subbed.mp4 (with hard-coded subtitles)
```

### Example 2: Fuzzy Matching
```
Input Files:
- Episode1-720p.mp4
- episode1 english.srt

Result: ✅ Automatically matched despite different naming
```

### Example 3: Manual Selection
```
Input Files:
- Show_S01E01.mkv
- Sub1.srt
- Sub2.srt
- Sub3.srt

Process: Script will prompt you to manually select the correct subtitle
```

## 📊 Progress Tracking

The latest version includes comprehensive progress tracking:

```
Processing: Episode01.mp4 + Episode01.srt |========================================----------| 80%
E.T.A: 00:02:15 | Out: 145.3MB (120.5%)
```

**Progress Information:**
- **Progress Bar**: Visual representation of encoding progress
- **Percentage**: Current completion percentage
- **ETA**: Estimated time remaining
- **Output Size**: Current output file size
- **Size Ratio**: Output size compared to input (video + subtitle)

## 🔧 Troubleshooting

### Common Issues

#### FFmpeg Not Found
```
Error: 'ffmpeg' is not recognized as an internal or external command
```
**Solution**: Install FFmpeg and ensure it's in your system PATH

#### No Matching Subtitles
```
(;_;) About to skip: Movie.mp4 (No matching subtitle found)
```
**Solution**: 
- Check subtitle file naming
- Use manual selection option (type 'n' when prompted)
- Ensure subtitle files are in supported formats

#### Permission Errors
```
Error: Permission denied when writing output file
```
**Solution**:
- Check write permissions in output directory
- Run as administrator if necessary
- Ensure output directory exists

### File Naming Best Practices

✅ **Good Examples:**
```
Movie.mp4 ↔ Movie.srt
Episode_01.mkv ↔ Episode_01.vtt
Show-S01E01-720p.mp4 ↔ Show-S01E01-English.srt
```

❌ **Problematic Examples:**
```
Movie.mp4 ↔ Subtitle.srt (too different)
Video1.mp4 ↔ Sub2.srt (numbers don't match)
```

## 📈 Version History

### v3.5 (Current)
- ✅ Real-time progress tracking with FFmpeg integration
- ✅ File size monitoring and comparison
- ✅ Improved error handling and user feedback
- ✅ Better filename sanitization for cross-platform compatibility

### v3.0
- ✅ Enhanced progress bar with animations
- ✅ Improved user interface with colored output
- ✅ Better subtitle matching algorithm

### v2.5
- ✅ Basic functionality with FFmpeg integration
- ✅ Fuzzy string matching for subtitle files
- ✅ Manual subtitle selection option

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to the branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Guidelines

- Follow PEP 8 style guidelines
- Add comments for complex logic
- Test with multiple video/subtitle format combinations
- Update documentation for new features

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👨‍💻 Author

**Nexus // MD_nexus**

- GitHub: [@MD-nexus](https://github.com/MD-nexus)
- Email:

## 🙏 Acknowledgments

- FFmpeg team for the powerful multimedia framework
- Python community for excellent libraries
- Contributors and users for feedback and improvements

---

<div align="center">

**Made with ❤️ by Nexus**

[⬆ Back to Top](#hardsubber-automator)

</div>
