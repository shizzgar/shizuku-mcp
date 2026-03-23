#!/bin/bash
set -e

echo "Updating Termux packages..."
pkg update -y

echo "Installing dependencies..."
pkg install -y python python-pip termux-api

echo "Setting up virtual environment..."
python -m venv venv
source venv/bin/activate

echo "Installing Python requirements..."
pip install .

echo "Checking for rish..."
if [ -f "$HOME/bin/rish" ]; then
    echo "Found rish in ~/bin/"
elif [ -f "/data/data/com.termux/files/usr/bin/rish" ]; then
    echo "Found rish in /usr/bin/"
else
    echo "WARNING: rish not found. Please follow Shizuku instructions to setup rish."
fi

echo "Creating configuration..."
if [ ! -f ".env" ]; then
    echo "MCP_AUTH_TOKEN=$(openssl rand -hex 16)" > .env
    echo "Created .env with random token."
fi

echo "Setup complete."
