# HardSubber Automator

## Overview

HardSubber Automator is a Python-based video processing application that automatically hard-codes subtitles into video files using FFmpeg. The project has evolved from a command-line tool to a sophisticated GUI application with real-time preview capabilities, subtitle customization, and batch processing features.

## System Architecture

### Frontend Architecture
- **GUI Framework**: PyQt6 for modern desktop interface
- **Video Integration**: QVideoWidget with QMediaPlayer for video playback
- **Custom Components**: Integrated subtitle overlay system with real-time preview
- **Multi-threaded Design**: Separate threads for video processing to maintain UI responsiveness

### Backend Architecture
- **Core Processing Engine**: FFmpeg integration for video encoding and subtitle embedding
- **File Management**: Intelligent subtitle-video matching using fuzzy string algorithms
- **Progress Tracking**: Real-time progress monitoring with ETA calculations
- **Configuration System**: QSettings for persistent user preferences

### Processing Pipeline
1. **File Discovery**: Scans directories for video and subtitle files
2. **Intelligent Matching**: Uses difflib for fuzzy matching between video and subtitle filenames
3. **Preview Generation**: Real-time subtitle preview with customizable styling
4. **Batch Processing**: Multi-threaded video encoding with progress tracking
5. **Output Management**: Configurable output locations with file size monitoring

## Key Components

### Core Modules
- **Hardsubber_V4_GUI.py**: Main GUI application with complete interface
- **Legacy Scripts**: Multiple versions showing evolution (V2.5, V3.0, V3.5) for command-line processing
- **Video Processing**: FFmpeg wrapper with custom encoding presets
- **Subtitle System**: Support for SRT and VTT formats with style customization

### File Structure
```
├── Hardsubber_V4_GUI.py     # Main GUI application
├── Hardsubber_V3.5.py       # Latest command-line version
├── Hardsubber_V3.py         # Previous CLI version
├── Hardsubber.py            # Original version
├── pyproject.toml           # Python project configuration
└── uv.lock                  # Dependency lock file
```

### Supported Formats
- **Video**: MP4, MKV, MOV
- **Subtitles**: SRT, VTT
- **Output**: Configurable video formats with hard-coded subtitles

## Data Flow

1. **Input Selection**: User selects source directory or individual files
2. **File Analysis**: System scans for video files and matches with subtitle files
3. **Preview Stage**: Real-time preview of subtitle styling and positioning
4. **Processing Queue**: Videos are queued for batch processing
5. **Encoding**: FFmpeg processes each video-subtitle pair
6. **Output Generation**: Hard-coded subtitle videos saved to specified location

## External Dependencies

### Required Dependencies
- **FFmpeg**: Core video processing engine (external binary requirement)
- **PyQt6**: GUI framework and multimedia widgets
- **Pillow**: Image processing for subtitle rendering
- **qtawesome**: Icon library for enhanced UI

### Python Standard Libraries
- **subprocess**: FFmpeg process management
- **threading**: Multi-threaded processing
- **difflib**: Fuzzy string matching for file pairing
- **pathlib**: Modern file path handling
- **json**: Configuration and settings storage

## Deployment Strategy

### Environment Setup
- **Python Version**: 3.12+ (configured in .replit)
- **Platform**: Cross-platform desktop application
- **Dependencies**: Managed via pyproject.toml and uv.lock
- **FFmpeg**: Must be installed separately and available in system PATH

### Development Environment
- **Replit Configuration**: Configured for Python 3.12 with GUI support
- **Run Configuration**: Main entry point is Hardsubber_V4_GUI.py
- **Package Management**: Uses modern Python packaging with pyproject.toml

### Distribution Considerations
- Requires FFmpeg installation on target system
- PyQt6 provides native look and feel across platforms
- Configuration persisted using QSettings for cross-platform compatibility

## Changelog

```
Changelog:
- June 14, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```