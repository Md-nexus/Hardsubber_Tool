# HardSubber Automator

## Overview

HardSubber Automator is a Python-based video processing application that automatically hard-codes subtitles into video files using FFmpeg. The project provides both a command-line interface and a modern PyQt6-based GUI for batch processing video files with intelligent subtitle matching.

## System Architecture

### Application Structure
- **Frontend**: PyQt6-based GUI with drag-and-drop support, real-time preview, and configuration management
- **Backend**: Python scripts for video processing, subtitle matching, and FFmpeg integration
- **Processing Engine**: FFmpeg for video encoding and subtitle hard-coding
- **File Management**: Intelligent fuzzy matching algorithm for pairing video and subtitle files

### Technology Stack
- **Python 3.12+**: Core runtime environment
- **PyQt6**: GUI framework with Qt6 bindings
- **FFmpeg**: Video processing and encoding engine
- **QtAwesome**: Icon library for GUI elements
- **Pillow**: Image processing for subtitle preview functionality

## Key Components

### 1. GUI Application (`Hardsubber_V4_GUI.py`)
- Modern PyQt6 interface with tabs and configuration dialogs
- Real-time subtitle preview with customizable styling
- Drag-and-drop file support
- Progress tracking with ETA calculations
- Settings persistence using QSettings

### 2. Command-Line Versions
- **V3.5**: Enhanced CLI with improved error handling and progress display
- **V3.0**: Basic CLI implementation with manual configuration options
- **V2.5**: Original implementation with fundamental features

### 3. Subtitle Processing
- Supports `.srt` and `.vtt` subtitle formats
- Intelligent file matching using difflib for fuzzy string comparison
- Manual override options when automatic matching fails
- Live preview functionality with sample subtitle rendering

### 4. Video Processing
- Supports `.mp4`, `.mkv`, and `.mov` video formats
- Configurable encoding speeds (slow, medium, fast, ultrafast)
- Real-time progress monitoring with file size tracking
- Batch processing capabilities

## Data Flow

1. **File Discovery**: Scan specified directory for video and subtitle files
2. **Intelligent Matching**: Use fuzzy string matching to pair videos with subtitles
3. **Configuration**: Apply user-specified encoding settings and subtitle styling
4. **Processing**: Execute FFmpeg commands with real-time progress monitoring
5. **Output**: Generate hard-coded video files with embedded subtitles

## External Dependencies

### Required System Dependencies
- **FFmpeg**: Core video processing engine (included in Nix environment)
- **Qt6 Libraries**: GUI framework dependencies
- **X11 Libraries**: Linux display system support
- **OpenGL**: Hardware-accelerated rendering support

### Python Dependencies
- `PyQt6`: GUI framework
- `qtawesome`: Icon library
- `Pillow`: Image processing
- `difflib`: String matching (built-in)
- `subprocess`: Process management (built-in)
- `threading`: Concurrent processing (built-in)

## Deployment Strategy

### Development Environment
- **Replit Nix**: Containerized development with all dependencies pre-configured
- **Python 3.12**: Latest stable Python runtime
- **Automatic Dependency Management**: UV lock file for reproducible builds

### Runtime Configuration
- GUI mode: `python Hardsubber_V4_GUI.py`
- CLI mode: `python hardsubber_working.py`
- Configurable through `.replit` workflows

### File Structure
- Source files: Multiple versions for backward compatibility
- Configuration: Settings stored in user preferences
- Output: Processed videos with `_subbed` suffix
- Logs: Processing history and error tracking

## Changelog
```
Changelog:
- June 19, 2025. Initial setup
```

## User Preferences

Preferred communication style: Simple, everyday language.