#!/bin/bash

# Activeer virtual environment
source venv/bin/activate

# Export locale en XDG variabelen voor sudo
export LC_ALL=C.UTF-8
export LANG=C.UTF-8

# Start het spel met sudo (nodig voor GPIO toegang)
# Gebruik --preserve-env om locale door te geven, maar reset XDG_RUNTIME_DIR
sudo --preserve-env=LC_ALL,LANG sh -c 'unset XDG_RUNTIME_DIR; venv/bin/python game.py'
