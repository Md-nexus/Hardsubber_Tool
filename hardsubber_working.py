#!/usr/bin/env python3
"""
HardSubber Working Entry Point
This file serves as the main entry point for the HardSubber application.
"""

import sys
import os
import subprocess

def setup_environment():
    """Setup environment variables for PyQt6 to work properly"""
    # Set Qt platform plugin
    os.environ['QT_QPA_PLATFORM'] = 'offscreen'
    
    # Set Qt API
    os.environ['QT_API'] = 'pyqt6'
    
    # Disable Qt accessibility to avoid potential issues
    os.environ['QT_ACCESSIBILITY'] = '0'
    
    # Add library paths for OpenGL
    nix_lib_paths = [
        '/nix/store/*/lib',
        '/nix/store/*/lib64'
    ]
    
    # Get existing library path
    current_ld_path = os.environ.get('LD_LIBRARY_PATH', '')
    
    # Find actual nix store paths
    try:
        result = subprocess.run(['find', '/nix/store', '-maxdepth', '2', '-name', 'lib', '-type', 'd'], 
                               capture_output=True, text=True, timeout=10)
        if result.returncode == 0:
            nix_paths = result.stdout.strip().split('\n')
            nix_paths = [p for p in nix_paths if p]  # Remove empty strings
            lib_path = ':'.join(nix_paths)
            if current_ld_path:
                os.environ['LD_LIBRARY_PATH'] = f"{lib_path}:{current_ld_path}"
            else:
                os.environ['LD_LIBRARY_PATH'] = lib_path
    except (subprocess.TimeoutExpired, Exception):
        # Fallback to basic setup
        if current_ld_path:
            os.environ['LD_LIBRARY_PATH'] = f"/usr/lib/x86_64-linux-gnu:{current_ld_path}"
        else:
            os.environ['LD_LIBRARY_PATH'] = "/usr/lib/x86_64-linux-gnu"

def main():
    """Main entry point"""
    setup_environment()
    
    # Add the pythonlibs path to ensure modules are found
    pythonlibs_path = os.path.join(os.getcwd(), '.pythonlibs', 'lib', 'python3.12', 'site-packages')
    if os.path.exists(pythonlibs_path) and pythonlibs_path not in sys.path:
        sys.path.insert(0, pythonlibs_path)
    
    try:
        # Import and run the main GUI application
        from Hardsubber_V4_GUI import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"Error importing GUI application: {e}")
        print("Please ensure all dependencies are properly installed.")
        sys.exit(1)
    except Exception as e:
        print(f"Error running application: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()