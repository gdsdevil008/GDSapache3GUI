#!/bin/bash

# Define paths
SCRIPT_NAME="your_script.py"
DIST_DIR="dist"

# Step 1: Install dependencies (ensure Py2App is installed)
pip install py2app

# Step 2: Build the .app bundle
python setup.py py2app

# Step 3: Package the .app into a .dmg file using create-dmg
create-dmg $DIST_DIR/your_script.app

# Step 4: Notify user of completion
echo "macOS .dmg file built successfully!"
echo "The .dmg file is located in: $DIST_DIR"
