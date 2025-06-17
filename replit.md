# HardSubber Automator

## Overview

HardSubber Automator is a Python-based video processing application that automatically hard-codes subtitles into video files using FFmpeg. The application provides both a modern PyQt6 GUI interface and command-line tools for batch processing video files with their corresponding subtitle files. The tool uses intelligent fuzzy matching to automatically pair video files with their subtitle counterparts and provides extensive customization options for subtitle styling and encoding parameters.

## System Architecture

### Frontend Architecture
- **GUI Framework**: PyQt6-based desktop application with modern Qt widgets
- **Interface Design**: Tabbed interface with drag-and-drop support
- **Real-time Preview**: Subtitle styling preview with frame-based rendering
- **Progress Tracking**: Live progress monitoring with ETA calculations
- **Settings Management**: QSettings-based configuration persistence

### Backend Architecture
- **Core Processing**: Python-based FFmpeg wrapper for video encoding
- **File Matching**: Fuzzy string matching algorithm using difflib for automatic subtitle pairing
- **Threading**: Multi-threaded architecture for non-blocking UI operations
- **Process Management**: Subprocess-based FFmpeg execution with real-time output parsing

### Processing Pipeline
1. **File Discovery**: Scans directories for supported video and subtitle formats
2. **Intelligent Matching**: Uses similarity scoring to pair video files with subtitles
3. **Configuration**: Applies user-defined encoding and styling parameters
4. **FFmpeg Execution**: Processes videos with hard-coded subtitles
5. **Progress Monitoring**: Tracks encoding progress and file size changes

## Key Components

### Core Processing Engine
- **File Format Support**: MP4, MKV, MOV (video) and SRT, VTT (subtitles)
- **Encoding Speeds**: Configurable presets (Slow, Medium, Fast, Ultrafast)
- **Quality Control**: User-defined quality settings and compression options
- **Batch Processing**: Handles multiple video files in sequence

### GUI Components
- **Main Interface**: Primary processing window with file selection and progress display
- **Advanced Settings Dialog**: Subtitle customization with font, color, and border controls
- **File Management**: Manual file path configuration and output directory selection
- **Preview System**: Real-time subtitle styling preview with sample text rendering

### Configuration System
- **Persistent Settings**: Save/load user preferences and processing configurations
- **Profile Management**: Multiple configuration profiles for different use cases
- **Default Values**: Sensible defaults for encoding parameters and styling options

## Data Flow

1. **Input Selection**: User selects input directory or individual files via GUI or CLI
2. **File Scanning**: System discovers video files and attempts automatic subtitle matching
3. **Match Validation**: User can override automatic matches or select manual pairings
4. **Configuration Application**: Processing parameters and subtitle styling applied
5. **Encoding Queue**: Files queued for sequential processing with FFmpeg
6. **Progress Monitoring**: Real-time progress updates with size and time estimations
7. **Output Generation**: Hard-subbed videos generated in specified output directory

## External Dependencies

### Core Dependencies
- **FFmpeg**: Required for video processing and subtitle embedding
- **Python 3.12+**: Runtime environment with modern Python features
- **PyQt6**: GUI framework for desktop interface components

### Python Packages
- **qtawesome**: Icon management for GUI elements
- **Pillow**: Image processing for preview generation
- **difflib**: Built-in library for fuzzy string matching

### System Dependencies
- **Graphics Libraries**: OpenGL, X11 libraries for GUI rendering (Linux)
- **Font Systems**: Fontconfig and FreeType for text rendering
- **Audio/Video Codecs**: System codecs for FFmpeg processing

## Deployment Strategy

### Development Environment
- **Replit Integration**: Configured for cloud-based development with Nix package management
- **Module System**: Python 3.11+ modules with necessary system libraries
- **Workflow Automation**: Predefined workflows for GUI and CLI execution

### Package Management
- **UV Lock File**: Dependency management with locked versions for reproducibility
- **Project Configuration**: TOML-based project metadata and dependency specification
- **Nix Dependencies**: System-level dependencies managed through Nix package manager

### Runtime Configuration
- **Entry Points**: Multiple execution modes (GUI, CLI, project workflows)
- **Path Management**: Flexible file path handling for different operating environments
- **Error Handling**: Comprehensive error management with user-friendly messaging

## Changelog

```
Changelog:
- June 17, 2025. Initial setup
```

## User Preferences

```
Preferred communication style: Simple, everyday language.
```