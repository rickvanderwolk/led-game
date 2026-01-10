#!/bin/bash

# Activate virtual environment
source venv/bin/activate

# Export locale and XDG variables for sudo
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Start the game with sudo (required for GPIO access)
# Use --preserve-env to pass locale, but reset XDG_RUNTIME_DIR
sudo --preserve-env=LC_ALL,LANG sh -c 'unset XDG_RUNTIME_DIR; venv/bin/python game.py'
