#!/usr/bin/env bash
# exit on error
set -o errexit

# 1. Update Linux package manager and install core SWI-Prolog binary engine
echo "Installing SWI-Prolog Engine..."
apt-get update && apt-get install -y swi-prolog

# 2. Install your Python requirements.txt
echo "Installing Python dependencies..."
pip install -r requirements.txt