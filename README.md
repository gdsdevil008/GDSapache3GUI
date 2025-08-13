# GDSapache3

Python Tkinter app to control Apache2 and manage TCP forwarding rules via socat.

## Requirements

- Python 3.6+
- tkinter
- sv_ttk (optional for dark theme)
- socat installed
- sudo privileges on Linux

## Installation

1. Clone repo or download files.
2. Install dependencies: `pip install -r requirements.txt`
3. Run: `python3 GDSapache3.py`

# Package Your Application

Once you’ve set up all your files, follow these instructions to package your app manually.
On Windows:

    Open Command Prompt or Git Bash.

    Navigate to your project directory.

    Run the build_windows.bat batch script to create the .exe:

    build_windows.bat

        This will create a .exe file inside the dist/ folder.

On macOS:

    Open Terminal.

    Navigate to your project directory.

    Make the build_macos.sh script executable:

chmod +x build_macos.sh

Run the build_macos.sh script:

    ./build_macos.sh

        This will create the .app file and then use create-dmg to package it into a .dmg file inside the dist/ folder.

